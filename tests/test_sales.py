import tempfile
import unittest
from pathlib import Path
from office.store import Store
from office.sales import Sales

class Transport:
    def __init__(self,fail=False): self.calls=0; self.fail=fail
    def send(self,item):
        self.calls+=1
        if self.fail: raise TimeoutError()
        return {'id':'provider-1','threadId':'thread-1'}

class SalesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name));self.sales=Sales(self.store)
        self.lid=self.sales.lead('Synthetic clinic','test@example.org','synthetic-test')
    def tearDown(self): self.temp.cleanup()
    def draft(self): return self.sales.draft(self.lid,'Synthetic proposal','Synthetic content')
    def incoming(self): return {'id':'reply-1','thread_id':'thread-1','direction':'IN','subject':'Re: Synthetic proposal','body':'No more contact','sent_at':'2026-11-06T12:00:00+00:00','source':'synthetic-provider'}
    def test_approval_and_explicit_switch_required(self):
        oid=self.draft();t=Transport()
        with self.assertRaises(ValueError): self.sales.send(oid,t,True)
        self.sales.approve(oid)
        with self.assertRaises(ValueError): self.sales.send(oid,t)
        self.assertEqual(t.calls,0)
        self.assertEqual(self.sales.send(oid,t,True),'SENT')
        with self.assertRaises(ValueError): self.sales.send(oid,t,True)
        self.assertEqual(t.calls,1)
    def test_changed_content_cannot_use_old_approval(self):
        oid=self.draft();self.sales.approve(oid)
        with self.store.tx() as db: db.execute("UPDATE sales_outbox SET body='Changed' WHERE id=?",(oid,))
        t=Transport()
        with self.assertRaises(ValueError): self.sales.send(oid,t,True)
        self.assertEqual(t.calls,0)
    def test_unknown_result_blocks_retry_even_after_restart(self):
        oid=self.draft();self.sales.approve(oid);t=Transport(True)
        self.assertEqual(self.sales.send(oid,t,True),'UNKNOWN')
        again=Sales(self.store);again.recover()
        with self.assertRaises(ValueError): again.send(oid,t,True)
        with self.assertRaises(ValueError): self.draft()
        self.assertEqual(t.calls,1)
    def test_reply_cancels_pending_followup_and_is_idempotent(self):
        oid=self.draft();self.sales.approve(oid)
        self.assertEqual(self.sales.import_messages(self.lid,[self.incoming()]),1)
        self.assertEqual(self.sales.import_messages(self.lid,[self.incoming()]),0)
        snap=self.sales.snapshot()
        self.assertEqual(snap['outbox'][0]['status'],'CANCELLED')
        self.assertEqual(snap['leads'][0]['blocked'],1)
        self.assertEqual(snap['leads'][0]['status'],'REPLY_REVIEW')
        with self.assertRaises(ValueError): self.draft()
    def test_older_import_does_not_hide_newer_reply(self):
        self.sales.import_messages(self.lid,[self.incoming()])
        old={**self.incoming(),'id':'old-1','direction':'OUT','sent_at':'2026-11-06T13:00:00+04:00'}
        self.sales.import_messages(self.lid,[old])
        self.assertEqual(self.sales.snapshot()['leads'][0]['status'],'REPLY_REVIEW')
    def test_contact_dedupe_and_suppression(self):
        self.assertEqual(self.sales.lead('Other name','TEST@example.org','same-contact'),self.lid)
        oid=self.draft();self.sales.approve(oid)
        self.sales.task(self.lid,'Do not contact',True)
        with self.assertRaises(ValueError): self.sales.send(oid,Transport(),True)
    def test_crash_does_not_requeue(self):
        oid=self.draft()
        with self.store.tx() as db: db.execute("UPDATE sales_outbox SET status='SENDING' WHERE id=?",(oid,))
        self.sales.recover()
        self.assertEqual(self.sales.snapshot()['outbox'][0]['status'],'UNKNOWN')
    def test_sync_failure_not_fresh(self):
        class Broken:
            def messages(self,email): raise ConnectionError()
        with self.assertRaises(ValueError): self.sales.sync(Broken())
        self.assertIsNone(self.sales.snapshot()['sync']['checked_at'])
        self.assertTrue(self.sales.snapshot()['sync']['error'])
    def test_concurrent_dispatch_sends_once(self):
        from concurrent.futures import ThreadPoolExecutor
        oid=self.draft();self.sales.approve(oid);t=Transport()
        def send():
            try:return self.sales.send(oid,t,True)
            except ValueError:return 'BLOCKED'
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _:send(),range(2)))
        self.assertEqual(t.calls,1);self.assertCountEqual(results,['SENT','BLOCKED'])
    def test_duplicate_new_draft_after_send_is_blocked(self):
        oid=self.draft();self.sales.approve(oid);self.sales.send(oid,Transport(),True)
        with self.assertRaises(ValueError):self.draft()
    def test_five_attempts_limit(self):
        for i in range(5):
            oid=self.sales.draft(self.lid,'Proposal '+str(i),'Synthetic');self.sales.approve(oid);self.sales.send(oid,Transport(),True)
        oid=self.sales.draft(self.lid,'Sixth','Synthetic');self.sales.approve(oid);t=Transport()
        with self.assertRaises(ValueError):self.sales.send(oid,t,True)
        self.assertEqual(t.calls,0)
