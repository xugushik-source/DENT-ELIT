# Deployment status 2026-11-09

Supabase factory-executor deployed. JWT gateway plus private invocation key; service-role-only control/candidate tables with RLS. pg_cron invokes every ten minutes. Dry run verified HTTP200, owner Gmail profile verified, ten directory candidates stored, zero sends.

Still DRY_RUN. Candidate discovery is not qualification: no automatic activity/website validation and initial_draft generator are wired to RESEARCH candidates yet. Thus target50 and autonomous prospect-to-send flow are NOT complete. Existing verified FIRST_DRAFT dispatch path is implemented but not live-tested for sending. No spend, no main/production/DNS changes.

Credentials are absent from source. Existing encrypted OAuth is decrypted only server-side using private control key. No secret values in cron command or HTTP result. Lease prevents concurrent invocations. UNKNOWN claims never retried. Candidate upsert ignores duplicates. Read heartbeat,last_result,cursor on factory_executor_control and candidates on factory_executor_candidates using server-only access.
