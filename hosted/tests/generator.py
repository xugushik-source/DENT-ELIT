"""Run after python hosted/prepare_engine.py. No network or real clinic records."""
import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('hosted_build',Path(__file__).parents[1]/'api/build.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class GeneratorTests(unittest.TestCase):
 def test_reviewed_renderer_builds_each_supported_language(self):
  for language in ('ru','en','hy'):
   with self.subTest(language=language):
    state={};result={}
    def bridge(action,payload=None):
     command=payload['command']
     if command=='create':state.update(payload['data']);return {'id':'00000000-0000-4000-8000-000000000001',**state}
     if command=='claim':return state
     if command=='finish':result.update(payload['data']);return {'status':'BUILT'}
     self.fail('Unexpected failure command')
    old=module.bridge;module.bridge=bridge
    try:
     module.initialize({'synthetic':True,'language':language})
     module.generate('00000000-0000-4000-8000-000000000001','https://office.example')
     self.assertTrue(result['report']['synthetic']);self.assertGreater(len(result['files']),5)
     self.assertTrue(any(f['path']==language+'/index.html' for f in result['files']))
     self.assertGreater(len(result['report']['pending']),0)
    finally:module.bridge=old
 def test_stopped_or_unknown_contact_cannot_initialize(self):
  old=module.bridge;module.bridge=lambda *args,**kw:{'leads':[]}
  try:
   with self.assertRaises(ValueError):module.initialize({'lead_id':'not-found','name':'Unverified','language':'ru'})
  finally:module.bridge=old
 def test_unreviewed_language_is_rejected(self):
  with self.assertRaises(ValueError):module.initialize({'synthetic':True,'language':'ka'})
if __name__=='__main__':unittest.main()
