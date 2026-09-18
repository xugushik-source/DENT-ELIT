# Customization Guide — ORDER PROFIT Dental Engine

ELIT DENT is the first site built on this engine, but the codebase is deliberately
data-driven so the **next** clinic doesn't require rewriting templates — it requires
new data. This is what makes it "one codebase, visually different sites" rather than
"the same site with a new logo."

## The replication contract (read this first, every time)

When the ask is "build a site like ELIT DENT for [new clinic]," it means: clone the
**mechanics** exactly, byte-for-byte, and swap only the **variable** content. It does
**not** mean redesigning, restructuring, or re-implementing anything below — a
different clinic gets different data flowing through the same machine, not a
reinterpretation of the machine. If something isn't explicitly listed as variable,
treat it as mechanical and leave it alone.

**Variable — this is what actually changes per client:**
- Brand identity: clinic name, tagline, founding year, and the client's own real logo
  files (never invent or redesign a logo — technical prep only: crop/resize/recompress
  what the client supplies, exactly as `AUDIT_V2.md` §0 and step 2 below describe).
- Color tokens (`static/css/tokens.css`) — palette/tone shifts per brand, nothing else
  in the CSS architecture changes to achieve this (see step 4).
- Contact details: phone, WhatsApp number, email, address per language, working hours,
  service-area cities, social links (only real ones — never guessed handles).
- Content data: doctors (photos, names, roles, bios, experience, education,
  certifications), services (copy, images, and — critically — **prices and the
  currency they're quoted in**, per the currency actually used in that clinic's
  market), technologies, reviews, trust stats, the rating shown.
- Photography throughout `static/images/` (aspect ratios must still match what each
  slot expects — see step 3).
- `featureFlags.demoMode` and the footer disclosure line, once real data replaces
  fictional placeholder data for that client.

**Mechanical — this stays identical across every clinic built on this engine, unless
the client explicitly asks to change the mechanic itself (not just its content):**
- The whole pipeline and file layout: `build.py`, the `data/` + `content/` + `templates/`
  + `static/` separation, directory-style URLs, and the full page set (home, services
  list/detail, doctors list/detail, technology, about, reviews, contact, 404).
- The full-screen intro splash: shown once per browser session via `sessionStorage`
  (never replayed on internal navigation), fading the client's logo in and the whole
  overlay out before the site underneath. The *logo image* is variable; the splash
  *mechanism* (timing, session-gating, fade behavior) is not.
- Breadcrumb navigation on every non-home page (`templates/partials/breadcrumb.html`):
  "Home / Section" on list pages, "Home / Section / Item" on detail pages — this is
  what lets a visitor navigate back up the hierarchy without opening the mobile menu,
  and every page must keep having it.
- The scroll-reveal system (`.reveal` / `.js-reveal`, `IntersectionObserver`-driven,
  ~80ms stagger between siblings, full `prefers-reduced-motion` fallback to static
  content) — every section on every page keeps this, not just the homepage.
- The booking modal + WhatsApp flow end to end: server-side `wa_url()` for every
  *static* WhatsApp link, the client-side message builder in `main.js` that
  interpolates name/phone/service/doctor/contact-method/message into the template
  strings from `content/{lang}.json`, and doctor-specific booking via the `data-doctor`
  attribute. **The visitor's phone number must always end up in the WhatsApp message**
  — this broke once already (see `AUDIT_V2.md` §1) and is the single most
  business-critical mechanic on the whole site; never regress it.
- Mobile nav overlay, bottom bar (Call/WhatsApp/Book), floating WhatsApp button, and
  the focus-trap/`aria-expanded`/`aria-hidden` accessibility behavior behind all of
  them.
- The SEO machinery: `SITE_URL` env-var resolution with `seo.productionUrl` fallback,
  canonical/hreflang/`x-default`/OG tags, `sitemap.xml`/`robots.txt` generation, and
  the structured data (`Dentist`/`Service`/`Person`/`BreadcrumbList`/`FAQPage`), with
  `AggregateRating` staying forbidden while `demoMode` is true.
- `validate.py`, run after every build, on every clinic, before every deploy. A new
  clinic still needs "PASSED: 0 errors" — broken links, missing translations,
  leftover placeholder text, and cross-file numeric consistency (doctor/service/review
  counts vs. the numbers quoted in `stats`) are exactly as unacceptable for client #2
  as they were for ELIT DENT.
- The visual design *system* — spacing scale, type scale, component structure (cards,
  buttons, modal, header, footer) — as opposed to the color *tokens* riding on top of
  it, which are variable (step 4).

If a change doesn't fit cleanly into "this is client data" or "this is machinery,"
stop and ask rather than guessing which bucket it belongs in.

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
2. **Replace the logo** — put the *new client's own* files in `static/brand/` and
   update `brand.logo.{full,mark,light,dark,favicon}` paths in `data/site.json`.
   Regenerate favicons from the new mark (see `generate_placeholders.py` for the
   pattern, or just crop/resize manually to 16/32/180/512px). **Important distinction:**
   the "never redesign the logo" rule documented in `AUDIT_V2.md` §0 applies to the
   *current* client (ELIT DENT) — their supplied mark must never be altered. It does
   **not** forbid swapping in a *different* client's own real logo when reskinning this
   engine for them; that's simply step 2 of onboarding a new client, same as everything
   else in this list. Never invent a logo for a client who hasn't supplied one — ask for
   the real file instead of generating a placeholder mark.
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
11. **Add prices** — each service in `data/services.json` already has a `price`
    object (`amount`, `currency`, localized `prefix`/`note`) — just replace the values;
    `service_detail.html` already renders `service.priceDisplay`/`priceNote`, no
    template change needed.
12. **Add reviews** — edit `data/reviews.json`. Only set `aggregateRatingEnabled:true`
    (and wire a real `rating.value`/`rating.count` into `data/site.json`) once real,
    verified reviews exist — never before, and never emit `AggregateRating` JSON-LD from
    fictional/demo data (see `AUDIT_V2.md` §5 for why, and `validate.py`'s
    `demoMode` check that guards it).
13. **Configure contacts** — `data/site.json → contact.*` (phone, WhatsApp, email,
    address per language, hours via `content/{lang}.json → contactPage.hours*`).
14. **Configure SEO** — `data/site.json → seo.*` (country, city, service areas, and
    `seo.productionUrl`, the fallback used when the `SITE_URL` environment variable
    isn't set — see step 17). This drives canonical/hreflang/OG/sitemap URLs everywhere;
    nothing else hardcodes a domain.
15. **Turn off demo mode** — set `featureFlags.demoMode:false` in `data/site.json` once
    all content above is real (not fictional). Update the trilingual footer disclosure
    (`content/{lang}.json → footer.disclosure`) to reflect the live clinic, or clear it
    if the agency wants no such line at all.
16. **Build** — `python3 build.py`.
17. **Validate before shipping** — `python3 validate.py`. Must report "PASSED: 0
    errors" — it catches broken links/images, missing translations, leftover
    placeholder text, and cross-file inconsistencies (doctor/service/review counts vs.
    the numbers quoted in `stats`) before they reach production. Set the `SITE_URL`
    environment variable to the real client domain before this final build:
    `SITE_URL=https://realclinic.com python3 build.py && python3 validate.py`.
18. **Deploy** — `dist/` is a complete static site: upload it as-is to any static host
    (Netlify, S3+CloudFront, GitHub Pages, nginx, Vercel with `outputDirectory: dist`
    and no build command, etc.). `dist/lang/404.html` is a flat file specifically so
    hosts that support custom per-path error pages can use it directly.

## Feature flags

`data/site.json → featureFlags` is the intended config surface for gating whole
sections/features without touching templates: `servicesEnabled`,
`doctorProfilesEnabled`, `technologyEnabled`, `reviewsEnabled`, `beforeAfterEnabled`,
`galleryEnabled`, `bookingEnabled`, `whatsappEnabled`, `offersEnabled`, `blogEnabled`,
`multilingualEnabled`, `demoMode` (see item 15 above). **Note for the next engineer:**
only `demoMode` and `homepageSections` (item 7 above) are actually read by
`build.py`/templates today — see `AUDIT_V2.md` §9 for the full, honest status. Don't
assume toggling e.g. `reviewsEnabled: false` alone removes the `/reviews/` page or its
nav item; today that still means removing it from `homepageSections` and editing the
relevant template/nav conditional by hand. Wiring every flag through end-to-end
(including nav items and standalone list/detail pages) is the next reusability
milestone.

## What's genuinely reusable today vs. what still needs generalizing

**Reusable as-is:** design tokens, header/footer/nav/modal/bottom-bar components,
service/doctor/technology data schema, the Jinja2 build pipeline, hreflang/sitemap
generation, the WhatsApp deep-link + booking-modal mechanism, the intro splash
screen, breadcrumb navigation on every page, the scroll-reveal animation system, and
`validate.py`'s full check suite.

**Still ELIT-DENT-specific and would need generalizing for a very different clinic
shape:** the fixed list of 12 service categories (a different specialty clinic — e.g.
orthodontics-only — would want fewer, differently-named services, which just means
editing `data/services.json`, not code); the 5-step process template is shared across
all services (per brief §21) rather than fully independent per service — that's a
deliberate content-volume trade-off, documented in `DESIGN_AUDIT.md` §13, not an
oversight.
