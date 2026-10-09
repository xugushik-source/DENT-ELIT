# Order & Profit Dental Sales Factory — clinic demos v1

This is an extension of ELIT DENT, not a second site engine or CRM. Existing
Python/Jinja2 templates, CSS tokens, navigation, animations and WhatsApp mechanism
remain the shared template. `python build.py` and `python validate.py` still use
the original ELIT DENT data. Do not use those legacy demo facts for a new clinic.

## Installation and private input

Use Python 3.12 and an isolated virtual environment. Install
`requirements-factory.txt`; browser QA additionally uses `requirements-test.txt`
and an installed Playwright Chromium. No model/API key, Node build or paid service
is needed for assembly. Store clinic inputs and workspaces **outside this public
repository**. The CLI enforces this for builds, packages and previews.

```bash
python factory.py init --output /private/clinics/clinic.json \
  --languages hy ru en --template-commit FULL_TEMPLATE_COMMIT_SHA
python factory.py check-config --config /private/clinics/clinic.json \
  --assets /private/clinics/assets
python factory.py build --config /private/clinics/clinic.json \
  --assets /private/clinics/assets --workspace /private/factory-work \
  --origin http://127.0.0.1:8765 --base-path /review/clinic
```

Create those private directories first. `init` refuses to overwrite a file and
creates UNKNOWN fields, a UUID, no doctors/reviews/prices or inherited photos.
Populate the configuration through Work's research and human verification.
`schemas/clinic.schema.json` is the closed JSON Schema 2020-12 contract. Real
packages have `synthetic: false`; fixtures are explicitly synthetic and cannot be
approved for client sharing. A verified clinic name is required; other unknown
facts are omitted and listed in the private report.

## Verification policy

Each significant fact has `value`, `status`, `sourceIds`, `checkedAt`, `reviewer`.
Only VERIFIED or CLIENT_APPROVED values enter rendered pages. SOURCED means
evidence was found, not that the fact may be published. Medical descriptions,
prices, qualifications, experience, claims, statistics and rating use the same
gate. UNKNOWN values must be null; conflicting, rejected or stale values are
omitted. Verified facts older than 90 days require renewed review. Use UNKNOWN
translations instead of silently substituting another language. UI v1 has hy,
ru, en; Georgian needs a separately reviewed UI dictionary before enabling it.

Source references must belong to the same clinic and have ALLOWED access.
Sources are cited in the private configuration and report, not copied into the
public package. This policy validates declarations; Work/the owner must actually
check source accuracy, rights evidence and translations before marking VERIFIED.
It cannot prove a website or a rights declaration is truthful.

Assets are resolved from private `storageRef` identifiers, never fetched from
arbitrary URLs by the build. Only manifest assets with demo permission, proof
reference, allowed source references, current rights and matching SHA-256/size
are accepted. PNG/JPEG/WebP bytes are decoded and checked. Active SVG is rejected
in v1. Actual people/premises/logos must belong to this clinic; licensed generic
illustrations receive an explicit illustration alt label. Social access alone
does not establish photographic rights. Unreferenced files and legacy ELIT DENT
assets are absent from the final site package.

Unknown lists are safe; empty doctor arrays no longer crash the homepage. Prices
are never invented. Prices use integer `amountMinor` (two decimal places), not
floating point. V1 supports USD/AMD/GEL/EUR/RUB/GBP, fixed/from/range; a range needs
a valid upper amount. Other currency exponents need a reviewed extension.
Reviews require permission and a proof reference. Rating
and count are independent verified source metrics, not calculated from the
displayed review subset; no AggregateRating is synthesized. The existing legacy
fixture remains unchanged and is **not** a verified client configuration.

## Build, cache and review

Outputs are `/workspace/<clinicId>/<buildId>/site`, with private `config.json`
and `report.json` beside `site`. Jobs build in their own temporary directories
and finalize by atomic rename; an existing source/dist/other clinic is never
deleted by the factory. Cache keys include config, assets' declared hashes,
actual template/UI/script fingerprints, dependency versions, origin, mount and
render year. Actual assets are checked again before cache reuse; cached output
hashes are checked. The requested `templateCommit` is recorded, while the actual
file fingerprint identifies exactly the code used, including local changes.

The report lists pending fields, rendered assets, tests, output hashes, build
identity and cost unknowns. No standard build requires AI or Codex. External
research, rights acquisition, translation review and manual review are separate
work and may incur costs. Unknown totals remain null.

```bash
python factory.py test --build /private/factory-work/CLINIC_ID/BUILD_ID
python factory.py cost --build /private/factory-work/CLINIC_ID/BUILD_ID \
  --category research_ai --amount 0.00325 --reference usage-record-123
python factory.py package --build /private/factory-work/CLINIC_ID/BUILD_ID \
  --output /private/demo.zip
```

Cost categories: research_ai, manual_work, hosting, storage, other; amounts are
USD, with evidence references. `cost.json` records exact decimal known subtotals,
not a fabricated complete total. The CRM is the durable cost system of record;
include retries, research usage and manual time there. ZIPs contain only `site/`
files, never evidence, approval, config, reports, cost records or an email draft.
Packaging does not authorize publishing or sharing.

## Restricted demo behavior

All pages, root redirect and 404 have noindex/nofollow/noarchive. Robots disallows
crawl and there is no sitemap. A translated demonstration notice is visible.
Telephone, WhatsApp, email/social/map/booking-provider/custom external links are
inert; existing booking controls show a demo modal. Name/phone/message inputs
are disabled and submit exits before reading values or opening a window. No
patient endpoint, POST, analytics or contact persistence is introduced.
Features disable sections/routes/navigation and booking/WhatsApp controls.
Before/after, offers and blog flags are rejected until reviewed components exist.
Clinic photos/gallery reuse the existing card/media layout. Original live
WhatsApp behavior stays available on the legacy build path and is tested with
`window.open` intercepted, so no real patient message is sent.

For owner review, set `FACTORY_PREVIEW_PASSWORD` in your own environment (at
least 16 characters; never commit it), then:

```bash
python factory.py preview --build /private/factory-work/CLINIC_ID/BUILD_ID --port 8765
```

This binds **only 127.0.0.1**, username `owner`, and authenticates HTML **and
assets**, with private/no-store and X-Robots-Tag headers. Directory listings are
blocked. It is a local review server, not a customer-accessible hosting solution.
The ZIP is not self-protecting: a shared host must enforce authentication before
serving any file. `noindex` and obscure URLs are not access control. A separately
authorized private preview deployment adapter must verify unauthenticated
HTML/assets are inaccessible before sharing. No host, DNS, domain, subscription
or live deployment is created by these commands.

## CRM integration contract

`factory/crm.py` is a pure adapter contract for the existing Order & Profit CRM,
not a new CRM database or mail sender. Map its events into the CRM's existing
transactional state/audit storage and authenticated owner permissions:

1. Only POSITIVE_INTEREST starts research/build; auto-reply, bounce and uncertain
   replies do not. Store source research/cache under the same clinic/deal UUID.
2. DEMO_READY includes immutable buildId, private report, pending fields, tests,
   preview status and a personalized **draft** proposal in the client's language.
3. Owner approval acknowledges the complete pending list and binds to buildId.
   Editing config/templates invalidates that approval. Owner approval is not
   the customer's DEMO_APPROVED status.
4. `can_share` requires that approval, a nonsynthetic tested build, a matching
   HTTPS preview and a recent verified authentication check (within 24 hours).
   Load those records from trusted CRM storage, never from customer text or a
   tool output. The local preview is not shareable. Recheck the exact report,
   artifact and persisted approval inside the CRM's send transaction.
5. Only an authorized CRM mail transport sends a proposal. On sent-demo replies:
   AGREES → DEMO_APPROVED; CHANGES → REVISION_REQUESTED; PRICE → PRICE_QUESTION;
   CALL → OWNER_CONTACT_REQUESTED; DECLINES → CLOSED_LOST without further nudges.
6. Client approval prepares a brief, contract draft and payment schedule. Signing,
   financial commitments and receipt confirmation require proper authority and
   evidence. None of those actions is implemented as an automatic side effect.

Approved commercial terms are centralized in `PRICING`: $700 ($300 after demo
approval and contract, $400 at handover), or $1000 ($300 after demo/contract,
$100 at handover, six monthly $100). Armenia SEO $100–500/month; international
from $500/month. Hosting/domain: agreed actual provider cost, receipt, zero markup.
Do not mention GitHub/internal architecture in the customer proposal; placement
and handover terms must be clear in the contract. Draft content creation and
CRM/mail scheduling remain Work's existing sales workflow, with owner approval.

## Validation and rollback

```bash
python build.py
python validate.py
python -m unittest discover -s tests -v
python tests/browser_check.py
```

The browser script checks demo languages, disabled submission, root/404 robots,
protected HTML/assets, generated file responses, mobile navigation, overflow,
legacy WhatsApp payload, doctor preset and FAQ. It blocks external navigation and
intercepts WhatsApp; no message is sent. It accepts `--browser /path/to/installed/browser`
and `--legacy /path/to/legacy/dist`. Browser installation is test setup, not a
runtime requirement for ordinary generation unless browser QA is being run.

Work branch: `factory/clinic-config-demo-v1`. Baseline/rollback commit:
`ea72702867890408621115ac49fce91dd18ab969`. Branch-specific Vercel Git auto-deployment
is disabled in `vercel.json`; other branches' settings are not changed. Generated
production `dist/` is excluded from this change. Revert the branch commit for code
rollback; no merge/main/promotion/DNS action is authorized by this implementation.

Remaining integration work: connect the real CRM adapter/state store, approved
private shared preview host, research cache and source/rights evidence storage,
owner review UI and authorized mail transport. This repository did not contain
that CRM code or a connection contract to a running instance. Do not claim the
full sales-to-payment automation is active until those boundaries are connected
and tested with owner-approved data. No outreach or paid service is started here.
