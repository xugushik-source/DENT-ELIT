"""Create an empty private clinic package, never clone another clinic's facts."""
import json
import uuid
from .policy import ROOT


def scaffold(languages, template_commit):
    schema = json.loads((ROOT / "schemas/clinic.schema.json").read_text())
    def blank(s):
        if "$ref" in s: return blank(schema["$defs"][s["$ref"].split("/")[-1]])
        if s.get("type") == "object":
            properties=s.get("properties",{})
            if {"value","status"} <= properties.keys():
                return {"value":None,"status":"UNKNOWN","sourceIds":[],"checkedAt":None,"reviewer":None}
            if set(properties)=={"hy","ru","en","ka"}: return {l:blank(properties[l]) for l in languages}
            return {k:blank(properties[k]) for k in s.get("required",[])}
        if s.get("type") == "array": return []
        if "const" in s:return s["const"]
        if "enum" in s:return s["enum"][0]
        if s.get("type") == "boolean":return False
        if s.get("type") in ("integer","number"):return 1
        return "v1"
    c=blank(schema)
    c.update(clinicId=str(uuid.uuid4()),templateCommit=template_commit,synthetic=False,deploymentMode="demo")
    c["languages"]={"enabled":languages,"default":languages[0],"uiVersion":"v1"}
    c["features"].update(servicesEnabled=True,doctorProfilesEnabled=True,technologyEnabled=True,reviewsEnabled=True,
                         galleryEnabled=True,bookingEnabled=True,whatsappEnabled=True,multilingualEnabled=len(languages)>1)
    return c
