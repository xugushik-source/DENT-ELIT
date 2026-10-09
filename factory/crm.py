"""Pure integration contract for the existing Order & Profit CRM. No outbound I/O.

Persist events and enforce permissions transactionally in the CRM's own store.
These helpers neither send mail nor create contracts or acknowledge payments.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta


@dataclass(frozen=True)
class Approval:
    clinic_id: str
    build_id: str
    owner_id: str
    approved_at: str
    acknowledged_pending: tuple[str, ...]


def can_start_demo(reply_kind):
    return reply_kind == "POSITIVE_INTEREST"


def approve(report, owner_id, acknowledged_pending):
    if not report["tests"]["passed"] or not owner_id:
        raise ValueError("Tested build and authenticated owner are required")
    pending = {p["path"] for p in report["pending"]}
    if set(acknowledged_pending) != pending:
        raise ValueError("Owner must acknowledge the complete pending-field list")
    return Approval(report["clinicId"],report["buildId"],owner_id,datetime.now(timezone.utc).isoformat(),tuple(sorted(pending)))


def can_share(report, approval, protected_preview, now=None):
    # The CRM must load owner identity from its trusted session, not customer text.
    now = now or datetime.now(timezone.utc)
    stamp = protected_preview.get("accessVerifiedAt")
    fresh = False
    if stamp:
        checked = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        fresh = timedelta(0) <= now - checked <= timedelta(hours=24)
    return bool(not report["synthetic"] and report["tests"]["passed"] and approval
        and approval.clinic_id == report["clinicId"] and approval.build_id == report["buildId"]
        and protected_preview.get("buildId") == report["buildId"] and protected_preview.get("authenticated") is True
        and fresh and protected_preview.get("url", "").startswith("https://"))


def client_response(state, kind):
    if state != "DEMO_SENT": raise ValueError("Client response requires a sent demo")
    return {"AGREES":"DEMO_APPROVED", "CHANGES":"REVISION_REQUESTED", "PRICE":"PRICE_QUESTION",
            "CALL":"OWNER_CONTACT_REQUESTED", "DECLINES":"CLOSED_LOST"}[kind]


PRICING = {
    "standard":{"currency":"USD","total":700,"after_demo_and_contract":300,"at_handover":400,"monthly":[]},
    "installments":{"currency":"USD","total":1000,"after_demo_and_contract":300,"at_handover":100,"monthly":[100]*6},
    "seoArmenia":{"monthlyMin":100,"monthlyMax":500},"seoInternational":{"monthlyMin":500},
    "hostingDomain":{"pricing":"provider actual cost, agreed before purchase","providerReceiptRequired":True,"markup":0},
}
