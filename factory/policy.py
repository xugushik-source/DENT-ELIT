"""Fail closed on provenance, references, languages and asset rights."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
APPROVED = {"VERIFIED", "CLIENT_APPROVED"}


def facts(obj, path=""):
    if isinstance(obj, dict):
        if {"value", "status", "sourceIds", "checkedAt", "reviewer"} <= obj.keys():
            yield path, obj
        else:
            for key, value in obj.items():
                yield from facts(value, f"{path}/{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from facts(value, f"{path}/{index}")


def value(fact, default=None):
    return fact["value"] if fact["status"] in APPROVED else default


def instant(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def validate(config, asset_root=None, now=None):
    schema = json.loads((ROOT / "schemas/clinic.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(config),
                    key=lambda e: str(list(e.path)))
    if errors:
        raise ValueError("Schema: " + "; ".join(f"/{'/'.join(map(str,e.path))}: {e.message}" for e in errors))
    now = now or datetime.now(timezone.utc)
    if config["deploymentMode"] != "demo":
        raise ValueError("Factory v1 only builds demos; live release needs a separately reviewed workflow")
    if config["languages"]["default"] not in config["languages"]["enabled"]:
        raise ValueError("Default language is not enabled")
    if config["languages"]["uiVersion"] != "v1" or "ka" in config["languages"]["enabled"]:
        raise ValueError("Reviewed UI v1 supports hy, ru, en only")
    if any(config["features"][flag] for flag in ("beforeAfterEnabled","offersEnabled","blogEnabled")):
        raise ValueError("Before/after, offers and blog need separately reviewed components in factory v1")
    if not config["features"]["multilingualEnabled"] and len(config["languages"]["enabled"]) > 1:
        raise ValueError("Multilingual disabled but multiple languages enabled")
    sources = {s["id"]: s for s in config["sources"]}
    assets = {a["id"]: a for a in config["assets"]}
    if len(sources) != len(config["sources"]) or len(assets) != len(config["assets"]):
        raise ValueError("Duplicate source or asset id")
    def source_refs(ids):
        for sid in ids:
            s = sources.get(sid)
            if not s or s["clinicId"] != config["clinicId"] or s["accessStatus"] != "ALLOWED":
                raise ValueError(f"Source is absent, blocked, or belongs to another clinic: {sid}")
            if instant(s["retrievedAt"]) > now:
                raise ValueError(f"Future source timestamp: {sid}")
    pending = []
    used = set()
    for path, fact in facts(config):
        source_refs(fact["sourceIds"])
        if fact["status"] not in APPROVED:
            pending.append({"path": path, "status": fact["status"], "sourceIds": fact["sourceIds"]})
            continue
        checked = instant(fact["checkedAt"])
        if checked > now or now - checked > timedelta(days=90):
            raise ValueError(f"Reverify stale/future field: {path}")
        if isinstance(fact["value"], str) and fact["value"].startswith("https://"):
            url = urlsplit(fact["value"])
            if not url.hostname or url.username or url.password or any(c in fact["value"] for c in '\r\n\\'):
                raise ValueError(f"Unsafe URL: {path}")
        # Asset envelopes have an identifier value, never a path or remote fetch URL.
        if path.endswith(("/logo", "/logoSplash", "/favicon", "/photo", "/heroPhoto", "/workingPhoto",
                          "/hero", "/team", "/reception", "/finalCta")) or path.startswith("/media/gallery/"):
            aid = fact["value"]
            if aid not in assets:
                raise ValueError(f"Missing asset: {path}")
            used.add(aid)
    if value(config["brand"]["name"]) is None:
        raise ValueError("A verified clinic name is required")
    for group in ("services", "doctors", "technologies", "reviews", "statistics", "links"):
        items = config[group]
        for key in ("id", "slug"):
            ids = [i[key] for i in items if key in i]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Duplicate {group} {key}")
    ids = {group: {i["id"] for i in config[group]} for group in ("services", "doctors", "technologies")}
    for service in config["services"]:
        price = value(service["price"])
        if price:
            if price["currency"] not in {"USD","AMD","GEL","EUR","RUB","GBP"}:
                raise ValueError("Factory v1 supports reviewed two-decimal currencies USD/AMD/GEL/EUR/RUB/GBP")
            if price["basis"] == "range":
                if price["maxAmountMinor"] is None or price["maxAmountMinor"] < price["amountMinor"]:
                    raise ValueError("Price range requires a valid upper amount")
            elif price["maxAmountMinor"] is not None:
                raise ValueError("Fixed/from price must not have a range upper amount")
    for doctor in config["doctors"]:
        experience = value(doctor["experienceYears"])
        if experience is not None and (experience < 0 or int(experience) != experience):
            raise ValueError("Doctor experience must be nonnegative whole years")
    for group, mappings in (("services", {"doctorIds":"doctors", "technologyIds":"technologies", "relatedServiceIds":"services"}),
                            ("doctors", {"serviceIds":"services"})):
        for item in config[group]:
            for field, target in mappings.items():
                if not set(item[field]) <= ids[target]:
                    raise ValueError(f"Dangling {field}: {item['id']}")
    def localized(obj, path=""):
        if isinstance(obj, dict):
            if obj and set(obj) <= {"hy", "ru", "en", "ka"}:
                if not set(config["languages"]["enabled"]) <= set(obj):
                    raise ValueError(f"Missing translation at {path}; use UNKNOWN instead of fallback")
            else:
                for k, v in obj.items(): localized(v, path + "/" + k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj): localized(v, path + "/" + str(i))
    localized(config)
    for index,r in enumerate(config["reviews"]):
        if r["permission"] != "PERMITTED":
            pending.append({"path":f"/reviews/{index}/permission","status":r["permission"],"sourceIds":[]})
        if r["permission"] == "PERMITTED" and not r["proofRef"]:
            raise ValueError("Review permission requires proofRef")
    rating, count = value(config["rating"]["value"]), value(config["rating"]["count"])
    if rating is not None and not 0 <= rating <= 5:
        raise ValueError("Rating must be 0..5")
    if count is not None and (count < 0 or int(count) != count):
        raise ValueError("Rating count must be a nonnegative integer")
    hours = value(config["contact"]["hours"], [])
    if len({h["day"] for h in hours}) != len(hours):
        raise ValueError("Duplicate hours day")
    for h in hours:
        if (h["closed"] and (h["byAppointment"] or h["intervals"])) or any(i["open"] >= i["close"] for i in h["intervals"]):
            raise ValueError("Inconsistent hours; split overnight intervals by day")
    root = Path(asset_root).resolve() if asset_root is not None else None
    for aid in used:
        a = assets[aid]
        rights = a["rights"]
        if rights["status"] != "PERMITTED" or "demo" not in rights["allowedUses"]:
            raise ValueError(f"No demo rights for asset {aid}")
        source_refs(rights["sourceIds"])
        if rights["expiresAt"] and instant(rights["expiresAt"]) <= now:
            raise ValueError(f"Expired asset rights: {aid}")
        if a["scope"] == "clinic" and a["subjectClinicId"] != config["clinicId"]:
            raise ValueError(f"Cross-clinic asset: {aid}")
        if a["depiction"] != "generic_illustration" and (a["scope"] != "clinic" or a["subjectClinicId"] != config["clinicId"]):
            raise ValueError(f"Actual people, premises and logos must belong to this clinic: {aid}")
        if a["mime"] == "image/svg+xml":
            raise ValueError("SVG input is unsupported in v1; provide a reviewed raster asset")
        if root is not None:
            file = root / a["storageRef"]
            if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(root):
                raise ValueError(f"Unsafe or missing asset file: {aid}")
            data = file.read_bytes()
            if len(data) != a["bytes"] or hashlib.sha256(data).hexdigest() != a["sha256"]:
                raise ValueError(f"Asset hash/size mismatch: {aid}")
            from PIL import Image
            with Image.open(file) as image:
                expected = {"image/jpeg":"JPEG", "image/png":"PNG", "image/webp":"WEBP"}[a["mime"]]
                if image.format != expected or image.width * image.height > 40000000:
                    raise ValueError(f"Invalid raster type/size: {aid}")
                image.verify()
    return pending, used
