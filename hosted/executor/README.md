# Durable executor core — NOT LIVE

This queue is the first implemented component, not a complete sales worker.
It supports durable checkpoints, exclusive leases, idempotent enqueue keys,
bounded recovery for non-send work and UNKNOWN after an uncertain send.
Use a private persistent volume. Never commit queue databases, clinic records,
credentials or message bodies. Tests: `python -m unittest discover -s executor/tests -v`.

## Required integration before activation

- Install authorized discovery, evidence verification, CRM and Gmail connector adapters.
- Discovery must continue regional coverage until 50 new fully qualified drafts or
  a recorded access limitation; raw directory rows do not count.
- Before each send read live pause/runtime flags, sync replies, verify published
  contact and MX, deduplicate by clinic/email/domain/thread, then call existing
  atomic initial_claim. Send its exact body once, save provider id via sent and
  first_sent. Maximum 30 first claims per Asia/Tbilisi day. Never bypass the RPC.
- UNKNOWN tasks require Gmail reconciliation; neither timeout nor lease expiry
  allows another send. CRM RPCs and every other side-effecting handler also need
  their own idempotency keys. Task handlers must complete inside their lease.
- A stopped/declined lead never resumes automatically; NIO DENT stays stopped.
- Demo creation follows explicit recipient consent, source/permission checks,
  actual ka/en/ru build QA and a verified scoped public client URL.
- Run under a supervisor on an approved persistent host, report heartbeat and
  READY/RUNNING/BLOCKED/UNKNOWN counts. Do not silently swallow BLOCKED/UNKNOWN.

## Current blocker

The connected ChatGPT Gmail tool is available inside agent runs. No server-side
credential, endpoint or SDK for that exact connector has been provided or verified.
There is also no verified persistent host attached to this checkout. Do not copy
OAuth secrets or replace the transport with direct Gmail API to claim completion.
No scheduler, production deployment or real sending has been enabled by this code.
