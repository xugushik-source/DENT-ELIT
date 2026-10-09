import unittest
from datetime import datetime, timezone
from factory.crm import approve, can_share, can_start_demo, client_response, PRICING


class CRMTests(unittest.TestCase):
    def report(self):return {"clinicId":"clinic","buildId":"build1","tests":{"passed":True},"pending":[{"path":"/phone"}],"synthetic":False}
    def test_positive_reply_only(self):
        self.assertTrue(can_start_demo("POSITIVE_INTEREST"))
        for kind in ("AUTO_REPLY","BOUNCE","NEGATIVE","UNKNOWN"):self.assertFalse(can_start_demo(kind))
    def test_owner_approval_bound_to_build(self):
        r=self.report()
        with self.assertRaises(ValueError):approve(r,"owner",[])
        a=approve(r,"owner",["/phone"])
        preview={"url":"https://preview.example.com","buildId":"build1","authenticated":True,"accessVerifiedAt":datetime.now(timezone.utc).isoformat()}
        self.assertFalse(can_share(r,None,preview));self.assertTrue(can_share(r,a,preview))
        r["buildId"]="build2";self.assertFalse(can_share(r,a,preview))
    def test_synthetic_and_unprotected_never_shared(self):
        r=self.report();a=approve(r,"owner",["/phone"])
        self.assertFalse(can_share(r,a,{}))
        r["synthetic"]=True
        self.assertFalse(can_share(r,a,{"url":"https://preview.example.com","buildId":"build1","authenticated":True,"accessVerifiedAt":datetime.now(timezone.utc).isoformat()}))
    def test_client_approval_and_prices(self):
        self.assertEqual(client_response("DEMO_SENT","AGREES"),"DEMO_APPROVED")
        self.assertEqual(client_response("DEMO_SENT","DECLINES"),"CLOSED_LOST")
        for plan in ("standard","installments"):
            p=PRICING[plan];self.assertEqual(p["total"],p["after_demo_and_contract"]+p["at_handover"]+sum(p["monthly"]))


if __name__ == "__main__":unittest.main()
