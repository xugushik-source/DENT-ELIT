# ELIT DENT — Design Audit

## 0. Known limitation (read first)

The brief for this project asks for a live visual audit of `dentor.ge` (desktop/tablet/mobile,
scroll behaviour, hover states, exact spacing) before writing any code. In this build
environment, outbound network access to `dentor.ge` is blocked by the execution
sandbox's egress policy — the fetch was attempted and rejected at the network layer, not
skipped. So this audit is **not** a pixel-level teardown of the live site; it is a design
system built from professional premium-dental / boutique-clinic conventions (the same
family of decisions Dentor-style sites make: warm neutral palettes, restrained gold/brass
accents, large confident type, generous whitespace, editorial photography, subtle
scroll-reveal motion).

**Action item before ship:** open `dentor.ge` yourself (desktop + mobile) alongside the
built ELIT DENT pages and do the side-by-side pass described in the brief's sections 68–69
(header height, hero proportions, container width, section rhythm, button sizing, footer).
Treat everything below as a strong, defensible starting point — not a verified match.

## 1. Visual principles

- **Warm, clinical-but-human.** No generic medical blue. Warmth comes from ivory/cream
  surfaces and a desaturated warm-gold accent — never a fully saturated "luxury gold" wash.
- **Editorial, not templated.** Large type, asymmetric hero (copy left / photography right),
  restrained card chrome (thin hairline borders instead of heavy shadows).
- **Calm motion.** Fade + short translate-Y reveals on scroll, staggered by ~80ms per
  sibling. No bounce, no parallax, no autoplay carousels.
- **One accent, used sparingly.** Gold marks CTAs, active nav state, numbered process
  steps, and small dividers only — never large fills or backgrounds.

## 2. Palette

| Token | Value | Use |
|---|---|---|
| `--color-bg` | `#FAF7F1` (warm ivory) | page background |
| `--color-surface` | `#FFFFFF` | cards, header |
| `--color-surface-alt` | `#F1EBE0` (travertine/stone) | alternating sections |
| `--color-text` | `#221F1A` (near-black graphite, warm) | headings/body |
| `--color-text-muted` | `#6B6459` | secondary copy |
| `--color-border` | `#E4DBCB` | hairlines |
| `--color-primary` | `#221F1A` | primary buttons, dark surfaces |
| `--color-accent` / `--color-gold` | `#B8925A` (champagne gold) | CTA fills, active states, numerals |
| `--color-accent-soft` | `#EFE3CF` | gold-tinted chips/badges |
| `--color-success` (WhatsApp CTA) | `#3F7A5C` (muted forest, not brand-green) | WhatsApp button only |

Dark mode is out of scope for v1 (marketing site, not an app) — not implemented.

## 3. Typography

- **Headings:** a high-contrast serif/humanist-serif display face for H1/H2 (editorial,
  premium-clinic feel) — implemented with a Google Fonts pairing that has full Armenian,
  Cyrillic and Latin glyph coverage (see §4).
- **Body/UI:** a clean humanist sans for body copy, nav, buttons, forms.
- Scale (desktop): Display 56/1.05, H1 44/1.1, H2 34/1.15, H3 24/1.3, Body-L 19/1.6,
  Body 16/1.7, Caption 13/1.5 uppercase tracked, Eyebrow 13/1.4 uppercase tracked +0.08em,
  Button 15/1 medium tracked +0.02em.
- Mobile scale steps down ~20–30% on display/H1/H2, body stays ~16–17px minimum.

## 4. Multilingual font coverage (verified requirement, not guessed)

Armenian glyph support is the single most common failure point in "premium" web fonts —
most display serifs silently fall back to a generic system font for Armenian, breaking the
premium feel exactly where the brief cares most (Armenian is the default language).

Chosen pairing:
- **Headings:** `Noto Serif` (Google Fonts) — Noto's explicit design goal is full Unicode
  coverage; it ships Armenian, Cyrillic and Latin in the same family, same metrics, so
  headlines don't visually "jump" between languages.
- **Body/UI:** `Noto Sans` — same coverage guarantee, pairs cleanly with Noto Serif.

This is a deliberate trade against a more "boutique" display face: a beautiful Latin-only
serif that silently drops to Times New Roman for Armenian would fail the brief's own
Armenian-first requirement. If a licensed premium face with confirmed Armenian hinting is
sourced later, swap only the `--font-heading` token.

## 5. Spacing & layout

- 8px base unit. Section vertical rhythm: `--section-spacing: clamp(64px, 8vw, 128px)`.
- Container: `--container-width: 1200px`, side gutters `clamp(20px, 5vw, 64px)`.
- Grid: 12-col conceptual, implemented with CSS Grid `auto-fit`/`minmax` for card rows
  (services 3-up desktop / 2-up tablet / 1-up mobile; doctors 3-up / 1-up).

## 6. Radii, borders, shadows

- `--radius-sm: 6px` (chips, inputs), `--radius-md: 14px` (cards, buttons),
  `--radius-lg: 28px` (hero image frame, large photo blocks).
- Borders: 1px hairline `--color-border`, not heavy drop shadows. One soft shadow token
  (`--shadow-card: 0 12px 32px -16px rgba(34,31,26,.18)`) used only on hover/elevation,
  never as default card chrome — keeps the page feeling flat/premium rather than "SaaS card
  soup".

## 7. Buttons

- Primary: solid graphite (`--color-primary`) fill, cream text, `radius-md`, generous
  padding (16px/28px), on hover: background shifts to gold, text stays legible (checked
  contrast).
- Secondary (WhatsApp): outline or muted-forest fill with WhatsApp glyph, same radius.
- Ghost/text links: underline-on-hover with 4px offset, arrow (→) that translates 4px on
  hover — used for "Learn more" card links.

## 8. Cards

- Service card: image (4:3), title, 2-line clamp description, "Learn more →" row. On
  hover: image scale(1.04) over 400ms ease, arrow translates +4px, card border shifts to
  accent-soft. No shadow pop — motion carries the interaction, not elevation.
- Doctor card: portrait (3:4), name, role, one-line specialization, on hover a thin gold
  underline draws in under the name.

## 9. Image treatment

- Hero: doctor-focused photography always placed right, negative space left, 16:10-ish crop
  on desktop, closer to 4:5 on mobile (re-crop via `object-position`, not the same crop
  squeezed).
- All photography desaturated ~5–8% and warmed slightly (subtle sepia-lean filter token)
  so stock/generated images read as "one photoshoot," matching brief §8's intent — applied
  via a shared `.photo` CSS class, not baked into the files, so it can be turned off per
  image if a real photoshoot arrives later.

## 10. Motion

- Reveal: `opacity 0 → 1`, `translateY(16px) → 0`, 600ms `cubic-bezier(.2,.7,.2,1)`,
  staggered via `transition-delay` in 80ms steps per group, triggered by
  `IntersectionObserver`.
- Header: transparent-over-hero → solid `--color-surface` + 1px border + blur once
  scrolled past hero height.
- All motion wrapped in `@media (prefers-reduced-motion: reduce)` → instant, no transform.

## 11. Header behaviour

- Desktop (≥1360px — see note below): logo left, nav center-right, language switch +
  primary CTA right. Sticky, background/blur transition on scroll (see Motion).
- Below 1360px: compact header (logo, language switch, hamburger) with a full-height
  animated nav overlay, not a Bootstrap dropdown.
- **No phone number in the inline desktop header.** This was a deliberate reversal during
  build: with 7 nav items in Armenian (the longest of the 3 languages) plus language
  switch and a CTA button, there is not enough horizontal room in a premium, generously
  spaced header to also fit a phone number without either cramming everything into
  illegibly tight type or overflowing the container (verified with Playwright — an earlier
  pass shipped exactly that overflow bug before this was caught in QA). Rather than widen
  the header container out of alignment with the page's content column, the phone number
  was dropped from this one slot. It remains one click away everywhere it matters: the
  WhatsApp float button, the mobile bottom bar, the final CTA, the footer, and the contact
  page all carry it. `--container-width` was raised from 1200px to 1360px site-wide (not
  just in the header) to keep the header and body content edges aligned at every viewport.

## 12. Mobile-specific

- Fixed bottom conversion bar: Call / WhatsApp / Book, respecting
  `env(safe-area-inset-bottom)`, `z-index` above content, hidden while the booking modal is
  open.

## 13. Service detail page architecture

Breadcrumb → Eyebrow + H1 → Intro + CTA → Hero image → About treatment → Who it's for →
Benefits → Numbered process (01–05) → Technology used → Doctor → Pricing (config-driven,
"price after consultation" copy, no invented numbers) → FAQ (accordion) → Related services
→ Final CTA.

## 14. CTA logic

Every page carries exactly two conversion paths at all times: **Call** (`tel:`) and
**WhatsApp** (deep link with a page-aware prefilled message) — plus a **Book Consultation**
modal as the primary path in hero/final-CTA positions. No competing tertiary CTAs.
