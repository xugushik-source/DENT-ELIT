"""Checks on actual build output, independent of the renderer."""
import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote


def manifest(folder):
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
    def handle_starttag(self, tag, attrs): self.tags.append((tag,dict(attrs)))
    handle_startendtag = handle_starttag


def check(folder, base_path="", origin="http://127.0.0.1"):
    folder = Path(folder)
    errors = []
    pages = list(folder.rglob("*.html"))
    if not pages: errors.append("No HTML pages")
    for file in pages:
        html = file.read_text()
        page = Page(); page.feed(html)
        tags = page.tags
        if not any(tag == "meta" and a.get("name") == "robots" and "noindex" in a.get("content", "") for tag,a in tags):
            errors.append(f"Missing noindex: {file.relative_to(folder)}")
        if "{{" in html or "{%" in html: errors.append(f"Unrendered template: {file.name}")
        for tag,a in tags:
            if tag == "form" and (a.get("action") or a.get("method", "get").lower() == "post"):
                errors.append("Active form")
            for key in ("href","src"):
                url = a.get(key, "")
                if tag == "a" and (urlsplit(url).scheme or url.startswith("//")):
                    errors.append(f"Outbound demo action: {url}")
                if not url.startswith("/") or url.startswith("//"): continue
                path = unquote(urlsplit(url).path)
                if base_path and not path.startswith(base_path + "/"):
                    errors.append(f"Outside mount: {path}");continue
                path = path[len(base_path):].lstrip("/")
                target = folder / path
                if not target.resolve().is_relative_to(folder.resolve()):
                    errors.append(f"Path escape: {path}");continue
                if target.is_dir(): target = target / "index.html"
                if not target.is_file(): errors.append(f"Missing link/asset: {path}")
            if tag == "link" and a.get("rel") in ("canonical","alternate"):
                if not a.get("href", "").startswith(origin + base_path + "/"):
                    errors.append("Canonical/alternate escaped origin or mount")
    if (folder / "sitemap.xml").exists(): errors.append("Demo exposes sitemap")
    if (folder / "robots.txt").read_text() != "User-agent: *\nDisallow: /\n": errors.append("Demo robots allows crawl")
    if errors: raise ValueError("Output checks: " + "; ".join(sorted(set(errors))))
    return {"passed":True,"htmlPages":len(pages),"checks":["noindex","links","assets","mount","inactive actions","no sitemap"]}
