#!/usr/bin/env python3
"""
Generates tasteful placeholder SVG images for every photography slot referenced
in /data/*.json, until the real ELIT DENT photoshoot (Gemini-generated assets
per the project brief) is supplied. Each placeholder is clearly watermarked
"Photography pending" in a corner so nobody mistakes it for final content —
see CONTENT_REQUIRED.md item MEDIA-1.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUT = ROOT / "static" / "images"

PALETTE_PAIRS = [
    ("#F1EBE0", "#E4DBCB"),
    ("#EFE3CF", "#D9C8A6"),
    ("#F6F1E8", "#E4DBCB"),
    ("#ECE3D2", "#D6C6A4"),
]

ICONS = {
    "implant": '<path d="M50 20 v35 M35 55 q15 15 30 0 M40 90 q10 -15 20 0" stroke-linecap="round"/>',
    "sparkle": '<path d="M50 25 L55 45 L75 50 L55 55 L50 75 L45 55 L25 50 L45 45 Z"/>',
    "aligner": '<ellipse cx="50" cy="50" rx="28" ry="18"/><path d="M25 50 h50" />',
    "crown": '<path d="M25 60 L35 35 L50 50 L65 35 L75 60 Z" /><path d="M25 60 h50 v10 h-50 Z"/>',
    "tooth": '<path d="M50 25 c-15 0 -22 10 -20 25 c1 10 6 25 12 25 c4 0 4 -10 8 -10 c4 0 4 10 8 10 c6 0 11 -15 12 -25 c2 -15 -5 -25 -20 -25 Z"/>',
    "cleaning": '<circle cx="50" cy="45" r="18"/><path d="M50 63 v20" stroke-linecap="round"/>',
    "root-canal": '<circle cx="50" cy="50" r="22" fill="none"/><path d="M50 35 v30 M35 50 h30" stroke-linecap="round"/>',
    "gum": '<path d="M25 60 q25 -30 50 0 q-25 20 -50 0 Z"/>',
    "surgery": '<path d="M30 30 L70 70 M70 30 L30 70" stroke-linecap="round"/>',
    "scan": '<rect x="28" y="28" width="44" height="44" rx="6" fill="none"/><path d="M28 40 h44 M28 60 h44" />',
    "family": '<circle cx="38" cy="38" r="10"/><circle cx="62" cy="38" r="10"/><path d="M22 75 q16 -20 32 0 M46 75 q16 -20 32 0" fill="none"/>',
    "whitening": '<path d="M50 25 L58 45 L50 75 L42 45 Z"/>',
    "cbct": '<circle cx="50" cy="50" r="24" fill="none"/><circle cx="50" cy="50" r="10" fill="none"/>',
    "scanner": '<rect x="25" y="35" width="50" height="30" rx="6" fill="none"/><path d="M35 35 v-8 M65 35 v-8" stroke-linecap="round"/>',
    "microscope": '<path d="M40 75 h20 M50 75 V55 M35 55 h30 l-6 -25 h-18 Z" fill="none"/>',
    "planning": '<rect x="28" y="25" width="44" height="50" rx="4" fill="none"/><path d="M36 40 h28 M36 50 h28 M36 60 h18"/>',
}

LABEL_RE = re.compile(r"[/.]")


def slug_label(path: str) -> str:
    name = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return name.replace("-", " ").title()


def make_svg(path: str, icon_key: str | None, seed: int) -> str:
    bg1, bg2 = PALETTE_PAIRS[seed % len(PALETTE_PAIRS)]
    icon = ICONS.get(icon_key, ICONS["tooth"])
    label = slug_label(path)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" role="img" aria-label="{label} — placeholder photography">
<defs>
<linearGradient id="g{seed}" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{bg1}"/>
<stop offset="1" stop-color="{bg2}"/>
</linearGradient>
</defs>
<rect width="400" height="300" fill="url(#g{seed})"/>
<g transform="translate(160,100) scale(0.8)" fill="none" stroke="#B8925A" stroke-width="2.5" opacity="0.55">
{icon}
</g>
<text x="20" y="280" font-family="sans-serif" font-size="11" fill="#6B6459" opacity="0.75">ELIT DENT — photography pending</text>
</svg>'''


def main():
    paths = {}  # path -> icon key

    services = json.load(open(DATA / "services.json", encoding="utf-8"))
    for s in services:
        paths[s["cardImage"]] = s["icon"]
        paths[s["heroImage"]] = s["icon"]

    doctors = json.load(open(DATA / "doctors.json", encoding="utf-8"))
    for d in doctors:
        paths[d["photo"]] = "family"
        paths[d["workingPhoto"]] = "family"

    technology = json.load(open(DATA / "technology.json", encoding="utf-8"))
    for tItem in technology:
        paths[tItem["image"]] = tItem["icon"]

    paths["/images/hero/doctor-hero.svg"] = "family"
    paths["/images/cta/final-cta.svg"] = "family"

    for i, (path, icon_key) in enumerate(sorted(paths.items())):
        rel = path.lstrip("/")
        assert rel.startswith("images/")
        out_path = ROOT / "static" / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(make_svg(path, icon_key, i), encoding="utf-8")

    print(f"Generated {len(paths)} placeholder images under {OUT}")


if __name__ == "__main__":
    main()
