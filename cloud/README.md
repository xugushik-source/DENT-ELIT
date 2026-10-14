# Private cloud adapter for the existing Dental Sales Factory

The existing office UI, strict clinic schema, pricing and Python ELIT DENT
renderer remain shared. This adapter replaces the local office SQLite runtime
with Workers + D1, stores inputs/output privately in R2, and dispatches a
short-lived GitHub Actions job. No persistent Windows service is required.
No clinic configurations, uploaded assets or build artifacts belong in git.

## Reproduce the tested cycle

Use Python 3.12+ and Node 22+ (tested Node 24). From the repository root:

```sh
python -m pip install -r requirements-factory.txt
cd cloud
npm ci
npm test
```

`prepare.mjs` copies the existing owner UI and compiles the existing JSON schema
without runtime eval. Generated UI/schema/proposals are ignored by git. The
integration test runs actual Miniflare Workers/D1/R2, validates signed owner JWTs,
builds the real 26-page synthetic ELIT DENT package and runs the actual Python
runner through a test-local transport. It reaches owner approval and an unsent
proposal. This is local platform emulation, not an account deployment or browser
visual QA. Owner decisions in tests are simulations.

## Account setup still required — no resources were created

1. Cloudflare account access: create one D1 database, apply `migrations/0001.sql`,
   and create one **private** R2 bucket. Fill the returned database ID in
   `wrangler.jsonc`. Check the account's free plan and R2 billing requirements;
   stop rather than accept a paid plan, purchase or automatic overage.
2. Configure Cloudflare Access **before exposing any route**. Use an owner-only
   email policy for the office and demos, and a Service Auth policy for
   `/api/runner/*`. No anonymous bypass. Set `ACCESS_ISSUER`, `ACCESS_AUD`,
   `OWNER_EMAIL`; worker verifies JWT signature/issuer/audience/expiry/email too.
   Use a protected workers.dev address only after this policy exists. This
   avoids changing ELIT DENT DNS. `workers_dev` and preview URLs default to false;
   deployment has no reachable route until the protected route is configured.
3. Create/authorize a separate **private build repository**. Install
   `runner-workflow.yml` as `.github/workflows/dental-demo.yml` there. It must
   exist on that repository's default branch. Do not install this workflow in
   the public template repository. Give the cloud dispatcher only repository
   metadata read and Actions write permission for that private repository.
4. Store secrets in the providers' secret stores, never chat, git or logs:
   Worker: `CSRF_SECRET`, `BUILD_SECRET` (independent random >=32 characters),
   `GITHUB_DISPATCH_TOKEN`.
   Private Actions environment `dental-demo-private`: `FACTORY_BUILD_SECRET`
   (matches worker BUILD_SECRET), `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`.
   Set Worker vars `RUNNER_REPOSITORY`, `RUNNER_WORKFLOW`, `RUNNER_REF`,
   `TEMPLATE_COMMIT`. Actions vars: `TRUSTED_TEMPLATE_SHA` (same reviewed full
   commit SHA), `FACTORY_CLOUD_ORIGIN` (protected HTTPS office origin).
5. Only after verifying account/free-plan/access settings: deploy this worker,
   run a synthetic card via the owner login, check private preview and owner
   approval. No patient requests or client messages are possible in this adapter.

The available GitHub connector can update this existing source branch but
cannot create the private repository, set CI secrets or provision Cloudflare.
There is no connected Cloudflare provisioning capability in this session.

## Limits and recovery

Five build requests per UTC day by default, ten-minute CI timeout, fifteen-minute
job expiry. Expired jobs can be resubmitted by the owner; old leases cannot
upload or finish. Revision changes invalidate approvals and drafts. D1 updates
use version checks and atomic batches. The worker checks private runner repository
visibility before dispatch, exact template commit and immutable manifest hashes.
Only manifest files are viewable. Office polling runs every 30 seconds while
visible. Storage reservation stops at 200 MB by default, including uploaded site
files; failed reservations remain conservatively counted. No automatic upgrade.

The generator records build seconds, zero standard-build AI usage and unknown
hosting/research totals. These are not a claim of guaranteed $0 total cost.
Provider billing/export integration is not connected.

## Current scope

Works: clinic cards, evidence/config revisions, validation, dispatch interface,
private asset download, deterministic build, tested artifact upload, owner
preview, pending-data acknowledgement, approval, proposal draft and audit history.
For this first cycle, the synthetic illustration is supplied automatically.
Actual clinic media ingestion/research connectors, CRM lead/email synchronization,
client-specific share access and sending remain disconnected. Real media must be
uploaded through an authorized ingestion integration with hash/size/rights
metadata; do not use public R2 URLs or commit assets as a workaround.

This is the cloud runtime for the same CRM/template; no independent clinic
application is created. Existing local office remains usable. Rollback: revert
this feature branch/runtime and keep the retained private D1/R2 data. Main,
production, DNS and existing ELIT DENT dist output are unchanged.
