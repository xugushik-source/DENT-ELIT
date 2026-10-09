"""Explicit per-build expense record; unknown costs never become zero."""
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


def record(build, category, amount, reference):
    folder = Path(build).resolve()
    allowed = {"research_ai", "manual_work", "hosting", "storage", "other"}
    if category not in allowed or not reference.strip(): raise ValueError("Valid expense category and evidence reference required")
    try: amount = Decimal(amount)
    except InvalidOperation as error: raise ValueError("Invalid expense amount") from error
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -6:
        raise ValueError("Expense must be finite, nonnegative USD with at most 6 decimals")
    # Exclusive lock avoids losing concurrent expense entries; CRM is system of record.
    lock = folder / "cost.lock"
    with lock.open("x"):
        try:
            file = folder / "cost.json"
            data = json.loads(file.read_text()) if file.exists() else {"currency":"USD","entries":[],"complete":False}
            data["entries"].append({"category":category,"amount":str(amount),"reference":reference})
            data["knownSubtotal"] = str(sum((Decimal(e["amount"]) for e in data["entries"]), Decimal(0)))
            data["total"] = None
            temp = folder / "cost.json.tmp"
            temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
            temp.replace(file)
        finally:lock.unlink()
    return data
