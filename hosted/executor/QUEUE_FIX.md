# Initial queue recovery — 12 November 2026

Root cause: initial_draft returned an existing outbox ID without restoring FIRST_DRAFT after research changed the stage to QUALIFIED. Do not change stages directly or remove hash guards to send.

Fix deployed: initial_draft restores FIRST_DRAFT only for a fresh QUALIFIED, unblocked clinic, with no correspondence and an unchanged DRAFT matching lead, recipient, subject and saved text hash. Repeated calls reuse the same draft. Research cannot reset contacted, suppressed or owner-paused stages.

Verified in live database using rolled-back synthetic fixtures: restore, no duplicate outbox, tamper rejection and OWNER_PAUSED protection passed. Sending still requires initial_claim and Gmail provider acknowledgement. UNKNOWN is never retried automatically. Legacy RESEARCH/UNKNOWN records still require factual qualification; this fix does not auto-qualify them.
