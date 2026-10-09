#!/usr/bin/env python3
"""One shared template + private config/assets. No AI, network or deployment calls."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from datetime import date
from importlib.metadata import version
from urllib.parse import urlsplit

from factory.policy import ROOT, validate
from factory.prepare import prepare
from factory.report import check, manifest


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def build(config_path, assets, workspace, origin="http://127.0.0.1", base_path=""):
    start = time.monotonic()
    config_path, assets, workspace = Path(config_path).resolve(), Path(assets).resolve(), Path(workspace).resolve()
    # Public source tree is never a runtime data/output directory.
    for p in (config_path, assets, workspace):
        if p.is_relative_to(ROOT):
            raise ValueError("Keep clinic configurations, assets and outputs outside the public repository")
    u = urlsplit(origin)
    if u.username or u.password or u.query or u.fragment or u.path not in ("", "/") or not u.hostname:
        raise ValueError("Origin must be a bare http(s) origin without credentials")
    if u.scheme != "https" and not (u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost")):
        raise ValueError("Use HTTPS, or loopback HTTP for local review")
    origin = origin.rstrip("/")
    if base_path and not re.fullmatch(r"/(?:[a-z0-9-]+/)*[a-z0-9-]+", base_path):
        raise ValueError("Mount path must have safe lowercase segments and no trailing slash")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    pending, used = validate(config, assets)
    template = {}
    for folder in ("templates","static/css","static/js","factory","schemas"):
        for p in sorted((ROOT / folder).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts: template[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    for file in ("build.py","factory.py","requirements-factory.txt"):
        template[file] = hashlib.sha256((ROOT / file).read_bytes()).hexdigest()
    dependencies = {name:version(name) for name in ("Jinja2","jsonschema","Pillow","MarkupSafe","attrs","referencing","rpds-py","jsonschema-specifications","typing-extensions")}
    identity = digest({"config":config,"template":template,"origin":origin,"basePath":base_path,"dependencies":dependencies,"renderYear":date.today().year})
    target = workspace / config["clinicId"] / identity
    if target.exists():
        report = json.loads((target / "report.json").read_text())
        if manifest(target / "site") != report["files"]: raise ValueError("Cached output changed; rebuild into a clean workspace")
        check(target / "site",base_path,origin)
        return dict(report, cacheHit=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="build-",dir=target.parent) as temp:
        work = Path(temp)
        prepare(config, assets, work, used)
        env = dict(os.environ,FACTORY_BASE_PATH=base_path,FACTORY_ORIGIN=origin,
                   FACTORY_BOOKING=str(config["features"]["bookingEnabled"]),FACTORY_WHATSAPP=str(config["features"]["whatsappEnabled"]))
        generic = []
        for asset in config["assets"]:
            if asset["id"] in used and asset["depiction"] == "generic_illustration":
                ext = {"image/jpeg":"jpg", "image/png":"png", "image/webp":"webp"}[asset["mime"]]
                generic.append(f"/media/{asset['sha256']}.{ext}")
        env["FACTORY_ILLUSTRATIONS"] = json.dumps(generic)
        subprocess.run([sys.executable,str(ROOT / "build.py"),"--prepared",str(work),"--output",str(work / "site"),"--site-url",origin],
                       env=env,check=True,capture_output=True,text=True)
        # Copy only assets actually referenced by generated pages into the final package.
        html = "".join(p.read_text() for p in (work / "site").rglob("*.html"))
        used_hashes = set()
        for file in (work / "site/media").iterdir():
            if file.name in html: used_hashes.add(file.stem)
            else: file.unlink()
        used = {a["id"] for a in config["assets"] if a["id"] in used and a["sha256"] in used_hashes}
        checks = check(work / "site",base_path,origin)
        report = {"schemaVersion":"1.0","clinicId":config["clinicId"],"revision":config["revision"],"buildId":identity,
            "templateCommit":config["templateCommit"],"templateFingerprint":digest(template),"dependencies":dependencies,"synthetic":config["synthetic"],
            "mode":"demo","origin":origin,"basePath":base_path,"cacheHit":False,"pending":pending,"tests":checks,
            "usedAssets":sorted(used),"files":manifest(work / "site"),"ownerApprovalRequired":True,
            "preview":{"published":False,"access":"loopback basic auth","shareable":False},
            "cost":{"currency":"USD","buildAI":0,"buildCodexRuns":0,"researchAI":None,"hosting":None,
                    "manualMinutes":None,"buildSeconds":round(time.monotonic()-start,3),"total":None}}
        # Private evidence and config stay out of the site package.
        (work / "report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        (work / "config.json").write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding="utf-8")
        # Atomic rename: a concurrent winner is safe to reuse after verification.
        try: work.rename(target)
        except OSError:
            if not target.exists(): raise
            existing = json.loads((target / "report.json").read_text())
            if manifest(target / "site") != existing["files"]: raise ValueError("Concurrent output mismatch")
            return dict(existing,cacheHit=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command",required=True)
    s = sub.add_parser("init");s.add_argument("--output",type=Path,required=True);s.add_argument("--languages",nargs="+",choices=["hy","ru","en"],default=["hy","ru","en"]);s.add_argument("--template-commit",required=True)
    for name in ("check-config","build"):
        s = sub.add_parser(name);s.add_argument("--config",type=Path,required=True);s.add_argument("--assets",type=Path,required=True)
        if name == "build":
            s.add_argument("--workspace",type=Path,required=True);s.add_argument("--origin",default="http://127.0.0.1");s.add_argument("--base-path",default="")
    s = sub.add_parser("test");s.add_argument("--build",type=Path,required=True)
    s = sub.add_parser("package");s.add_argument("--build",type=Path,required=True);s.add_argument("--output",type=Path,required=True)
    s = sub.add_parser("preview");s.add_argument("--build",type=Path,required=True);s.add_argument("--port",type=int,default=8765)
    s = sub.add_parser("cost");s.add_argument("--build",type=Path,required=True);s.add_argument("--category",required=True);s.add_argument("--amount",required=True);s.add_argument("--reference",required=True)
    args = p.parse_args()
    try:
        if args.command == "init":
            from factory.scaffold import scaffold
            if args.output.resolve().is_relative_to(ROOT): raise ValueError("Private configuration must be outside repository")
            if not re.fullmatch("[a-f0-9]{40}",args.template_commit) or len(set(args.languages)) != len(args.languages):
                raise ValueError("Use a commit SHA and unique languages")
            config = scaffold(args.languages,args.template_commit)
            with args.output.open("x",encoding="utf-8") as file: json.dump(config,file,ensure_ascii=False,indent=2)
            result = {"clinicId":config["clinicId"],"readyToBuild":False,"requires":"verified clinic name and provenance"}
        elif args.command == "check-config":
            pending,used = validate(json.loads(args.config.read_text()),args.assets)
            result = {"valid":True,"pending":pending,"usedAssets":sorted(used)}
        elif args.command == "build": result = build(args.config,args.assets,args.workspace,args.origin,args.base_path)
        else:
            folder = args.build.resolve()
            if folder.is_relative_to(ROOT): raise ValueError("Runtime build must be outside repository")
            report = json.loads((folder / "report.json").read_text())
            if manifest(folder / "site") != report["files"]: raise ValueError("Output does not match tested build")
            result = check(folder / "site",report["basePath"],report["origin"])
            if args.command == "package":
                output = args.output.resolve()
                if output.is_relative_to(ROOT) or output.is_relative_to(folder): raise ValueError("Package destination must be outside repository/build")
                with zipfile.ZipFile(output,"x",compression=zipfile.ZIP_DEFLATED) as z:
                    for file in sorted((folder / "site").rglob("*")):
                        if file.is_file(): z.write(file,file.relative_to(folder / "site"))
                result = {"package":str(output),"published":False,"ownerApprovalRequired":True}
            elif args.command == "cost":
                from factory.cost import record
                result = record(folder,args.category,args.amount,args.reference)
            elif args.command == "preview":
                from factory.preview import serve
                serve(folder / "site",args.port,report["basePath"])
                return
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        p.exit(1,f"Factory failed: {error}\n")


if __name__ == "__main__": main()
