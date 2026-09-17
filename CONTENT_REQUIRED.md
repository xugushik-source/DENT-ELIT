# ELIT DENT — Content Required

Onboarding brief: what still needs to come from the client before this site is
launch-ready, and what a *next* clinic on the ORDER PROFIT dental engine needs to
provide to get their own version built. Everything below that's still open is also
flagged inline in the code (`data/site.json`, `data/reviews.json`, etc.) so it isn't
just tracked here.

## Status legend
✅ done · ⏳ using placeholder/demo data · ❌ not started (real data required before launch)

---

## BRAND

| Item | Status | Notes |
|---|---|---|
| Clinic name | ✅ | ELIT DENT |
| Logo | ✅ | Real client-supplied gold tooth-ribbon mark + serif wordmark. Two source renders (dark hero shot, marble wall-signage shot) live in `static/brand/source/`. Production crops: `static/brand/logo-mark-light.png` (header/nav), `static/brand/logo-full-light.png` (About page, full lockup with tagline), `static/brand/logo-full-dark.png` (available for dark-surface use). No background-removal cutout was attempted on the small mark — a naive luminance-alpha matte produced a visible grey halo, so each crop keeps its native, on-brand travertine or black backdrop instead of shipping a botched cutout. **If a clean vector/transparent master exists on the client's side, that supersedes these photographic crops.** |
| Tagline | ✅ | "Premium Dental Care" / per-language in `data/site.json` |
| Brand colors | ✅ | Derived from the logo's champagne-gold + a warm ivory/travertine system — see `DESIGN_AUDIT.md` §2 |

## CONTACT

| Item | Status | Notes |
|---|---|---|
| Phone | ✅ | +995 579 145 634 (ORDER PROFIT demo number, per brief) |
| WhatsApp | ✅ | Same number, wired to contextual deep links site-wide |
| Email | ❌ | `data/site.json → contact.email` is `null` |
| Address | ❌ | `contact.address` is `null` — contact page shows "To be confirmed" |
| Working hours | ❌ | `contact.workingHours` is `null` — same placeholder treatment |
| Google Maps URL | ❌ | `contact.googleMapsUrl` is `null` — contact page shows a labeled map placeholder, not a fake embed |
| Google Business URL | ❌ | `contact.googleBusinessUrl` is `null` |

## DOCTORS

⏳ **Six demo doctor characters**, built from the Gemini photo categories named in the
brief (implantologist, orthodontist, aesthetic dentist, general/family dentist,
endodontist, hygienist). Names, roles, bios, and quotes are placeholder-but-plausible —
**no real degrees, universities, or certifications are claimed anywhere**, per the
brief's explicit instruction. Before launch, replace in `data/doctors.json`:
- Real names, real photos
- Real specialization/role text
- Real experience, education, certifications (currently `experienceYears: null`,
  no education field is even rendered, intentionally, since nothing real exists yet)
- Real languages spoken

## SERVICES

✅ All 12 services from the brief are written with real (non-Lorem-Ipsum) copy in all
three languages, each with its own detail page (intro, about, who-it's-for, benefits,
5-step process, technology, doctor, pricing, FAQ, related services). Pricing is
architecturally ready (`price.note` per language) but intentionally shows only
"Price after consultation" — **no invented numbers anywhere**. When real prices exist,
add `amount`/`currency` fields to `data/services.json` and update the pricing template
section in `templates/pages/service_detail.html`.

## TECHNOLOGY

✅ Four technology items (CBCT, intraoral scanning, dental microscope, digital
treatment planning) with real explanatory copy. If the clinic's actual equipment
differs (different CBCT brand, no in-house microscope, etc.), edit `data/technology.json`
— models/brand names are not currently named, only the technology category.

## MEDIA

✅ **Real Gemini photography is now integrated**, pulled from the client's Google Drive
folder "Стоматология шаблон элит день" (15 photos). Each was opened and identified by
content, not filename (filenames are generic `Gemini_Generated_Image_*.jpg`). Master
originals are kept at `static/images/real/photo_01.jpg`–`photo_15.jpg`; every other
photography slot in the site is a copy of one of these 15, mapped by subject:

| # | Content | Used for |
|---|---|---|
| 01 | Assistant + patient reviewing 3D scan on wall monitor | Digital treatment planning (technology) |
| 02 | Dentist using operating microscope, assistant beside | Root canal / microscope technology, Dr. Tigran Avetisyan |
| 03 | Hygienist cleaning patient's teeth | Professional cleaning, Dr. Mane Ghazaryan |
| 04 | Dentist showing tablet to child + mother | Family dentistry, Dr. Narek Sargsyan |
| 05 | Dentist showing hand mirror to smiling patient | Aesthetic dentistry / teeth whitening, Dr. Lusine Margaryan |
| 06 / 07 | Patient positioned in CBCT scanner (duplicate upload) | CBCT 3D diagnostics |
| 08 | Intraoral scanning in progress, assistant in background | Intraoral scanning, crowns & prosthetics |
| 09 | Five-person clinic team, reception hallway | About page team section |
| 10 | Dentist pointing to ortho scan on wall screen with teen patient | Orthodontics, Dr. Ani Petrosyan |
| 11 | Solo male dentist portrait, panoramic X-ray behind | Dental implants / oral surgery, Dr. Vardan Hakobyan |
| 12 | Dentist explaining panoramic X-ray to a couple | Homepage hero doctor spotlight, implant consultation |
| 13 | Two staff treating a smiling reclined patient | General dentistry, periodontology |
| 14 | Solo female dentist portrait, clean negative space on the left | **Homepage hero** (matches the brief's doctor-right/negative-space-left composition exactly) |
| 15 | Receptionist checking in a patient, another waiting | Homepage final CTA, About page clinic environment |

**Known limitation, be upfront about it:** 15 real photos cover a much larger sitemap
of image slots (38+), so several photos are deliberately reused across thematically
related slots (e.g. the CBCT shot appears on both the CBCT technology card and the
oral-surgery/digital-diagnostics service pages). This is normal practice for a real
site launch too, but if the client wants zero repeats, more photography is needed —
this is a real constraint of the 15-photo set, not a placeholder shortcut.

**Not yet sourced:** a dedicated gallery/before-after set (feature-flagged off anyway),
and any photo not already covering one of the 15 subjects above (e.g. a distinct oral
surgery action shot, distinct periodontology shot — currently sharing photos 11/06/03/13
by theme instead).

## REVIEWS

⏳ `data/reviews.json` contains 3 demo reviews, each explicitly flagged `"isDemo": true`
and rendered with a visible "Demo data" badge — no fake Google star rating or review
count is shown anywhere (`aggregateRatingEnabled: false`). Replace with verified,
real patient reviews before launch; flip `isDemo` off per entry as each is verified.

## SEO

| Item | Status | Notes |
|---|---|---|
| Country / city | ❌ | `data/site.json → seo.country/city` are `null` |
| Service areas | ❌ | `seo.serviceAreas` is an empty list |
| Real domain | ❌ | Sitemap/canonical/OG tags currently use the placeholder `https://elitdent.example` — set `seo.siteUrlPlaceholder` to the real domain before launch, it propagates everywhere automatically |
| Google Business Profile | ❌ | Not linked — needed for local SEO/structured data once the clinic has a verified listing |

## SOCIAL

❌ All of `data/site.json → contact.socials` (instagram/facebook/tiktok/youtube) are
`null`. The footer's "Follow us" column only renders once at least one is filled in —
it won't show an empty/broken section in the meantime.

---

## What "done" looked like for this pass

Architecture, copy (3 languages, natively written not machine-translated), design
system, animations, SEO plumbing (sitemap/robots/hreflang/structured data), booking
flow, and QA (see below) are complete and functioning. What's missing is exclusively
**client-supplied real-world content**: photography, doctor credentials, contact
specifics, and reviews. None of it was fabricated to fill the gap — every open item
above is either `null`/absent in the data or visibly marked as demo/placeholder in the
rendered page, per the brief's explicit instruction not to invent facts.

## Known QA gap

The brief calls for a live visual side-by-side against `dentor.ge` before sign-off.
This build environment's network egress blocks `dentor.ge`, so that comparison pass
(brief §68–69) has **not** been done and should be run manually once the site is in an
environment with normal internet access.
