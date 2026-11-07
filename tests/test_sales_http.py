import base64
import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch
from office.server import server

class FakeGmail:
    def __init__(self): self.sent=[];self.reply=False
    def send(self,item): self.sent.append(item);return {'id':'synthetic-provider-id','threadId':'synthetic-thread'}
    def messages(self,email):
        return [{'id':'synthetic-reply','thread_id':'synthetic-thread','direction':'IN','subject':'Re: Test','body':'Please stop',
                 'sent_at':'2026-11-06T12:00:00Z','source':'synthetic-gmail'}] if self.reply else []

class SalesHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.fake=FakeGmail()
        with patch('office.gmail.configured',return_value=self.fake),patch.dict('os.environ',{'FACTORY_MAIL_SEND_ENABLED':'yes','FACTORY_MAIL_WORKER_ENABLED':'no'}):
            self.http=server(Path(self.tmp.name),0,'synthetic-test-password-123')
        self.origin=f'http://127.0.0.1:{self.http.server_port}';self.csrf=''
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.csrf=self.req('/api/bootstrap')[1]['csrf']
    def tearDown(self): self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def req(self,path,body=None,auth=True,csrf=True):
        h={}
        if auth:h['Authorization']='Basic '+base64.b64encode(b'owner:synthetic-test-password-123').decode()
        if body is not None:
            h.update({'Content-Type':'application/json','Origin':'http://127.0.0.1:0'})
            if csrf:h['X-CSRF-Token']=self.csrf
        req=urllib.request.Request(self.origin+path,data=json.dumps(body).encode() if body is not None else None,headers=h)
        try:
            with urllib.request.urlopen(req) as r:return r.status,json.loads(r.read())
        except urllib.error.HTTPError as e:return e.code,json.loads(e.read()) if e.code!=401 else {}
    def test_full_sales_cycle_and_reply_stop(self):
        self.assertEqual(self.req('/api/sales',auth=False)[0],401)
        self.assertEqual(self.req('/api/sales/lead',{},csrf=False)[0],403)
        code,r=self.req('/api/sales/lead',{'name':'Synthetic clinic','email':'test@example.org','source':'synthetic'})
        self.assertEqual(code,201);lid=r['id']
        code,r=self.req('/api/sales/draft',{'lead_id':lid,'subject':'Test','body':'Synthetic only'})
        self.assertEqual(code,201);oid=r['id']
        self.assertEqual(self.req('/api/sales/send',{'id':oid})[0],400)
        self.assertEqual(self.req('/api/sales/approve',{'id':oid})[0],200)
        self.assertEqual(self.req('/api/sales/send',{'id':oid})[1]['status'],'SENT')
        self.assertEqual(self.req('/api/sales/send',{'id':oid})[0],400)
        self.assertEqual(len(self.fake.sent),1)
        self.fake.reply=True
        self.assertEqual(self.req('/api/sales/sync',{})[0],200)
        snap=self.req('/api/sales')[1]
        self.assertEqual(snap['leads'][0]['blocked'],1)
        self.assertTrue(snap['sync']['checked_at'])
        self.assertEqual(self.req('/api/sales/draft',{'lead_id':lid,'subject':'Again','body':'No'})[0],400)
