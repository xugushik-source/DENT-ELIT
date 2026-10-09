"""Synthetic test data only. No real clinic identity, claims or patient information."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def clinic(asset_root, suffix="A", languages=("ru","en","hy")):
    schema = json.loads((ROOT / "schemas/clinic.schema.json").read_text())
    def empty(s):
        if "$ref" in s: return empty(schema["$defs"][s["$ref"].split("/")[-1]])
        if s.get("type") == "object":
            if {"value","status"} <= set(s.get("properties",{})):
                return {"value":None,"status":"UNKNOWN","sourceIds":[],"checkedAt":None,"reviewer":None}
            if set(s.get("properties",{})) == {"hy","ru","en","ka"}:
                return {l:empty(s["properties"][l]) for l in languages}
            return {k:empty(s["properties"][k]) for k in s.get("required",[])}
        if s.get("type") == "array":return []
        if "const" in s:return s["const"]
        if "enum" in s:return s["enum"][0]
        if s.get("type") == "boolean":return True
        if s.get("type") in ("integer","number"):return 1
        return "v1"
    c = empty(schema)
    c["clinicId"] = "11111111-1111-4111-8111-" + ("111111111111" if suffix == "A" else "222222222222")
    c["synthetic"] = True;c["templateCommit"] = "ea72702867890408621115ac49fce91dd18ab969";c["deploymentMode"] = "demo"
    c["languages"] = {"enabled":list(languages),"default":languages[0],"uiVersion":"v1"}
    timestamp = datetime.now(timezone.utc).isoformat()
    for flag in ("beforeAfterEnabled","offersEnabled","blogEnabled"): c["features"][flag] = False
    c["sources"]=[{"id":"fixture-evidence","clinicId":c["clinicId"],"kind":"client_material","url":None,
        "documentRef":"synthetic-test-only","retrievedAt":timestamp,"accessStatus":"ALLOWED","contentHash":None}]
    def verified(v):return {"value":v,"status":"VERIFIED","sourceIds":["fixture-evidence"],"checkedAt":timestamp,"reviewer":"test-only"}
    def loc(v):return {l:verified(v) for l in languages}
    c["brand"]["name"] = verified("Fixture " + suffix)
    c["brand"]["description"] = loc("Synthetic configuration for automated tests")
    c["contact"]["phone"] = verified("+37400000000" + ("1" if suffix=="A" else "2"))
    c["contact"]["whatsapp"] = copy.deepcopy(c["contact"]["phone"])
    c["contact"]["address"] = loc("Synthetic address " + suffix)
    c["contact"]["hours"] = verified([{"day":"mon","closed":False,"byAppointment":False,"intervals":[{"open":"08:15","close":"17:45"}]}])
    asset_root = Path(asset_root);asset_root.mkdir(parents=True,exist_ok=True)
    path = asset_root / ("fixture-image-" + suffix)
    Image.new("RGB",(80,60),"#B8925A" if suffix=="A" else "#221F1A").save(path,format="PNG")
    blob = path.read_bytes()
    a = {"id":"fixture-image-"+suffix,"storageRef":path.name,"sha256":hashlib.sha256(blob).hexdigest(),"mime":"image/png",
        "bytes":len(blob),"scope":"clinic","subjectClinicId":c["clinicId"],"depiction":"generic_illustration",
        "rights":{"status":"PERMITTED","sourceIds":["fixture-evidence"],"proofRef":"synthetic-test-only","allowedUses":["demo"],"expiresAt":None}}
    c["assets"]=[a];c["media"]["hero"] = verified(a["id"])
    service = empty(schema["$defs"]["service"])
    service.update(id="fixture-service",slug="fixture-service",name=loc("Synthetic service " + suffix),description=loc("Verified test description"),
                   intro=loc("Verified test intro"),medicalDetails=loc("Verified test details"))
    service["photo"] = verified(a["id"]);service["heroPhoto"] = verified(a["id"])
    c["services"]=[service]
    return c
