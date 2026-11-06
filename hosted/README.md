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

Current cloud cabinet supports company records, project-specific tasks with completion/block reasons, drafts, approvals, audit, Gmail OAuth and manual synchronization. Automatic scheduled mail polling, the demo generator/build runner, private previews of generated sites and automated research are **not connected to this hosted adapter**. It does not send on a schedule. Never represent a plan or old connector import as a completed live action. Imported historical records retain original dates; `sync_at` remains null until a complete live API sync succeeds.

## Verification

`npm test` from this directory: encryption tampering/wrong key, OAuth callback/PKCE, wrong sender, Gmail pagination/draft filtering, header injection, HTTP CSRF, secret redaction, disabled send. `tests/database.sql` runs service-role SQL assertions within a transaction ending ROLLBACK: disabled send, atomic claim/no repeat, unknown result and incoming reply suppression. No test letters or fake contacts remain.

Database privileges were checked on the live database. Direct Edge API probes returned 401 without auth, 401 with the wrong independent key, and 200 to the authenticated server. Security advisor reports only informational RLS-without-policy notices: intentional server-only tables, with all client grants revoked. A real owner browser login and Google consent are still required to verify the complete hosted path. No native Windows install is required.

Free Supabase projects can pause after inactivity. Vercel Hobby is for personal noncommercial use; live sales operations need an eligible plan. This deployment is for private setup/testing. No paid plan upgrade was authorized or enabled.
