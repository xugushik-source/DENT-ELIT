# Customization Guide — ORDER PROFIT Dental Engine

ELIT DENT is the first site built on this engine, but the codebase is deliberately
data-driven so the **next** clinic doesn't require rewriting templates — it requires
new data. This is what makes it "one codebase, visually different sites" rather than
"the same site with a new logo."

## How the build actually works

```
data/*.json        → structured content: services, doctors, technology, reviews, site config
content/{lang}.json → UI strings per language (nav, buttons, section headings, etc.)
templates/*.html    → Jinja2 templates (rarely need to change per clinic)
static/css/*.css    → design tokens + component styles
static/images/...   → photography
build.py            → renders data + content + templates → dist/{lang}/...
```

Run `python3 build.py` any time data/content/templates change. It's a full rebuild
(deletes and regenerates `dist/`), takes well under a second, and needs no Node/npm —
only Python 3 + Jinja2 (`pip install jinja2`).

## Step-by-step: turning this into a different clinic's site

1. **Change clinic config** — edit `data/site.json`: `brand.clinicName`, `brand.tagline`,
   `contact.*`, `languages.supported`/`default`, `featureFlags.*`.
2. **Replace the logo** — put new files in `static/brand/` and update
   `brand.logo.{full,mark,light,dark,favicon}` paths in `data/site.json`. Regenerate
   favicons from the new mark (see `generate_placeholders.py` for the pattern, or just
   crop/resize manually to 16/32/180/512px).
3. **Replace photography** — swap files under `static/images/` (same relative paths
   referenced in `data/services.json` / `data/doctors.json` / `data/technology.json`,
   or update those paths to new filenames). Keep aspect-ratio expectations in mind:
   service cards are 4:3, doctor portraits 3:4, technology shots 16:10, hero ~4:5
   (mobile) / 16:12 (desktop) — see `DESIGN_AUDIT.md` §9.
4. **Select a palette** — edit the color tokens in `static/css/tokens.css`
   (`--color-bg`, `--color-accent`, etc.). Everything else (buttons, cards, header)
   references these tokens, so a palette swap is a handful of line edits, not a
   find-and-replace across templates.
5. **Select fonts** — swap the `@import` in `static/css/main.css` and the
   `--font-heading`/`--font-body` tokens. **Verify Armenian/Cyrillic glyph coverage
   before committing to a font** — this was the reason Noto Serif/Sans were chosen for
   ELIT DENT over a prettier Latin-only display face (see `DESIGN_AUDIT.md` §4).
6. **Select a hero variant** — `data/site.json → visual.heroVariant` is read but only
   `doctorFocus` (the current split hero) is implemented. Building a second variant
   (e.g. `fullscreen`) means adding a new `templates/partials/home/hero.html` variant
   and branching on this value — not yet built, flagged here so it isn't mistaken for
   a bug.
7. **Select section order** — `data/site.json → homepageSections` is a plain ordered
   list (`["hero","trust","services",...]`). Reorder, remove, or add entries and the
   homepage rebuilds accordingly — each entry maps to
   `templates/partials/home/<name>.html`. Adding a new section type means adding that
   one partial file; no other template needs touching.
8. **Add/remove services** — edit `data/services.json`. Each entry is self-contained
   (content in `hy`/`ru`/`en`, image paths, related slugs, doctor slug, technology
   refs, FAQ). The service listing page and all service detail pages regenerate
   automatically — no template changes needed for a different service count.
9. **Add/remove doctors** — same pattern in `data/doctors.json`.
10. **Add/remove technologies** — same pattern in `data/technology.json`.
11. **Add prices** — extend the `price` object per service
    (`data/services.json`) with real `amount`/`currency` once available, and adjust
    the pricing block in `templates/pages/service_detail.html` to render them instead
    of just the note.
12. **Add reviews** — edit `data/reviews.json`. Set `isDemo:false` once verified, and
    `aggregateRatingEnabled:true` (plus wire in real rating/count) only once real
    Google/verified data exists — never before.
13. **Configure contacts** — `data/site.json → contact.*`.
14. **Configure SEO** — `data/site.json → seo.*` (country, city, service areas, and
    critically `seo.siteUrlPlaceholder`, which drives canonical/hreflang/sitemap URLs
    everywhere — set it to the real domain before deploying).
15. **Build** — `python3 build.py`.
16. **Deploy** — `dist/` is a complete static site: upload it as-is to any static host
    (Netlify, S3+CloudFront, GitHub Pages, nginx, etc.). `dist/lang/404.html` is a flat
    file specifically so hosts that support custom per-path error pages can use it
    directly.

## Feature flags

`data/site.json → featureFlags` gates whole sections/features without touching
templates: `servicesEnabled`, `doctorProfilesEnabled`, `technologyEnabled`,
`reviewsEnabled`, `beforeAfterEnabled`, `galleryEnabled`, `bookingEnabled`,
`whatsappEnabled`, `offersEnabled`, `blogEnabled`, `multilingualEnabled`. **Note for
the next engineer:** these flags are currently declared as the config surface but not
yet all wired into `build.py`/templates to actually skip rendering — today, disabling
a section means removing it from `homepageSections` (item 7 above) or editing the
relevant template's conditional. Wiring every flag through is the next reusability
milestone, not done in this pass — don't assume toggling `reviewsEnabled: false` alone
currently removes the reviews page.

## What's genuinely reusable today vs. what still needs generalizing

**Reusable as-is:** design tokens, header/footer/nav/modal/bottom-bar components,
service/doctor/technology data schema, the Jinja2 build pipeline, hreflang/sitemap
generation, the WhatsApp deep-link + booking-modal mechanism.

**Still ELIT-DENT-specific and would need generalizing for a very different clinic
shape:** the fixed list of 12 service categories (a different specialty clinic — e.g.
orthodontics-only — would want fewer, differently-named services, which just means
editing `data/services.json`, not code); the 5-step process template is shared across
all services (per brief §21) rather than fully independent per service — that's a
deliberate content-volume trade-off, documented in `DESIGN_AUDIT.md` §13, not an
oversight.
