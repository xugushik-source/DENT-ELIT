# ELIT DENT — Audit V2 (demo-to-production readiness pass)

This is the second audit pass, run against the working site built in `DESIGN_AUDIT.md`
(visual system) and `CONTENT_REQUIRED.md` (photo mapping). Its job was different: not
"does this look premium," but "does this read as a finished, internally consistent,
honest commercial product" — no scattered demo labels, no dead links, a complete
fictional dataset, correct SEO, and a fixed booking flow. Findings below are grouped by
severity/category, each marked with what was found and what was done about it. Every
item marked **FIXED** has been verified against a rebuilt `dist/` and `python3
validate.py` (see that file for the automated checks that now guard this).

## 0. Logo integrity — read first

Per explicit, repeated client instruction, **no new or modified logo was created at any
point in this pass.** The original client-supplied files were only technically prepared
(cropped/resized/recompressed) for web use — never redesigned.

- **ORIGINAL LOGO SOURCE FILES (client-supplied, untouched):**
  `static/brand/source/logo-source-dark-hero.png`,
  `static/brand/source/logo-source-wall-signage.png`
- **PRODUCTION LOGO FILES (technical crops/exports of the above, same mark/wordmark):**
  `static/brand/logo-full-light.png`, `static/brand/logo-full-dark.png`,
  `static/brand/logo-mark-light.png`, referenced from `data/site.json → brand.logo.*`
  and used unchanged in `templates/partials/header.html`, `footer.html`, and favicons.
- The `source/` subfolder is intentionally excluded from `dist/` (see
  `build.py`'s `shutil.copytree(..., ignore=shutil.ignore_patterns("source"))`) so the
  originals stay in the repo for provenance but never ship as extra unused assets.

No further logo work is in scope or should be attempted by anyone maintaining this site.

## 1. CRITICAL

- **Booking form silently dropped the visitor's phone number.** The WhatsApp message
  built on submit never read the `phone` field — a lead's own callback number never
  reached the clinic. **FIXED**: `static/js/main.js` now reads `phone` and every
  language's `whatsapp.bookingMessageTemplate` includes `{phone}`.
- **Doctor detail pages had no way to book with that specific doctor** — the booking CTA
  opened the generic modal with no doctor context, so a WhatsApp lead from a doctor's
  page lost which doctor the visitor actually wanted. **FIXED**: `data-doctor="{{
  doctor.name }}"` on the doctor-page CTA now flows through `openModal()` into a
  `doctorClause` inserted into the WhatsApp message (`main.js` + new
  `whatsapp.doctorClauseTemplate` strings).
- **Content/photo gender mismatch**: `doctors.json` named the general/family dentist
  "Dr. Narek Sargsyan" (a male name) but the assigned portrait (Gemini `photo_04.jpg`,
  reused as `narine-sargsyan.jpg`) depicts a female dentist. **FIXED**: renamed the
  doctor (slug, display name, image filename) to "Dr. Narine Sargsyan" throughout
  `data/doctors.json`, `data/services.json` (`doctorSlug` refs), and
  `CONTENT_REQUIRED.md`; bio/quote copy in all three languages was already
  gender-neutral, so no other text needed changing. Verified zero remaining "Narek"
  occurrences anywhere in `data/`, `content/`, `templates/`, or `dist/`.

## 2. HIGH

- **`elitdent.example` was hardcoded** as the canonical/hreflang/OG/sitemap domain in
  `build.py`, which would have shipped a broken placeholder domain to production.
  **FIXED**: `SITE_URL` is now resolved as `os.environ.get("SITE_URL") or
  site["seo"]["productionUrl"]` (falls back to `https://dent-elit.vercel.app`); set the
  env var to the real client domain at deploy time and nothing else needs touching.
  `elitdent.example` now appears exactly once sitewide, intentionally, as the fictional
  demo contact email (`info@elitdent.example`) — `validate.py` asserts this.
- **WhatsApp links used `href="#"` rewritten by client-side JS** on page load — a
  conversion-critical link with a broken href until JS finished running, and flagged by
  this project's own no-`href="#"` rule. **FIXED**: moved static WhatsApp link
  generation into a Jinja2 build-time global (`wa_url()` in `build.py`), so every static
  WhatsApp link ships as a real `https://wa.me/...` URL in the HTML. Only the
  booking-modal message (built from live form input) still needs client-side JS, which
  is unavoidable — its target `wa.me` number is still resolved server-side.
- **Scattered "demo" labels instead of one disclosure.** Per-review "Demo review"
  badges and inline demo disclaimers existed on multiple pages. **FIXED**: removed all
  of them; replaced with exactly one small, muted, trilingual line in the footer
  (`t.footer.disclosure`, styled `.footer-disclosure` in `main.css`) and a `demoMode`
  feature flag in `site.json` that documents the intent even though no UI currently
  branches on it beyond suppressing `AggregateRating` schema (§5).
- **Contact page admitted it had no map**: `contactPage.mapNote` literally said "a map
  will appear here once connected" in all three languages — exactly the kind of
  unfinished-looking copy this pass was meant to remove. **FIXED**: replaced the dashed
  placeholder box with a real, working location card — clinic address plus a "Open
  directions in Google Maps" link built from the address itself
  (`https://www.google.com/maps/search/?api=1&query=...`, no API key, no fabricated
  business listing). `static/css/main.css`'s `.map-placeholder` renamed to `.map-card`.

## 3. MEDIUM

- **No fictional operating data existed** — no address, hours, email, founding year,
  doctor credentials, or prices; the site read as a shell. **FIXED**: built one coherent
  fictional dataset — Tbilisi address (`data/site.json → contact.address`), working
  hours, `info@elitdent.example` (marked `emailIsLive:false`), `foundedYear: 2014`, and
  per-doctor `experienceYears`/`education`/`certifications` (format
  `DEMO-GE-<SPECIALTY>-2026-0NN`, clearly fictional, never resembling a real license
  registry format). See §6 for why this is safe rather than misleading.
- **No pricing anywhere.** **FIXED**: every service in `data/services.json` now has a
  `price` object (amount, currency `₾`, localized prefix/note), rendered on service
  detail pages.
- **No patient reviews, no rating.** **FIXED**: 11 varied, non-repetitive fictional
  reviews (`data/reviews.json`), each tied to a real `serviceSlug`; a `rating: {value:
  4.9, count: 11}` shown as a "★ 4.9 · Patient rating (11)" line — see §5 for why this
  is UI-only and not emitted as schema.
- **No payment or sterilization/safety information** — a real prospective patient's two
  most common pre-booking questions. **FIXED**: added both as dedicated sections on the
  contact page (`contactPage.paymentOptions`, `contactPage.safetyItems`), plus a general
  FAQ accordion distinct from the per-service FAQs.
- **Accessibility gaps in the booking modal and mobile nav**: no focus trap, no focus
  restore on close, no `aria-expanded`/`aria-hidden` state, missing `autocomplete`/
  `inputmode` on form fields. **FIXED**: `static/js/main.js` gained `getFocusable()` /
  `trapFocus()` helpers used by both the mobile-nav overlay and the booking modal;
  `aria-expanded`/`aria-hidden` now toggle correctly; `lastFocusedEl` is restored on
  close; phone input has `autocomplete="tel" inputmode="tel"`, name input has
  `autocomplete="name"`.

## 4. LOW / VISUAL POLISH

- Trust stats ("10+ years", "6 specialists", "3 languages", "12 treatment areas") were
  claimed nowhere on the site despite being obvious premium-clinic trust signals.
  **FIXED**: added a `.stats-row` under the About-page H1 and under the homepage trust
  strip, sourced from `data/site.json → stats` (kept in sync with the actual data — see
  §7, `validate.py` now asserts these numbers agree with the underlying doctor/service
  counts rather than being hand-typed and driftable).
- Doctor cards (home team strip + `/doctors/`) showed role only, no experience — added a
  one-line "`N` years experience" under the role wherever a doctor card renders.

## 5. CONTENT (deliberate decisions, not oversights)

- **6 doctors shown, not 7.** The brief's example role list implies a 7th specialist
  (e.g. a dedicated pediatric dentist separate from general/family). Only 6 distinct
  real Gemini-photographed faces exist across the licensed photo set. Rather than invent
  a 7th doctor reusing another doctor's face (visually detectable, and dishonest),
  overlapping specialties were consolidated onto the 6 real people (e.g. Dr. Hakobyan
  covers both chief dentist and implant surgery; Dr. Ghazaryan covers both hygiene and
  periodontics). Every doctor shown has a genuinely distinct portrait.
- **No Instagram/Facebook links.** `contact.socials` is intentionally left `null`
  throughout. A plausible-looking guessed handle risks resolving to a real, unrelated
  account (reputational/misleading risk), and a `href="#"` stub is explicitly
  disallowed by this project's own rules. The footer's "Follow us" block already
  degrades cleanly to nothing when no social URL is set — nothing renders broken.
- **No `AggregateRating` JSON-LD, no Google Business Profile link**, even though the
  UI shows a friendly "★ 4.9 · Patient rating (11)" line. `demoMode: true` in
  `site.json` documents this intent; `build.py`'s structured data stays a minimal
  `Dentist` schema (name + phone only). Showing a rating to visitors is honest
  UI framing; asserting it as machine-readable third-party-verified data would not be.
  `validate.py` fails the build if `AggregateRating` ever appears on the homepage while
  `demoMode` is true, so this can't regress silently.

## 6. SEO

- Canonical, hreflang (including `x-default`), Open Graph, sitemap and robots.txt all
  derive from the single `SITE_URL` resolution described in §2 — no other hardcoded
  domain exists anywhere in `templates/` or `build.py`.
- `BreadcrumbList`, `Service`, `FAQPage` (where a service has FAQs), and `Person`
  structured data render per relevant page; homepage carries a minimal `Dentist` entry
  (see §5 for why it's deliberately minimal).
- `validate.py` now checks: every page has a non-empty `<title>` and meta description, a
  canonical link, no duplicate canonicals (excluding the two intentional root-level
  mechanical copies — see next point), `sitemap.xml` is well-formed and free of the
  placeholder domain, and `robots.txt` references the sitemap.
- `dist/index.html` (meta-refresh to the default language) and `dist/404.html` (a root
  copy of `dist/hy/404.html` for hosts like Vercel that look for one) intentionally
  share their canonical with the real page they mirror — this is correct, not a defect.

## 7. VALIDATION / TOOLING (new in this pass)

`validate.py` — run after every build (`python3 build.py && python3 validate.py`):

- **Structural checks** across all of `dist/`: broken internal links, missing image
  assets, leftover placeholder/Lorem-ipsum/unrendered-Jinja text, stray `href="#"`,
  missing `<title>`/meta description/canonical, duplicate canonicals, stray
  `elitdent.example` outside the one intentional demo email string.
- **hy/ru/en parity**: every page that exists in one language must exist in all three.
- **Cross-file content consistency**, read directly from `data/*.json` rather than
  rendered HTML, so it fails fast on the source of truth: `stats.specialists` must equal
  the actual doctor count, `stats.treatmentAreas` the actual service count,
  `stats.languages` the configured language count, `rating.count` the actual review
  count, every `doctorSlug`/`serviceSlug` cross-reference must resolve, and the
  `yearsExperience` stat can't overstate any individual doctor's experience or the
  clinic's own age.
- Exits non-zero on any error, so it can gate a deploy in CI later.

Current status: **0 errors, 0 warnings** against the rebuilt `dist/` (80 HTML files, 75
pages × 3 languages + shared root files).

## 8. MOBILE / CONVERSION

- Booking modal, mobile nav, and bottom bar were already built mobile-first in the
  original pass (`DESIGN_AUDIT.md` §§7–9); this pass added the missing accessibility
  layer (§3) on top rather than redesigning them.
- The bottom bar (call + WhatsApp + book) and floating WhatsApp button remain the
  primary mobile conversion paths; both now use build-time `wa_url()` links (§2), so
  they work even before `main.js` finishes loading on a slow connection.

## 9. KNOWN REMAINING LIMITATIONS (honest, not hidden)

- **Feature flags are declared but not fully wired.** `data/site.json →
  featureFlags.*` exists as the intended config surface for the reusable engine, but
  today only `homepageSections` (an explicit ordered list) actually controls what
  renders on the homepage; the list/detail pages (`/services/`, `/doctors/`,
  `/technology/`, `/reviews/`) and nav items still render unconditionally regardless of
  their matching flag. This has zero effect on the live ELIT DENT demo (every flag that
  matters is `true`; the three that are `false` — `beforeAfterEnabled`,
  `offersEnabled`, `blogEnabled` — have no implemented section to begin with, so there's
  nothing to leak). It matters for the *next* clinic built on this engine, and is
  flagged as the top item in `CUSTOMIZATION_GUIDE.md`'s "what's not reusable yet"
  section rather than silently left undocumented.
- **No live side-by-side comparison against `dentor.ge`** was possible — this sandbox's
  network egress policy blocks fetching arbitrary external sites (see
  `DESIGN_AUDIT.md` §0). The design system was built from general premium-dental
  conventions, not a pixel audit of that specific reference site. Recommended as a
  manual follow-up by whoever has unrestricted browser access.
