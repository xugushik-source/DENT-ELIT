# ELIT DENT

Premium multilingual (Armenian / Russian / English) dental clinic website, built as
a reusable static-site engine. See `DESIGN_AUDIT.md` for the design system,
`CONTENT_REQUIRED.md` for what's real vs. placeholder, and `CUSTOMIZATION_GUIDE.md`
for how to reskin this engine for a different clinic.

## Stack

Plain HTML/CSS/vanilla JS output, generated from Jinja2 templates + JSON data by a
small Python build script. No Node, no framework, no client-side build step —
`dist/` is a complete, deployable static site as-is.

## Build

```bash
pip install -r requirements.txt
python3 build.py
```

Regenerates `dist/` from `data/`, `content/`, and `templates/`. Run this after
editing any content, then commit the updated `dist/`.

## Project layout

```
data/*.json          structured content — services, doctors, technology, reviews, site config
content/{lang}.json  UI strings per language (hy/ru/en)
templates/*.html     Jinja2 templates
static/               CSS, JS, images, brand assets (source photography lives in static/images/real/)
build.py              the generator
dist/                 generated output — this is what gets deployed
```

## Deploy

`vercel.json` points at `dist/` with no build command — Vercel serves the
already-committed static output directly. To publish a content change: run the
build locally, commit the refreshed `dist/`, push.
