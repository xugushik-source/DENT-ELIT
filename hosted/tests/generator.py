"""Run after python hosted/prepare_engine.py. No network or real clinic records."""
import importlib.util
import io,base64
from PIL import Image
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
 def test_real_card_requires_and_builds_its_own_content_and_photo(self):
  state={};result={}
  def bridge(action,payload=None):
   if action=='snapshot':return {'leads':[{'id':'lead-1','name':'Clinic Verified','blocked':False,'source':'https://clinic.example/about'}]}
   command=payload['command']
   if command=='create':state.update(payload['data']);return {'id':'00000000-0000-4000-8000-000000000002',**state}
   if command=='claim':return state
   if command=='finish':result.update(payload['data']);return {'status':'BUILT'}
   self.fail('Unexpected command '+command)
  old=module.bridge;module.bridge=bridge
  try:
   with self.assertRaises(ValueError):module.initialize({'lead_id':'lead-1','confirmed':True})
   image=io.BytesIO();Image.new('RGB',(800,600),'blue').save(image,'JPEG')
   module.initialize({'lead_id':'lead-1','language':'ru','confirmed':True,'description':'Описание клиники, подтверждённое владельцем по материалам компании.','services':'Осмотр | Консультация врача','hero':base64.b64encode(image.getvalue()).decode()})
   module.generate('00000000-0000-4000-8000-000000000002','https://office.example')
   page=next(f for f in result['files'] if f['path']=='ru/index.html')
   html=base64.b64decode(page['content']).decode()
   self.assertIn('Clinic Verified',html);self.assertIn('Консультация врача',html);self.assertIn('/media/',html)
   self.assertNotIn('ELIT DENT',html);self.assertFalse(result['report']['synthetic'])
   self.assertTrue(any(f['mime']=='image/jpeg' for f in result['files']))
  finally:module.bridge=old
 def test_stopped_or_unknown_contact_cannot_initialize(self):
  old=module.bridge;module.bridge=lambda *args,**kw:{'leads':[]}
  try:
   with self.assertRaises(ValueError):module.initialize({'lead_id':'not-found','name':'Unverified','language':'ru'})
  finally:module.bridge=old
 def test_unreviewed_language_is_rejected(self):
  with self.assertRaises(ValueError):module.initialize({'synthetic':True,'language':'ka'})
if __name__=='__main__':unittest.main()
