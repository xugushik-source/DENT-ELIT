# Factory v1 verification — 2026-10-09

Baseline: `ea72702867890408621115ac49fce91dd18ab969`.
Scope: deterministic clinic-demo preparation and builds in the existing ELIT DENT
repository, with a pure CRM contract. No CRM instance, client delivery, hosting
deployment, main merge, DNS or paid-service action is part of this verification.

| Boundary | Evidence |
|---|---|
| Original engine | Baseline `python build.py`: 75 content pages / 3 languages; validator: 80 HTML files, 0 errors, 0 warnings |
| Refactored legacy engine | Same page count and existing validator pass; live booking tested with `window.open` intercepted |
| Automated policy/build/CRM suite | `python -m unittest discover -s tests -v`: **24 tests passed** |
| Browser end-to-end | `tests/browser_check.py`: passed; hy/ru/en; desktop 1440×900 and mobile 390×844; no JavaScript errors |
| Preview protection | Unauthenticated root, language page, JavaScript and image: **401**; authenticated generated files: **200** |
| Demo safety | Visible notice, no active external/tel/mailto actions; name/phone disabled; forced submit opened no window |
| No indexing | Root, language pages and 404: noindex; robots disallows all; no sitemap; preview X-Robots-Tag covers files |
| Isolation | Fixture A → B: no A/ELIT DENT identifiers, old phone/address/email/rating/doctor or unused legacy images in B |
| Config policy | Unknown facts omitted; invalid verification, rights, hashes, SVG, stale/future facts, cross-clinic sources/assets and missing translations rejected |
| Prices and profiles | Confirmed integer-minor-unit range converted exactly; doctor, equipment and permitted review rendered; unconfirmed medical copy absent |
| Runtime behavior | Empty doctor/service/review lists build; disabled routes/actions; mount paths; parallel jobs; cache reuse and tamper detection |
| Packaging and cost | ZIP exactly equals site manifest, no private config/report/cost; exact decimal expense subtotal, unknown total stays null |
| Approval contract | Auto-replies do not start demos; owner approval binds buildId/pending fields; synthetic or unprotected previews cannot be shared; client approval is separate |

Browser toolkit tested: Playwright 1.63.0; installed Chromium Headless Shell 134
was selected explicitly in this environment. Browser downloads are optional
test setup and do not affect standard assembly. External navigation was blocked;
WhatsApp window opening was intercepted, so these tests send no real messages.
Screenshots were inspected after scrolling through the complete pages to trigger
the existing reveal animations and lazy loading. Test screenshots and private
synthetic builds are not committed or deployed.

The original mobile trust grid overflowed with long translated headings. The
baseline reproduced the defect. A narrow CSS fix retains the grid/design and
allows text wrapping; the rebuilt legacy version passes mobile overflow checks.

The existing checked-in `dist/` is deliberately left unchanged. Browser QA rebuilds
legacy sources in a temporary external directory to avoid testing a stale
production artifact or altering it. Source data, clinic photos/logos and original
language content remain unchanged. Factory configurations start from UNKNOWN,
not copied legacy facts. The prepared renderer uses StrictUndefined and escaping;
root manual interpolation and JSON-LD script boundaries are escaped too.

The factory CLI performs no model/network/deployment/mail calls. Reports record
zero AI usage for assembly; research, manual work and provider charges remain
unknown until actual cost evidence is added. This is not a claim that the entire
research-to-sale process is free or that the CRM integration is already live.

Remaining boundaries: real CRM persistence and owner identity, rights/source
evidence store, shared protected preview hosting and authorized email transport.
These require the existing Dental Sales Factory source/API and a separately
approved deployment target. The shipped contract describes the integration;
there is no second database or independent CRM.

Before review, check `FACTORY_GUIDE.md`. Do not merge or deploy this branch without
the owner's separate authorization. Branch Git auto-deployment is disabled in
`vercel.json`; production settings and DNS are unchanged.
