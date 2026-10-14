import base64
import json
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path

from office.server import server
from office.store import Store
from office.workflow import Director
from office.sample import create_sample


class OfficeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        with socket.socket() as s:s.bind(("127.0.0.1",0));port=s.getsockname()[1]
        self.origin=f"http://127.0.0.1:{port}"
        self.auth="Basic "+base64.b64encode(b"owner:synthetic-test-password-123").decode()
        self.http=server(self.root,port,"synthetic-test-password-123",actor="synthetic-test-owner")
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.csrf=self.request('/api/bootstrap')[1]['csrf']
    def tearDown(self):
        self.http.director.stop.set();self.http.worker.join(timeout=20)
        self.http.shutdown();self.http.server_close();self.thread.join(timeout=5);self.temp.cleanup()
    def request(self,path,body=None,auth=True,csrf=True,origin=None):
        headers={}
        if auth:headers['Authorization']=self.auth
        if body is not None:
            headers['Content-Type']='application/json'
            if csrf:headers['X-CSRF-Token']=self.csrf
            if origin:headers['Origin']=origin
        request=urllib.request.Request(self.origin+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        try:
            with urllib.request.urlopen(request) as r:data=r.read();code=r.status;mime=r.headers.get('Content-Type','')
        except urllib.error.HTTPError as e:data=e.read();code=e.code;mime=e.headers.get('Content-Type','')
        return code,json.loads(data) if 'application/json' in mime else data
    def sample(self):return self.request('/api/sample',{})[1]
    def wait(self,cid):
        for _ in range(200):
            c=self.request('/api/clinics/'+cid)[1]
            if c['status'] in ('DEMO_READY','BUILD_FAILED'):return c
            time.sleep(.05)
        self.fail('worker did not finish')
    def test_full_cycle_with_no_send_and_persistence(self):
        c=self.sample();cid=c['id']
        self.assertTrue(c['synthetic'])
        self.assertEqual(self.request('/api/clinics/'+cid+'/validate',{})[0],200)
        self.assertEqual(self.request('/api/clinics/'+cid+'/draft',{'version':c['version']})[0],400)
        self.assertEqual(self.request('/api/clinics/'+cid+'/build',{'version':c['version']})[0],202)
        c=self.wait(cid);self.assertEqual(c['status'],'DEMO_READY')
        report=c['job']['report'];self.assertTrue(report['tests']['passed'])
        path='/demo/'+c['job']['id']+'/ru/'
        code,html=self.request(path);self.assertEqual(code,200);self.assertIn('noindex',html.decode())
        self.assertEqual(self.request(path,auth=False)[0],401)
        self.assertEqual(self.request('/demo/'+c['job']['id']+'/js/main.js',auth=False)[0],401)
        body={'version':c['version'],'pendingPaths':[p['path'] for p in report['pending']]}
        self.assertEqual(self.request('/api/clinics/'+cid+'/approve',body)[0],400)
        c=self.request('/api/clinics/'+cid+'/viewed',{'version':c['version']})[1]
        body['version']=c['version'];c=self.request('/api/clinics/'+cid+'/approve',body)[1]
        self.assertEqual(c['status'],'OWNER_APPROVED');self.assertTrue(c['approval']['simulation'])
        c=self.request('/api/clinics/'+cid+'/draft',{'version':c['version']})[1]
        self.assertEqual(c['status'],'DRAFT_READY');self.assertEqual(c['draft']['delivery'],'NOT_SENT')
        self.assertIn('$700',c['draft']['body']);self.assertIn('$1000',c['draft']['body'])
        self.assertNotIn('GitHub',c['draft']['body']);self.assertFalse(c['draft']['sendEnabled'])
        self.assertEqual(self.request('/api/clinics/'+cid+'/send',{})[0],404)
        restored=Store(self.root).get(cid);self.assertEqual(restored['draft'],c['draft'])
        restored['config']['brand']['description']['ru']['value']='Новое синтетическое описание'
        changed=self.request('/api/clinics/'+cid+'/config',{'version':restored['version'],'config':restored['config']})[1]
        self.assertIsNone(changed['approval']);self.assertIsNone(changed['draft'])
        self.assertEqual(changed['config']['brand']['description']['ru']['status'],'SOURCED')
        self.assertEqual(self.request('/api/clinics/'+cid+'/draft',{'version':changed['version']})[0],400)
    def test_auth_csrf_and_private_paths(self):
        for path in ('/','/app.js','/api/bootstrap'):
            self.assertEqual(self.request(path,auth=False)[0],401)
        self.assertEqual(self.request('/api/sample',{},csrf=False)[0],403)
        self.assertEqual(self.request('/api/sample',{},origin='https://untrusted.example')[0],403)
        self.assertEqual(self.request('/factory.sqlite3')[0],404)
    def test_pause_and_version_conflict(self):
        c=self.sample();cid=c['id']
        self.request('/api/director',{'paused':True})
        self.assertEqual(self.request('/api/clinics/'+cid+'/build',{'version':c['version']})[0],400)
        self.request('/api/director',{'paused':False})
        updated=self.request('/api/clinics/'+cid+'/config',{'version':c['version'],'config':c['config']})[1]
        self.assertEqual(self.request('/api/clinics/'+cid+'/config',{'version':c['version'],'config':c['config']})[0],400)
        self.assertGreater(updated['revision'],c['revision'])
    def test_superseded_job_cannot_overwrite_new_data(self):
        self.http.director.stop.set();self.http.worker.join(timeout=20)
        c=self.sample();store=self.http.store
        store.queue(c['id'],c['version']);job=store.claim();c=store.get(c['id'])
        store.save(c['id'],c['version'],c['config'])
        store.finish(job,{'buildId':'old-build'},None)
        fresh=store.get(c['id']);self.assertEqual(fresh['status'],'DATA_REQUIRED');self.assertIsNone(fresh['current_job'])
        with store.connect() as db:self.assertEqual(db.execute('SELECT status FROM jobs WHERE id=?',(job['id'],)).fetchone()[0],'SUPERSEDED')
    def test_single_director_lock(self):
        with self.assertRaises(ValueError):server(self.root,0,'another-synthetic-password')
    def test_interrupted_job_recovers_and_finishes(self):
        self.http.director.stop.set();self.http.worker.join(timeout=20)
        c=self.sample();store=self.http.store
        jid=store.queue(c['id'],c['version']);store.claim()
        store.recover()
        with store.connect() as db:self.assertEqual(db.execute('SELECT status FROM jobs WHERE id=?',(jid,)).fetchone()[0],'QUEUED')
        self.assertTrue(self.http.director.step())
        self.assertEqual(store.get(c['id'])['status'],'DEMO_READY')


if __name__=='__main__':unittest.main()
