# Order & Profit — hosted owner cabinet

This is the cloud sales adapter for the existing Dental Sales Factory, not a claim that the entire demo factory is live. The existing generator and renderer remain in this repository. Code is public; CRM records, mail content, OAuth files, runtime keys and database exports must never be committed.

## Runtime

A separate Vercel project `order-profit-owner` is protected by Vercel Authentication **for all deployments and aliases**. The team was checked to contain one confirmed owner. `staging` is the Vercel REST API name for a preview target. All mutations require the exact deployment origin and a random HttpOnly Secure SameSite CSRF cookie. Do not remove protection or create sharing/bypass links to make QA easier.

Supabase project `ehodzmqjubofvqdnnkdq` contains six RLS-protected tables with no browser/anon/authenticated grants. Only the Edge Function service role may call `factory_command`; the function is SECURITY INVOKER. `factory-bridge` requires gateway JWT verification **and** an independent 256-bit server credential, stored as SHA-256 in the database. Browser assets contain neither credential. The server has a strict operation allowlist.

Vercel encrypted environment variables (preview only): `FACTORY_BRIDGE_URL`, `FACTORY_BRIDGE_KEY`, `FACTORY_SUPABASE_JWT` (legacy anon JWT needed by the gateway), `FACTORY_CIPHER_KEY` (32 random bytes in hex). Use the exact deployment hostname as the Google callback origin. Do not use the production alias for a preview. Lost encryption keys mean Gmail must be reauthorized; retain them only in provider secret stores.

## Gmail connection from a phone

The cabinet shows the exact callback URL under “Подключить Gmail”. In the existing Google Cloud project, create a **Web application** OAuth client with that exact authorized redirect URI. The previous Desktop client cannot be reused for a hosted callback. Download its JSON privately, then select it in the protected cabinet. The file is sent to the protected API, never to ChatGPT or git. Google authorization uses PKCE, state, a separate browser-bound HttpOnly cookie, a ten-minute lifetime and one-time callback consumption. Only `orderprofit.he@gmail.com` is accepted. Refresh credentials are AES-256-GCM encrypted before entering the database. Neither access nor refresh tokens are included in API snapshots.

Testing mode can expire Gmail offline authorization after seven days. Review Google's requirements before treating this as permanent unattended mail access. No OAuth authorization or actual mail sending has been completed by deploying this code.

## Safety and current scope

`factory_runtime.sending_enabled` defaults to false. The UI cannot turn it on. Exact recipient and content must be approved before claim; the database atomically claims each letter and enforces five attempts per rolling 24h. Incoming messages cancel pending approvals and block contacts. Unknown outcomes cannot retry; a stranded SENDING row also remains unclaimable and requires manual reconciliation in Gmail. “SENT” means Gmail returned an ID, not confirmed delivery/read.

Current cloud cabinet supports company records, project-specific tasks, drafts, approvals, audit and Gmail OAuth. While the page is visible, known-company mail is polled every two minutes; this is not unattended operation. The Sites tab now invokes the shared Python renderer, stores bounded generated files in server-only database tables and serves them behind the same Vercel protection. Automated research, unattended jobs, client-specific external sharing and automatic proposal generation are not connected. It does not send on a schedule. Never represent a plan or old connector import as a completed live action. Imported historical records retain original dates; `sync_at` remains null until a complete live API sync succeeds.

## Verification

`npm test` from this directory: encryption tampering/wrong key, OAuth callback/PKCE, wrong sender, Gmail pagination/draft filtering, header injection, HTTP CSRF, secret redaction, disabled send. `tests/database.sql` runs service-role SQL assertions within a transaction ending ROLLBACK: disabled send, atomic claim/no repeat, unknown result and incoming reply suppression. No test letters or fake contacts remain.

Database privileges were checked on the live database. Direct Edge API probes returned 401 without auth, 401 with the wrong independent key, and 200 to the authenticated server. Security advisor reports only informational RLS-without-policy notices: intentional server-only tables, with all client grants revoked. A real owner browser login and Google consent are still required to verify the complete hosted path. No native Windows install is required.

Free Supabase projects can pause after inactivity. Vercel Hobby is for personal noncommercial use; live sales operations need an eligible plan. This deployment is for private setup/testing. No paid plan upgrade was authorized or enabled.

## Hosted generator

Run `python hosted/prepare_engine.py` from the repository root before assembling a deployment. It packages only reviewed renderer code, schema, templates, language UI and CSS/JS into a 63 KB `engine.zip`; no clinic configs, stock clinic photos or runtime data enter that bundle. The archive and staging directory are ignored by git. Deploy the archive at the function root alongside `requirements.txt` and `api/build.py`. `/api/build` runs on the Python runtime; the Node API remains the CRM/mail runtime.

The private tables `factory_sites` and `factory_site_files` have RLS and no client grants. The generator API requires Vercel authentication plus origin/CSRF checks. A transaction claims each build once. Five builds per rolling day, 150 files and a 3 MB encoded package limit bound the pilot. No customer share URLs are minted. Preview access and explicit acknowledgement of unknown fields precede approval. A stopped CRM contact cannot initialize a real build. Synthetic cards are separate from CRM leads and cannot become sent proposals.

The reviewed renderer supports ru/en/hy only. It does not invent missing doctors, services, reviews, contacts or translations. Owner-entered name/source come from the corresponding CRM lead. The initial cloud form supplies country and city; photo/media ingestion and richer verified content editing are not yet exposed. Building a complete real client site still requires those verified inputs.

`PYTHONPATH=<dependency-directory> python hosted/tests/generator.py -q` builds all three supported languages with the actual renderer, rejects stopped/absent contacts and rejects unsupported Georgian. Existing factory regression suite: 44 passed. The separate Node suite has 8 tests. Actual owner browser invocation of the new Python Vercel function remains a required hosted-path check.

## Approved template and completion gates (2026-11-06)

ELIT DENT at https://dent-elit.vercel.app/ru/ is the owner-approved visual reference. The cabinet links to it directly; empty synthetic builds are hidden from the owner list. Existing Jinja templates, CSS and JS are retained. A real build now requires owner-confirmed description, actual clinic photo with permission, and at least one sourced service. Images are decoded, resized, metadata stripped and stored privately; no arbitrary image URLs are fetched. Unknown doctors, reviews, prices and contact claims are not copied from another clinic.

After opening and approving a real build, the owner can create one idempotent proposal draft. The draft names ELIT DENT as a design sample, does not claim that its doctors or facts belong to the prospect, and does not include a private owner-only URL. It does not send mail. A client-accessible personal preview remains a separate, unimplemented approval gate. The cabinet shows each stage and current blockers. NIO DENT remains stopped.

Validation: real-card rendering with uploaded photo and service, missing-data rejection, three supported UI languages, DOM refresh/timeout checks, server CSRF checks; SQL transaction rollback verifies approval gate and draft idempotency. Live owner-authenticated Vercel invocation still needs confirmation; deployment READY alone is not an end-to-end test.


## Consent-first campaign correction — 7 November 2026

See PIPELINE_RUNBOOK.md and campaign.json. First proposal precedes a personal build. Persist a human consent quote/message id; blocked/opted-out leads do not progress. Georgian UI was added to the existing engine; a ka/en/ru build uses separate localized descriptions and service text, with no language fallback. Client preview release is still disconnected and no delivery is claimed. Two ChatGPT automations were configured (daily discovery/preparation and Gmail message-event handling); creation is not evidence of a completed execution. Campaign sending remains paused.

The first Georgian message now follows the owner's sent September examples: a loss-framed subject, a sourced issue, concrete benefits, ELIT DENT design sample, current project USD pricing and an invitation to consent to a free preliminary demo. The subject is phrased as a question, without inventing lost patient counts.


## Isolated client preview — 7 November 2026

Client preview is now deployed separately with an expiring per-build capability URL; the public service has no CRM/Gmail/write credentials. Database RPC returns only one generated file after hash, expiry, revocation, consent and approved-build checks. The owner cabinet issues and probes links before making a demo draft available; revoked/expired links block sending. Anonymous browser requests returned 200 for HTML/CSS/JS without cookies or owner identity, and a revoked test URL became unavailable. The synthetic test link is revoked. The client viewer's source is kept in its dedicated Sites source repository.

Mail sending remains paused after automatic approval review rejected the self-addressed test email. No message was sent; do not retry another transport or enable unattended sending to bypass that rejection.
