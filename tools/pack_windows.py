"""Build an offline Windows x64 office from reviewed source and vendor wheels.

No credential, cloud service, AI call or deployment is involved.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SHA = "d297e5ff019966817ad8502465176139f2d3d840fa4ed84b13bed399a6ab1f15"
RUNTIME_URL = "https://www.python.org/ftp/python/3.14.7/python-3.14.7-embed-amd64.zip"
FOLDERS = ("factory", "office", "schemas", "templates", "static/css", "static/js", "tests")
FILES = ("office.py", "factory.py", "build.py", "requirements-factory.txt")


def safe_extract(archive, destination):
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            target = (destination / entry.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Unsafe vendor archive path")
        z.extractall(destination)


def source_release(destination, commit):
    destination.mkdir(parents=True)
    for folder in FOLDERS:
        shutil.copytree(ROOT / folder, destination / folder,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in FILES:
        shutil.copy2(ROOT / name, destination / name)
    hashes = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(destination.rglob("*")) if p.is_file()}
    (destination / "factory-release.json").write_text(
        json.dumps({"commit": commit, "files": hashes}, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-zip", required=True, type=Path)
    parser.add_argument("--wheel-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.runtime_zip.read_bytes()).hexdigest() != RUNTIME_SHA:
        raise ValueError("Python runtime checksum mismatch")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise ValueError("Commit reviewed source before packaging")
    with tempfile.TemporaryDirectory() as scratch:
        package = Path(scratch) / "Order-Profit-Local"
        package.mkdir()
        source_release(package / "app", commit)
        safe_extract(args.runtime_zip, package / "runtime")
        (package / "runtime/python314._pth").write_text(
            "python314.zip\n.\n../app\n../packages\nimport site\n", encoding="ascii")
        subprocess.run([
            __import__("sys").executable, "-m", "pip", "install", "--disable-pip-version-check",
            "--no-index", "--find-links", str(args.wheel_dir.resolve()), "--only-binary=:all:",
            "--platform", "win_amd64", "--python-version", "3.14", "--implementation", "cp",
            "--abi", "cp314", "--no-compile", "--target", str(package / "packages"),
            "-r", str(ROOT / "requirements-factory.txt"),
        ], check=True)
        start = '@echo off\r\nchcp 65001 >nul\r\ncd /d "%~dp0app"\r\n"%~dp0runtime\\python.exe" -X utf8 office.py --open-browser\r\nif errorlevel 1 pause\r\n'
        (package / "START.cmd").write_bytes(start.encode("utf-8"))
        check = '@echo off\r\nchcp 65001 >nul\r\ncd /d "%~dp0app"\r\n"%~dp0runtime\\python.exe" -X utf8 -m unittest discover -s tests -p "test_*.py"\r\npause\r\n'
        (package / "CHECK.cmd").write_bytes(check.encode("utf-8"))
        shutil.copy2(ROOT / "WINDOWS_LOCAL.md", package / "READ-ME.txt")
        (package / "VENDOR-SOURCES.json").write_text(json.dumps({
            "python": {"url": RUNTIME_URL, "sha256": RUNTIME_SHA},
            "wheels": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(args.wheel_dir.glob("*.whl"))},
            "sourceCommit": commit,
        }, indent=2), encoding="utf-8")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(package.rglob("*")):
                if p.is_file(): z.write(p, p.relative_to(package.parent).as_posix())
    print(json.dumps({"file": str(args.output.resolve()), "bytes": args.output.stat().st_size,
                      "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
