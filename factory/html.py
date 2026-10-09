"""Apply demo-only safety and mount paths to rendered HTML, including root/404."""
import os
import json
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit


class DemoHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out = []
        self.base = os.environ.get("FACTORY_BASE_PATH", "")
        self.origin = os.environ.get("FACTORY_ORIGIN", "http://127.0.0.1")
        self.has_robots = False
        self.lang = "en"
        self.json_ld = False

    def tag(self, tag, attrs, closed=False):
        attrs = dict(attrs)
        if tag == "html": self.lang = attrs.get("lang", "en")
        if tag == "script": self.json_ld = attrs.get("type") == "application/ld+json"
        if tag == "meta" and attrs.get("name") == "robots":
            attrs["content"] = "noindex, nofollow, noarchive"
            self.has_robots = True
        if tag == "img" and not attrs.get("src"):
            return
        if tag == "img" and attrs.get("src") in json.loads(os.environ.get("FACTORY_ILLUSTRATIONS", "[]")):
            label = {"en":"Illustration", "ru":"Иллюстрация", "hy":"Նկարազարդում"}.get(self.lang,"Illustration")
            attrs["alt"] = label + " — " + attrs.get("alt", "")
            attrs["data-generic-illustration"] = "true"
        if tag == "link" and attrs.get("rel") in ("icon", "apple-touch-icon") and not attrs.get("href"):
            return
        if tag == "button" and "data-open-booking" in attrs and os.environ.get("FACTORY_BOOKING") == "False":
            attrs.pop("data-open-booking", None)
            attrs["disabled"] = None
        if tag == "a":
            href = attrs.get("href", "")
            if not href or urlsplit(href).scheme or href.startswith("//"):
                attrs.pop("href", None)
                attrs.pop("target", None)
                attrs["data-demo-action"] = ""
                attrs["role"] = "button"
                attrs["tabindex"] = "0"
                if os.environ.get("FACTORY_WHATSAPP") == "False" and ("wa.me" in href or "whatsapp" in attrs.get("class", "")):
                    attrs.pop("data-demo-action", None)
                    attrs["aria-disabled"] = "true"
                    attrs["tabindex"] = "-1"
        for key in ("href", "src"):
            link = attrs.get(key, "")
            if link.startswith("/") and not link.startswith("//"):
                attrs[key] = self.base + link
            elif link.startswith(self.origin + "/"):
                attrs[key] = self.origin + self.base + link[len(self.origin):]
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            attrs["content"] = attrs["content"].replace("url=/", "url=" + self.base + "/")
        if tag == "meta" and attrs.get("property") == "og:url":
            attrs["content"] = self.origin + self.base + attrs["content"][len(self.origin):]
        self.out.append("<" + tag + "".join(" " + k if v is None else f' {k}="{escape(v,quote=True)}"' for k,v in attrs.items()) + (" />" if closed else ">"))

    def handle_starttag(self, tag, attrs): self.tag(tag, attrs)
    def handle_startendtag(self, tag, attrs): self.tag(tag, attrs, True)
    def handle_endtag(self, tag):
        if tag == "script": self.json_ld = False
        if tag == "head" and not self.has_robots:
            self.out.append('<meta name="robots" content="noindex, nofollow, noarchive">')
        self.out.append(f"</{tag}>")
    def handle_data(self, data):
        if self.json_ld:
            def mount(obj):
                if isinstance(obj, str) and obj.startswith(self.origin + "/"):
                    return self.origin + self.base + obj[len(self.origin):]
                if isinstance(obj, dict): return {k:mount(v) for k,v in obj.items()}
                if isinstance(obj, list): return [mount(v) for v in obj]
                return obj
            data = json.dumps(mount(json.loads(data)),ensure_ascii=False).replace("<", "\\u003c")
        self.out.append(data)
    def handle_entityref(self, name): self.out.append(f"&{name};")
    def handle_charref(self, name): self.out.append(f"&#{name};")
    def handle_comment(self, data): self.out.append(f"<!--{data}-->")
    def handle_decl(self, decl): self.out.append(f"<!{decl}>")


def demo_html(html):
    parser = DemoHTML()
    parser.feed(html)
    return "".join(parser.out)
