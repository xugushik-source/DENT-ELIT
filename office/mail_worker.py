"""Poll replies; dispatch approved messages only when operator enabled sending."""
import time
from datetime import datetime, timedelta, timezone


def run(sales, transport, stop, send_enabled=False, daily_limit=5, interval=300):
    sales.recover()
    while not stop.is_set():
        try:
            sales.sync(transport)
            if send_enabled:
                cutoff=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
                with sales.store.connect() as db:
                    # Count attempts, including unknown results, toward the limit.
                    attempts=db.execute("SELECT COUNT(*) FROM sales_audit WHERE kind='SEND_STARTED' AND created_at>=?",(cutoff,)).fetchone()[0]
                    queued=[r[0] for r in db.execute("SELECT id FROM sales_outbox WHERE status='APPROVED' ORDER BY created_at LIMIT ?",(max(0,daily_limit-attempts),))]
                for oid in queued:
                    if stop.is_set(): break
                    if sales.send(oid,transport,True)=='UNKNOWN': break
        except Exception:
            # Details stay in the ledger. Never print OAuth responses or retry sends.
            pass
        stop.wait(interval)
