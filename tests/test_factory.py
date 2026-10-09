import copy
import importlib.util
import json
import tempfile
import subprocess
import sys
import zipfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from factory.policy import validate, ROOT
from factory.report import manifest
from fixtures import clinic

spec = importlib.util.spec_from_file_location("factory_cli",ROOT / "factory.py")
cli = importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.assets = self.root / "assets"
        self.config = clinic(self.assets)
        self.input = self.root / "clinic.json"
    def tearDown(self):self.temp.cleanup()
    def build(self,c=None,**kwargs):
        self.input.write_text(json.dumps(c or self.config))
        return cli.build(self.input,self.assets,self.root / "work",**kwargs)
    def output(self,r):return self.root / "work" / r["clinicId"] / r["buildId"] / "site"
    def test_build_all_languages_and_cache(self):
        a = self.build();b = self.build()
        self.assertTrue(a["tests"]["passed"]);self.assertTrue(b["cacheHit"])
        self.assertEqual(a["files"],b["files"])
        for lang in ("ru","en","hy"):self.assertTrue((self.output(a) / lang / "services/fixture-service/index.html").exists())
    def test_no_cross_clinic_data_or_assets(self):
        a=self.build();c=clinic(self.assets,"B");b=self.build(c)
        folder=self.output(b)
        html="".join(p.read_text() for p in folder.rglob("*.html"))
        self.assertIn("Fixture B",html)
        for forbidden in ("Fixture A","ELIT DENT","Hakobyan","info@elitdent.example","Tbilisi","09:00–19:00","★ 4.9"):
            self.assertNotIn(forbidden,html)
        self.assertNotEqual(a["usedAssets"],b["usedAssets"])
        self.assertEqual(len(list((folder / "media").iterdir())),1)
    def test_unknown_doctors_services_reviews(self):
        self.config["services"]=[];self.config["doctors"]=[];self.config["reviews"]=[]
        self.assertTrue(self.build()["tests"]["passed"])
    def test_sourced_medical_copy_and_price_hidden(self):
        f=self.config["services"][0]["medicalDetails"]
        for fact in f.values():fact.update(value="UNVERIFIED_MEDICAL",status="SOURCED")
        r=self.build();html=(self.output(r) / "ru/services/fixture-service/index.html").read_text()
        self.assertNotIn("UNVERIFIED_MEDICAL",html)
    def test_missing_verification_evidence_blocks(self):
        self.config["brand"]["name"]["sourceIds"]=[]
        with self.assertRaises(ValueError):self.build()
    def test_wrong_source_clinic_blocks(self):
        self.config["sources"][0]["clinicId"]="22222222-2222-4222-8222-222222222222"
        with self.assertRaises(ValueError):self.build()
    def test_rights_hash_and_svg_block(self):
        c=copy.deepcopy(self.config);c["assets"][0]["rights"]["status"]="UNKNOWN"
        with self.assertRaises(ValueError):self.build(c)
        c=copy.deepcopy(self.config);c["assets"][0]["sha256"]="a"*64
        with self.assertRaises(ValueError):self.build(c)
        c=copy.deepcopy(self.config);c["assets"][0]["mime"]="image/svg+xml"
        with self.assertRaises(ValueError):self.build(c)
    def test_missing_translation_blocks(self):
        del self.config["services"][0]["name"]["hy"]
        with self.assertRaises(ValueError):self.build()
    def test_subpath_and_flags(self):
        self.config["features"]["servicesEnabled"]=False
        self.config["features"]["doctorProfilesEnabled"]=False
        self.config["features"]["reviewsEnabled"]=False
        self.config["features"]["technologyEnabled"]=False
        r=self.build(base_path="/review/fixture-a")
        self.assertTrue(r["tests"]["passed"])
        self.assertFalse((self.output(r)/"ru/services").exists())
    def test_injection_and_unsafe_mount(self):
        self.config["brand"]["name"]["value"]='<script>alert(1)</script> & "test"'
        r=self.build();html=(self.output(r)/"index.html").read_text()
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)
        with self.assertRaises(ValueError):self.build(base_path="/../dist")
        with self.assertRaises(ValueError):self.build(origin="https://owner:secret@example.com")
    def test_modified_cache_rejected(self):
        r=self.build();(self.output(r)/"ru/index.html").write_text("bad")
        with self.assertRaises(ValueError):self.build()
    def test_parallel_same_build(self):
        self.input.write_text(json.dumps(self.config))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:cli.build(self.input,self.assets,self.root/"work"),range(2)))
        self.assertEqual(results[0]["buildId"],results[1]["buildId"])
    def test_stale_future_and_live_blocked(self):
        for key,v in (("checkedAt","2000-01-01T00:00:00Z"),("checkedAt","2099-01-01T00:00:00Z")):
            c=copy.deepcopy(self.config);c["brand"]["name"][key]=v
            with self.assertRaises(ValueError):self.build(c)
        self.config["deploymentMode"]="live"
        with self.assertRaises(ValueError):self.build()
    def test_private_runtime_not_in_repo(self):
        self.input.write_text(json.dumps(self.config))
        with self.assertRaises(ValueError):cli.build(self.input,self.assets,ROOT / "factory-work")
    def test_expired_rights_and_cross_clinic_image_block(self):
        c=copy.deepcopy(self.config);c["assets"][0]["rights"]["expiresAt"]="2000-01-01T00:00:00Z"
        with self.assertRaises(ValueError):self.build(c)
        c=copy.deepcopy(self.config);c["assets"][0]["subjectClinicId"]="22222222-2222-4222-8222-222222222222"
        with self.assertRaises(ValueError):self.build(c)
    def test_disabled_action_flags(self):
        self.config["features"].update(bookingEnabled=False,whatsappEnabled=False)
        r=self.build();html=(self.output(r)/"ru/index.html").read_text()
        self.assertNotIn('data-open-booking',html)
        self.assertIn('aria-disabled="true"',html)
    def test_cost_subtotal_is_not_unknown_total(self):
        from factory.cost import record
        r=self.build();folder=self.output(r).parent
        data=record(folder,"research_ai","0.00325","usage-record-1")
        data=record(folder,"manual_work","4.00","time-record-1")
        self.assertEqual(data["knownSubtotal"],"4.00325");self.assertIsNone(data["total"])
        with self.assertRaises(ValueError):record(folder,"hosting","NaN","bad")
    def test_scaffold_contains_no_previous_clinic(self):
        from factory.scaffold import scaffold
        c=scaffold(["ru"],self.config["templateCommit"])
        self.assertEqual(c["brand"]["name"]["status"],"UNKNOWN")
        self.assertFalse(c["synthetic"]);self.assertEqual(c["doctors"],[]);self.assertEqual(c["assets"],[])
        with self.assertRaises(ValueError):validate(c,self.assets)
    def test_confirmed_price_doctor_equipment_and_review(self):
        verified=copy.deepcopy(self.config["brand"]["name"])
        unknown=copy.deepcopy(self.config["brand"]["foundedYear"])
        loc=copy.deepcopy(self.config["services"][0]["name"])
        def fact(v):
            f=copy.deepcopy(verified);f["value"]=v;return f
        doctor={"id":"fixture-doctor","slug":"fixture-doctor","name":fact("Synthetic doctor"),"specialization":loc,
            "qualifications":[loc],"certifications":[loc],"bio":loc,"experienceYears":fact(4),"photo":unknown,"workingPhoto":unknown,
            "languages":fact(["ru","en"]),"serviceIds":["fixture-service"]}
        self.config["doctors"]=[doctor]
        self.config["technologies"]=[{"id":"fixture-device","name":loc,"description":loc,"photo":unknown}]
        self.config["reviews"]=[{"id":"fixture-review","authorDisplay":fact("Synthetic reviewer"),"quote":loc,"permission":"PERMITTED","proofRef":"synthetic-test-only"}]
        self.config["services"][0].update(doctorIds=["fixture-doctor"],technologyIds=["fixture-device"],price=fact({"amountMinor":125050,"currency":"USD","basis":"range","maxAmountMinor":150000}))
        r=self.build();folder=self.output(r)
        self.assertIn("1250.50–1500.00 USD",(folder/"ru/services/fixture-service/index.html").read_text())
        self.assertIn("Synthetic doctor",(folder/"ru/doctors/fixture-doctor/index.html").read_text())
        self.assertIn("Synthetic reviewer",(folder/"ru/reviews/index.html").read_text())
    def test_package_excludes_private_configuration_and_report(self):
        r=self.build();folder=self.output(r).parent;output=self.root/"demo.zip"
        subprocess.run([sys.executable,str(ROOT/"factory.py"),"package","--build",str(folder),"--output",str(output)],check=True,capture_output=True)
        with zipfile.ZipFile(output) as package:
            names=set(package.namelist())
            self.assertEqual(names,set(r["files"]))
            self.assertFalse({"config.json","report.json","cost.json"} & names)


if __name__ == "__main__":unittest.main()
