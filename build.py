#!/usr/bin/env python3
"""
ELIT DENT / ORDER PROFIT dental engine — static site generator.

Reads /data (structured content) + /content/{lang}.json (UI strings) and
renders /templates through Jinja2 into /dist/{lang}/... This is the
"reusable engine" referenced in CUSTOMIZATION_GUIDE.md: swapping the JSON
in /data and /content, plus the tokens in static/css/tokens.css, is enough
to reskin the whole site for a different clinic without touching templates.
"""
import json
import os
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
DATA = ROOT / "data"
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

SITE_URL = None  # resolved in main(): $SITE_URL env var, else data/site.json -> seo.productionUrl


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def slugify_href(lang_prefix, *parts):
    return "/" + "/".join([lang_prefix.strip("/")] + [p.strip("/") for p in parts if p]) + "/"


def localize_service(raw, lang, lang_prefix, doctors_by_slug, tech_by_slug, services_by_slug):
    href = slugify_href(lang_prefix, "services", raw["slug"])
    doctor = None
    if raw.get("doctorSlug") and raw["doctorSlug"] in doctors_by_slug:
        d = doctors_by_slug[raw["doctorSlug"]]
        doctor = {
            "slug": d["slug"],
            "name": d["name"],
            "role": d["role"][lang],
            "photo": d["photo"],
            "href": slugify_href(lang_prefix, "doctors", d["slug"]),
        }
    technologies = []
    for t_slug in raw.get("technologyRefs", []):
        t = tech_by_slug.get(t_slug)
        if t:
            technologies.append({
                "slug": t["slug"],
                "name": t["name"][lang],
                "shortExplain": t["shortExplain"][lang],
                "image": t["image"],
            })
    related = []
    for r_slug in raw.get("relatedSlugs", []):
        r = services_by_slug.get(r_slug)
        if r:
            related.append({
                "slug": r["slug"],
                "title": r["title"][lang],
                "shortCopy": r["shortCopy"][lang],
                "cardImage": r["cardImage"],
                "href": slugify_href(lang_prefix, "services", r["slug"]),
            })
    faq = [{"q": item["q"][lang], "a": item["a"][lang]} for item in raw.get("faq", [])]
    return {
        "slug": raw["slug"],
        "icon": raw["icon"],
        "flagship": raw.get("flagship", False),
        "href": href,
        "cardImage": raw["cardImage"],
        "heroImage": raw["heroImage"],
        "eyebrow": raw["eyebrow"][lang],
        "title": raw["title"][lang],
        "shortCopy": raw["shortCopy"][lang],
        "intro": raw["intro"][lang],
        "aboutTreatment": raw["aboutTreatment"][lang],
        "whoItIsFor": raw["whoItIsFor"][lang],
        "benefits": raw["benefits"][lang],
        "faq": faq,
        "priceNote": raw["price"]["note"][lang],
        "priceDisplay": f"{raw['price']['prefix'][lang]} {raw['price']['amount']} {raw['price']['currency']}",
        "doctor": doctor,
        "technologies": technologies,
        "related": related,
    }


def localize_doctor(raw, lang, lang_prefix, services_by_slug):
    services = []
    for s_slug in raw.get("services", []):
        s = services_by_slug.get(s_slug)
        if s:
            services.append({
                "slug": s["slug"],
                "title": s["title"][lang],
                "href": slugify_href(lang_prefix, "services", s["slug"]),
            })
    certifications = [
        {"id": c["id"], "label": c["label"][lang]}
        for c in raw.get("certifications", [])
    ]
    return {
        "slug": raw["slug"],
        "name": raw["name"],
        "role": raw["role"][lang],
        "photo": raw["photo"],
        "workingPhoto": raw["workingPhoto"],
        "quote": raw["quote"][lang],
        "bio": raw["bio"][lang],
        "languages": raw["languages"],
        "services": services,
        "href": slugify_href(lang_prefix, "doctors", raw["slug"]),
        "experienceYears": raw.get("experienceYears"),
        "education": raw.get("education", {}).get(lang, []),
        "certifications": certifications,
    }


def localize_technology(raw, lang):
    return {
        "slug": raw["slug"],
        "icon": raw["icon"],
        "image": raw["image"],
        "name": raw["name"][lang],
        "shortExplain": raw["shortExplain"][lang],
        "patientBenefit": raw["patientBenefit"][lang],
    }


def localize_review(raw, lang, services_by_slug):
    service_title = None
    if raw.get("serviceSlug") and raw["serviceSlug"] in services_by_slug:
        service_title = services_by_slug[raw["serviceSlug"]]["title"][lang]
    return {
        "id": raw["id"],
        "authorInitial": raw["authorInitial"][lang],
        "quote": raw["quote"][lang],
        "serviceTitle": service_title,
    }


def build_nav_items(t, lang_prefix, active_key):
    entries = [
        ("home", slugify_href(lang_prefix)),
        ("services", slugify_href(lang_prefix, "services")),
        ("doctors", slugify_href(lang_prefix, "doctors")),
        ("technology", slugify_href(lang_prefix, "technology")),
        ("about", slugify_href(lang_prefix, "about")),
        ("reviews", slugify_href(lang_prefix, "reviews")),
        ("contact", slugify_href(lang_prefix, "contact")),
    ]
    return [
        {"key": key, "href": href, "label": t["nav"][key], "active": key == active_key}
        for key, href in entries
    ]


def breadcrumb_list_schema(items, site_url):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": item["name"], "item": site_url + item["href"]}
            for i, item in enumerate(items)
        ],
    }


def main():
    global SITE_URL
    site = load_json(DATA / "site.json")
    SITE_URL = os.environ.get("SITE_URL") or site["seo"]["productionUrl"]
    SITE_URL = SITE_URL.rstrip("/")
    services_raw = load_json(DATA / "services.json")
    doctors_raw = load_json(DATA / "doctors.json")
    technology_raw = load_json(DATA / "technology.json")
    reviews_raw = load_json(DATA / "reviews.json")
    process_default = load_json(DATA / "process-default.json")

    content = {lang: load_json(CONTENT / f"{lang}.json") for lang in site["languages"]["supported"]}

    services_by_slug = {s["slug"]: s for s in services_raw}
    doctors_by_slug = {d["slug"]: d for d in doctors_raw}
    tech_by_slug = {t["slug"]: t for t in technology_raw}

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    wa_number = site["contact"]["whatsappNumber"]
    env.globals["wa_url"] = lambda message: "https://wa.me/" + wa_number + "?text=" + quote(message)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    all_pages = []  # for sitemap: (lang, path)
    languages = site["languages"]["supported"]

    for lang in languages:
        t = content[lang]
        lang_prefix = f"/{lang}"

        services = [localize_service(s, lang, lang_prefix, doctors_by_slug, tech_by_slug, services_by_slug) for s in services_raw]
        doctors = [localize_doctor(d, lang, lang_prefix, services_by_slug) for d in doctors_raw]
        technologies = [localize_technology(tt, lang) for tt in technology_raw]
        reviews = [localize_review(r, lang, services_by_slug) for r in reviews_raw["items"]]

        def base_ctx(canonical_path, active_key, page_title, page_description, page_slug_for_translation):
            translations = {l: f"/{l}{page_slug_for_translation}" for l in languages}
            return {
                "lang": lang,
                "t": t,
                "site": site,
                "site_url": SITE_URL,
                "asset_prefix": "",
                "lang_prefix": lang_prefix,
                "home_url": slugify_href(lang_prefix),
                "nav_items": build_nav_items(t, lang_prefix, active_key),
                "translations": translations,
                "canonical_path": canonical_path,
                "page_title": f"{page_title} — {site['brand']['clinicName']}",
                "page_description": page_description,
                "whatsapp_default_message": t["whatsapp"]["defaultMessage"],
                "all_services": services,
                "footer_services": [{"title": s["title"], "href": s["href"]} for s in services[:6]],
                "current_year": date.today().year,
                "structured_data": None,
                "rating": site["rating"],
            }

        # ---- Home ----
        ctx = base_ctx(slugify_href(lang_prefix), "home", t["meta"]["titleSuffix"], t["hero"]["description"], "/")
        ctx.update({
            "services_home": services[:6],
            "doctors_home": doctors[:3],
            "technologies": technologies,
            "reviews": reviews[:3],
            "doctor_spotlight": doctors[0],
        })
        org_schema = {
            "@context": "https://schema.org",
            "@type": "Dentist",
            "name": site["brand"]["clinicName"],
            "telephone": site["contact"]["phone"],
        }
        ctx["structured_data"] = json.dumps(org_schema, ensure_ascii=False)
        html = env.get_template("pages/home.html").render(**ctx)
        write_file(DIST / lang / "index.html", html)
        all_pages.append((lang, f"/{lang}/"))

        # ---- Services list ----
        ctx = base_ctx(slugify_href(lang_prefix, "services"), "services", t["servicesPage"]["title"], t["servicesPage"]["description"], "/services/")
        ctx["services"] = services
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["services"], "href": slugify_href(lang_prefix, "services")},
        ]
        html = env.get_template("pages/services.html").render(**ctx)
        write_file(DIST / lang / "services" / "index.html", html)
        all_pages.append((lang, f"/{lang}/services/"))

        # ---- Service detail pages ----
        for s in services:
            ctx = base_ctx(s["href"], "services", s["title"], s["shortCopy"], f"/services/{s['slug']}/")
            ctx["service"] = s
            ctx["process_steps"] = [
                {"step": step["step"], "title": step["title"][lang], "desc": step["desc"][lang]}
                for step in process_default
            ]
            breadcrumb = [
                {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
                {"name": t["nav"]["services"], "href": slugify_href(lang_prefix, "services")},
                {"name": s["title"], "href": s["href"]},
            ]
            ctx["breadcrumb"] = breadcrumb
            schema = {
                "@context": "https://schema.org",
                "@graph": [
                    breadcrumb_list_schema(breadcrumb, SITE_URL),
                    {
                        "@context": "https://schema.org",
                        "@type": "Service",
                        "name": s["title"],
                        "description": s["shortCopy"],
                        "provider": {"@type": "Dentist", "name": site["brand"]["clinicName"]},
                    },
                ] + ([{
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": [
                        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                        for f in s["faq"]
                    ],
                }] if s["faq"] else []),
            }
            ctx["structured_data"] = json.dumps(schema, ensure_ascii=False)
            html = env.get_template("pages/service_detail.html").render(**ctx)
            write_file(DIST / lang / "services" / s["slug"] / "index.html", html)
            all_pages.append((lang, s["href"]))

        # ---- Doctors list ----
        ctx = base_ctx(slugify_href(lang_prefix, "doctors"), "doctors", t["doctorsPage"]["title"], t["doctorsPage"]["description"], "/doctors/")
        ctx["doctors"] = doctors
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["doctors"], "href": slugify_href(lang_prefix, "doctors")},
        ]
        html = env.get_template("pages/doctors.html").render(**ctx)
        write_file(DIST / lang / "doctors" / "index.html", html)
        all_pages.append((lang, f"/{lang}/doctors/"))

        # ---- Doctor detail pages ----
        for d in doctors:
            ctx = base_ctx(d["href"], "doctors", d["name"], d["bio"], f"/doctors/{d['slug']}/")
            ctx["doctor"] = d
            breadcrumb = [
                {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
                {"name": t["nav"]["doctors"], "href": slugify_href(lang_prefix, "doctors")},
                {"name": d["name"], "href": d["href"]},
            ]
            ctx["breadcrumb"] = breadcrumb
            schema = {"@context": "https://schema.org", "@graph": [
                breadcrumb_list_schema(breadcrumb, SITE_URL),
                {"@context": "https://schema.org", "@type": "Person", "name": d["name"], "jobTitle": d["role"], "worksFor": {"@type": "Dentist", "name": site["brand"]["clinicName"]}},
            ]}
            ctx["structured_data"] = json.dumps(schema, ensure_ascii=False)
            html = env.get_template("pages/doctor_detail.html").render(**ctx)
            write_file(DIST / lang / "doctors" / d["slug"] / "index.html", html)
            all_pages.append((lang, d["href"]))

        # ---- Technology ----
        ctx = base_ctx(slugify_href(lang_prefix, "technology"), "technology", t["technologyPage"]["title"], t["technologyPage"]["description"], "/technology/")
        ctx["technologies"] = technologies
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["technology"], "href": slugify_href(lang_prefix, "technology")},
        ]
        html = env.get_template("pages/technology.html").render(**ctx)
        write_file(DIST / lang / "technology" / "index.html", html)
        all_pages.append((lang, f"/{lang}/technology/"))

        # ---- About ----
        ctx = base_ctx(slugify_href(lang_prefix, "about"), "about", t["aboutPage"]["title"], t["aboutPage"]["title"], "/about/")
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["about"], "href": slugify_href(lang_prefix, "about")},
        ]
        html = env.get_template("pages/about.html").render(**ctx)
        write_file(DIST / lang / "about" / "index.html", html)
        all_pages.append((lang, f"/{lang}/about/"))

        # ---- Reviews ----
        ctx = base_ctx(slugify_href(lang_prefix, "reviews"), "reviews", t["reviewsPage"]["title"], t["reviewsPage"]["description"], "/reviews/")
        ctx["reviews"] = reviews
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["reviews"], "href": slugify_href(lang_prefix, "reviews")},
        ]
        html = env.get_template("pages/reviews.html").render(**ctx)
        write_file(DIST / lang / "reviews" / "index.html", html)
        all_pages.append((lang, f"/{lang}/reviews/"))

        # ---- Contact ----
        ctx = base_ctx(slugify_href(lang_prefix, "contact"), "contact", t["contactPage"]["title"], t["contactPage"]["description"], "/contact/")
        ctx["breadcrumb"] = [
            {"name": t["nav"]["home"], "href": slugify_href(lang_prefix)},
            {"name": t["nav"]["contact"], "href": slugify_href(lang_prefix, "contact")},
        ]
        html = env.get_template("pages/contact.html").render(**ctx)
        write_file(DIST / lang / "contact" / "index.html", html)
        all_pages.append((lang, f"/{lang}/contact/"))

        # ---- 404 ----
        # Written as a flat lang/404.html (not lang/404/index.html) since that's
        # the file shape static hosts (Netlify, S3, GitHub Pages, etc.) look for
        # as a custom per-path error page — so its canonical/hreflang must point
        # at the flat .html path too, not the directory-style URLs every other
        # page uses.
        ctx = base_ctx(f"/{lang}/404.html", "home", t["notFound"]["title"], t["notFound"]["description"], "/404.html")
        ctx["robots_noindex"] = True
        html = env.get_template("pages/404.html").render(**ctx)
        write_file(DIST / lang / "404.html", html)

    # ---- Root redirect (default language) ----
    default_lang = site["languages"]["default"]
    redirect_html = f"""<!doctype html>
<html lang="{default_lang}">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=/{default_lang}/">
<meta name="description" content="{site['brand']['clinicName']} — {site['brand']['tagline'][default_lang]}.">
<link rel="canonical" href="{SITE_URL}/{default_lang}/">
<title>{site['brand']['clinicName']}</title>
</head>
<body><p><a href="/{default_lang}/">{site['brand']['clinicName']}</a></p></body>
</html>"""
    write_file(DIST / "index.html", redirect_html)

    # ---- Root 404 (for hosts that look for a top-level 404.html, e.g. Vercel) ----
    shutil.copy(DIST / default_lang / "404.html", DIST / "404.html")

    # ---- robots.txt ----
    robots = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"
    write_file(DIST / "robots.txt", robots)

    # ---- sitemap.xml ----
    urlset = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    seen = set()
    for lang, path in all_pages:
        if path in seen:
            continue
        seen.add(path)
        alt_links = "".join(
            f'<xhtml:link rel="alternate" hreflang="{l}" href="{SITE_URL}/{l}{path[len("/"+lang):]}"/>'
            for l in languages
        )
        urlset.append(f'<url><loc>{SITE_URL}{path}</loc>{alt_links}</url>')
    urlset.append("</urlset>")
    write_file(DIST / "sitemap.xml", "\n".join(urlset))

    # ---- Copy static assets ----
    shutil.copytree(STATIC / "css", DIST / "css", dirs_exist_ok=True)
    shutil.copytree(STATIC / "js", DIST / "js", dirs_exist_ok=True)
    shutil.copytree(STATIC / "images", DIST / "images", dirs_exist_ok=True,
                     ignore=shutil.ignore_patterns("real"))
    shutil.copytree(STATIC / "brand", DIST / "brand", dirs_exist_ok=True,
                     ignore=shutil.ignore_patterns("source"))
    for favicon_name in ("favicon-16.png", "favicon-32.png", "apple-touch-icon.png", "favicon-512.png"):
        src = STATIC / favicon_name
        if src.exists():
            shutil.copy(src, DIST / favicon_name)

    print(f"Built {len(all_pages)} pages across {len(languages)} languages into {DIST}")


if __name__ == "__main__":
    main()
