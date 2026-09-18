#!/usr/bin/env python3
"""
Post-build validator for the ELIT DENT / ORDER PROFIT dental engine.

Run after `python3 build.py`. Two passes:

1. Structural checks over every file in dist/: broken internal links,
   missing images, leftover placeholder/Lorem-ipsum/unrendered-template
   text, stray href="#", missing <title>/meta description/canonical,
   duplicate canonicals, and hy/ru/en content parity (every canonical
   path that exists in one language must exist in all supported ones).
2. Data-consistency checks over data/*.json directly: doctor count,
   service count, review count and the site-wide "stats" numbers must
   all agree with each other, since they're quoted independently on
   several pages (home trust strip, about page, doctor bios).

Exits 1 if anything is found, 0 if the build is clean. Intended to run
in CI / right before a deploy, not as part of build.py itself, so a
build can still be inspected locally even when it fails validation.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DIST = ROOT / "dist"

errors = []
warnings = []

PLACEHOLDER_PATTERNS = [
    r"\blorem ipsum\b",
    r"\bplaceholder\b",
    r"\bTBD\b",
    r"\bTODO\b",
    r"\bundefined\b",
    r"\bNone\b",
    r"уточняется",
    r"будет добавлено",
    r"\{\{",
    r"\{%",
]

HREF_RE = re.compile(r'href="([^"]*)"')
SRC_RE = re.compile(r'src="([^"]*)"')
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DESC_RE = re.compile(r'<meta name="description" content="([^"]*)"')
CANONICAL_RE = re.compile(r'<link rel="canonical" href="([^"]*)"')


def check_html_file(path, canonicals_seen):
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(DIST).as_posix()

    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, text):
            errors.append(f"{rel}: matches placeholder/unrendered pattern /{pat}/")

    for m in re.finditer(r"elitdent\.example", text):
        context = text[max(0, m.start() - 20):m.start()]
        if "info@" not in context:
            errors.append(f"{rel}: stray elitdent.example outside the demo contact email")

    if 'href="#"' in text:
        errors.append(f'{rel}: href="#" placeholder link found')

    title_m = TITLE_RE.search(text)
    if not title_m or not title_m.group(1).strip():
        errors.append(f"{rel}: missing or empty <title>")

    desc_m = DESC_RE.search(text)
    if not desc_m or not desc_m.group(1).strip():
        errors.append(f"{rel}: missing or empty meta description")

    canon_m = CANONICAL_RE.search(text)
    if not canon_m:
        errors.append(f"{rel}: missing canonical link")
    else:
        canonicals_seen.setdefault(canon_m.group(1), []).append(rel)

    for href in HREF_RE.findall(text):
        check_internal_link(href, rel)
    for src in SRC_RE.findall(text):
        check_asset(src, rel)


def check_internal_link(href, rel):
    if not href or href.startswith(("http://", "https://", "mailto:", "tel:", "whatsapp:", "#")):
        return
    path = href.split("#")[0].split("?")[0]
    if not path:
        return
    target = DIST / path.lstrip("/") / "index.html" if path.endswith("/") else DIST / path.lstrip("/")
    if not target.exists():
        errors.append(f"{rel}: broken internal link -> {href}")


def check_asset(src, rel):
    if not src or src.startswith(("http://", "https://", "data:")):
        return
    target = DIST / src.lstrip("/")
    if not target.exists():
        errors.append(f"{rel}: missing asset -> {src}")


def check_language_parity():
    """Every /hy/... page must have a matching /ru/... and /en/... page."""
    languages = ["hy", "ru", "en"]
    page_dirs = {lang: set() for lang in languages}
    for lang in languages:
        lang_root = DIST / lang
        if not lang_root.exists():
            errors.append(f"missing top-level language directory: {lang}/")
            continue
        for index_file in lang_root.rglob("index.html"):
            page_dirs[lang].add(index_file.parent.relative_to(lang_root).as_posix())
    all_slugs = set().union(*page_dirs.values()) if page_dirs else set()
    for slug in sorted(all_slugs):
        missing = [lang for lang in languages if slug not in page_dirs[lang]]
        if missing:
            errors.append(f"page '{slug}' missing for language(s): {', '.join(missing)}")


def check_sitemap_and_robots():
    robots = DIST / "robots.txt"
    if not robots.exists():
        errors.append("robots.txt missing from dist/")
    elif "Sitemap:" not in robots.read_text(encoding="utf-8"):
        errors.append("robots.txt has no Sitemap: line")

    sitemap = DIST / "sitemap.xml"
    if not sitemap.exists():
        errors.append("sitemap.xml missing from dist/")
    else:
        text = sitemap.read_text(encoding="utf-8")
        if "elitdent.example" in text:
            errors.append("sitemap.xml contains the placeholder elitdent.example domain")
        if not text.strip().startswith("<?xml"):
            errors.append("sitemap.xml does not look like well-formed XML")


def check_data_consistency():
    site = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
    doctors = json.loads((DATA / "doctors.json").read_text(encoding="utf-8"))
    services = json.loads((DATA / "services.json").read_text(encoding="utf-8"))
    reviews = json.loads((DATA / "reviews.json").read_text(encoding="utf-8"))

    stats = {s["key"]: s["value"] for s in site.get("stats", [])}

    if stats.get("specialists") != str(len(doctors)):
        errors.append(
            f"data/site.json stats.specialists = {stats.get('specialists')!r} "
            f"but data/doctors.json has {len(doctors)} doctors"
        )
    if stats.get("treatmentAreas") != str(len(services)):
        errors.append(
            f"data/site.json stats.treatmentAreas = {stats.get('treatmentAreas')!r} "
            f"but data/services.json has {len(services)} services"
        )
    if stats.get("languages") != str(len(site["languages"]["supported"])):
        errors.append(
            f"data/site.json stats.languages = {stats.get('languages')!r} "
            f"but {len(site['languages']['supported'])} languages are configured"
        )

    rating = site.get("rating", {})
    if rating.get("count") != len(reviews["items"]):
        errors.append(
            f"data/site.json rating.count = {rating.get('count')!r} "
            f"but data/reviews.json has {len(reviews['items'])} reviews"
        )
    if reviews.get("aggregateRatingEnabled") and not site.get("featureFlags", {}).get("demoMode") is False:
        # demoMode=true + aggregateRatingEnabled=true is fine for the UI rating line,
        # but must never be paired with a fabricated AggregateRating JSON-LD block.
        for lang in site["languages"]["supported"]:
            home = DIST / lang / "index.html"
            if home.exists() and "AggregateRating" in home.read_text(encoding="utf-8"):
                errors.append(
                    f"{lang}/index.html emits AggregateRating JSON-LD while demoMode is true "
                    "— fabricated third-party rating schema is not allowed in demo mode"
                )

    doctor_slugs = {d["slug"] for d in doctors}
    service_slugs = {s["slug"] for s in services}
    for s in services:
        if s.get("doctorSlug") and s["doctorSlug"] not in doctor_slugs:
            errors.append(f"data/services.json: service '{s['slug']}' references unknown doctorSlug '{s['doctorSlug']}'")
    for d in doctors:
        for s_slug in d.get("services", []):
            if s_slug not in service_slugs:
                errors.append(f"data/doctors.json: doctor '{d['slug']}' references unknown service '{s_slug}'")
    for r in reviews["items"]:
        if r.get("serviceSlug") and r["serviceSlug"] not in service_slugs:
            errors.append(f"data/reviews.json: review '{r['id']}' references unknown serviceSlug '{r['serviceSlug']}'")

    max_experience = max((d.get("experienceYears", 0) for d in doctors), default=0)
    founded_year_gap = 2026 - site["brand"].get("foundedYear", 2026)
    if stats.get("yearsExperience", "").rstrip("+") and int(stats["yearsExperience"].rstrip("+")) > max(max_experience, founded_year_gap):
        errors.append(
            f"data/site.json stats.yearsExperience = {stats.get('yearsExperience')!r} "
            f"is higher than any doctor's experienceYears (max {max_experience}) or the clinic's own age ({founded_year_gap}y)"
        )


def main():
    if not DIST.exists():
        print("dist/ does not exist — run `python3 build.py` first.", file=sys.stderr)
        sys.exit(1)

    canonicals_seen = {}
    html_files = sorted(DIST.rglob("*.html"))
    for path in html_files:
        check_html_file(path, canonicals_seen)

    # index.html and 404.html at dist root are intentional mechanical copies
    # (a meta-refresh redirect stub to the default language, and a root 404 for
    # hosts like Vercel that look for one) — they share their canonical with the
    # real page on purpose, so they're excluded from the duplicate check.
    root_copies = {"index.html", "404.html"}
    for url, files in canonicals_seen.items():
        real_dupes = [f for f in files if f not in root_copies]
        if len(real_dupes) > 1:
            errors.append(f"duplicate canonical '{url}' used by: {', '.join(real_dupes)}")

    check_language_parity()
    check_sitemap_and_robots()
    check_data_consistency()

    print(f"Checked {len(html_files)} HTML files in {DIST}.")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        print(f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s).")
        sys.exit(1)

    print(f"\nPASSED: 0 errors, {len(warnings)} warning(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()
