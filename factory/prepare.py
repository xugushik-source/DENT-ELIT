"""Convert verified facts to the existing ELIT DENT data contract; no legacy facts."""
import json
import shutil
from decimal import Decimal
from pathlib import Path

from .policy import ROOT, value


def prepare(config, asset_root, work, used):
    langs = config["languages"]["enabled"]
    def loc(data, fallback=""):
        return {l: value(data.get(l, {"status":"UNKNOWN"}), fallback) for l in langs}
    assets = {a["id"]: a for a in config["assets"]}
    def photo(fact):
        aid = value(fact)
        if not aid: return ""
        ext = {"image/jpeg":"jpg", "image/png":"png", "image/webp":"webp"}[assets[aid]["mime"]]
        return f"/media/{assets[aid]['sha256']}.{ext}"
    def good(data):
        return all(value(data[l]) is not None for l in langs)
    features = config["features"]
    services = [s for s in config["services"] if good(s["name"]) and features["servicesEnabled"]]
    doctors = [d for d in config["doctors"] if value(d["name"]) and good(d["specialization"]) and features["doctorProfilesEnabled"]]
    technologies = [t for t in config["technologies"] if good(t["name"]) and features["technologyEnabled"]]
    reviews = [r for r in config["reviews"] if value(r["authorDisplay"]) and good(r["quote"]) and r["permission"] == "PERMITTED" and features["reviewsEnabled"]]
    service_slugs = {s["id"]:s["slug"] for s in services}
    doctor_slugs = {d["id"]:d["slug"] for d in doctors}
    tech_ids = {t["id"] for t in technologies}
    raw_services = []
    for s in services:
        price = value(s["price"])
        formatted = None
        if price:
            amount = format(Decimal(price["amountMinor"]) / 100, ".2f")
            if price["basis"] == "range": amount += "–" + format(Decimal(price["maxAmountMinor"]) / 100, ".2f")
            prefix = {"ru":"От", "en":"From", "hy":"Սկսած"}
            formatted = {"amount":amount,"currency":price["currency"],
                         "prefix":{l:prefix[l] if price["basis"] == "from" else "" for l in langs},"note":{l:"" for l in langs}}
        raw_services.append({"slug":s["slug"], "icon":"tooth", "flagship":False,
            "title":loc(s["name"]), "eyebrow":loc(s["name"]), "shortCopy":loc(s["description"]),
            "intro":loc(s["intro"]), "aboutTreatment":loc(s["medicalDetails"]),
            "whoItIsFor":{l:[] for l in langs},
            "benefits":{l:[value(b[l]) for b in s["benefits"] if value(b[l])] for l in langs},
            "faq":[{"q":loc(f["question"]), "a":loc(f["answer"])} for f in s["faq"] if good(f["question"]) and good(f["answer"])],
            "price":formatted,
            "cardImage":photo(s["photo"]), "heroImage":photo(s["heroPhoto"]),
            "doctorSlug":next((doctor_slugs[i] for i in s["doctorIds"] if i in doctor_slugs),None),
            "technologyRefs":[i for i in s["technologyIds"] if i in tech_ids],
            "relatedSlugs":[service_slugs[i] for i in s["relatedServiceIds"] if i in service_slugs]})
    raw_doctors = [{"slug":d["slug"], "name":value(d["name"]), "role":loc(d["specialization"]),
        "photo":photo(d["photo"]), "workingPhoto":photo(d["workingPhoto"]), "quote":{l:"" for l in langs},
        "bio":loc(d["bio"]), "languages":value(d["languages"],[]), "services":[service_slugs[i] for i in d["serviceIds"] if i in service_slugs],
        "experienceYears":value(d["experienceYears"]),
        "education":{l:[value(q[l]) for q in d["qualifications"] if value(q[l])] for l in langs},
        "certifications":[{"id":str(i), "label":loc(q)} for i,q in enumerate(d["certifications"]) if good(q)]} for d in doctors]
    raw_tech = [{"slug":t["id"],"icon":"scan", "name":loc(t["name"]), "shortExplain":loc(t["description"]),
                 "patientBenefit":{l:"" for l in langs}, "image":photo(t["photo"])} for t in technologies]
    raw_reviews = {"items":[{"id":r["id"], "authorInitial":{l:value(r["authorDisplay"]) for l in langs}, "quote":loc(r["quote"])} for r in reviews]}
    name = value(config["brand"]["name"])
    phone, wa = value(config["contact"]["phone"],""), value(config["contact"]["whatsapp"],"")
    rating = {k:value(config["rating"][k]) for k in ("value","count")}
    site = {"brand":{"clinicName":name,"developer":"ORDER PROFIT", "tagline":loc(config["brand"]["slogan"]),
            "foundedYear":value(config["brand"]["foundedYear"],""),
            "logo":{k:photo(config["brand"]["logo"]) for k in ("mark","full")}},
        "contact":{"phone":phone,"phoneUri":"tel:"+phone if phone else "", "whatsapp":wa,
            "whatsappNumber":"".join(c for c in wa if c.isdigit()), "whatsappUri":"https://wa.me/"+wa.lstrip("+") if wa else "",
            "email":value(config["contact"]["email"],""), "emailIsLive":False, "address":loc(config["contact"]["address"]),
            "mapsEmbedUrl":None,"mapsUrl":value(config["contact"]["map"],""),
            "socials":{"instagram":value(config["contact"]["instagram"]),"facebook":value(config["contact"]["facebook"]),"tiktok":None,"youtube":None},
            "hours":value(config["contact"]["hours"],[]),
            "links":[{"label":loc(link["label"]),"url":value(link["url"],"")} for link in config["links"] if good(link["label"])],
            "bookingLabel":loc(config["booking"]["displayLabel"]),"bookingUrl":value(config["booking"]["providerUrl"],"")},
        "seo":{"productionUrl":"http://127.0.0.1", "country":value(config["contact"]["country"],""),"city":value(config["contact"]["city"],"")},
        "languages":{"supported":langs,"default":config["languages"]["default"]},
        "features":dict(features, demoMode=True, enableServices=features["servicesEnabled"], enableDoctors=features["doctorProfilesEnabled"], enableTechnology=features["technologyEnabled"], enableReviews=features["reviewsEnabled"], enableAbout=True),"factoryMode":True,"clinicId":config["clinicId"],
        "trustItems":[],"stats":[],"rating":rating,
        "media":dict({k:photo(config["media"][k]) for k in ("hero","team","reception","finalCta")},gallery=[photo(f) for f in config["media"]["gallery"] if value(f)] if features["galleryEnabled"] else []),
        "logoSplash":photo(config["brand"]["logoSplash"]),"favicon":photo(config["brand"]["favicon"]),
        "homepageSections":["hero"] + (["trust"] if config["trustClaims"] or config["statistics"] else []) +
            (["services"] if services else []) + (["technology"] if technologies else []) +
            (["doctorSpotlight","team"] if doctors else []) + (["reviews"] if reviews else []) + ["finalCTA"]}
    for i, claim in enumerate(config["trustClaims"]):
        if good(claim): site["trustItems"].append({"key":f"claim{i}"})
    for stat in config["statistics"]:
        if value(stat["value"]) is not None and good(stat["label"]):
            site["stats"].append({"key":stat["id"],"value":value(stat["value"])})
    (work / "data").mkdir()
    (work / "content").mkdir()
    (work / "static").mkdir()
    for fname,data in (("site",site),("services",raw_services),("doctors",raw_doctors),("technology",raw_tech),("reviews",raw_reviews),("process-default",[])):
        (work / "data" / f"{fname}.json").write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
    for lang in langs:
        t = json.loads((ROOT / "factory/ui" / f"{lang}.json").read_text())
        def replace(obj):
            if isinstance(obj,str): return obj.replace("{clinicName}",name)
            if isinstance(obj,dict): return {k:replace(v) for k,v in obj.items()}
            if isinstance(obj,list): return [replace(v) for v in obj]
            return obj
        t = replace(t)
        description = loc(config["brand"]["description"])[lang]
        t["hero"]["headline"] = name
        t["hero"]["description"] = description
        t["meta"]["titleSuffix"] = value(config["seo"]["title"][lang],name)
        t["seoDescription"] = value(config["seo"]["description"][lang],description)
        t["aboutPage"]["sections"]["philosophy"]["body"] = description
        for i,claim in enumerate(config["trustClaims"]):
            t["trust"]["items"][f"claim{i}"] = {"title":value(claim[lang],""),"desc":""}
        for stat in config["statistics"]: t["trust"]["stats"][stat["id"]] = value(stat["label"][lang],"")
        (work / "content" / f"{lang}.json").write_text(json.dumps(t,ensure_ascii=False),encoding="utf-8")
    for folder in ("css","js"):
        shutil.copytree(ROOT / "static" / folder, work / "static" / folder)
    tokens = "\n:root {\n"
    for field,token in (("background","--color-bg"),("accent","--color-accent"),("text","--color-text")):
        if value(config["brand"]["colors"][field]): tokens += f"{token}: {value(config['brand']['colors'][field])};\n"
    with (work / "static/css/tokens.css").open("a") as f: f.write(tokens + "}\n")
    (work / "static/media").mkdir()
    for aid in used:
        a = assets[aid]
        ext = {"image/jpeg":"jpg", "image/png":"png", "image/webp":"webp"}[a["mime"]]
        shutil.copyfile(Path(asset_root) / a["storageRef"], work / "static/media" / f"{a['sha256']}.{ext}")
    return site
