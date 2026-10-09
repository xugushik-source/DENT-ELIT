"""Restricted loopback review. Never a public hosting or auth deployment adapter."""
import base64
import hmac
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


def serve(site, port, base_path=""):
    password = os.environ.get("FACTORY_PREVIEW_PASSWORD", "")
    if len(password) < 16: raise ValueError("Set FACTORY_PREVIEW_PASSWORD to at least 16 characters")
    expected = "Basic " + base64.b64encode(("owner:"+password).encode()).decode()
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(site),**kwargs)
        def authorized(self):
            if not hmac.compare_digest(self.headers.get("Authorization",""),expected):
                self.send_response(401);self.send_header("WWW-Authenticate",'Basic realm="Private clinic demo"');self.end_headers();return False
            path = urlsplit(self.path).path
            if base_path and not path.startswith(base_path + "/"):
                self.send_error(404);return False
            self.path = self.path[len(base_path):] if base_path else self.path
            return True
        def do_GET(self):
            if self.authorized(): super().do_GET()
        def do_HEAD(self):
            if self.authorized(): super().do_HEAD()
        def list_directory(self,path): self.send_error(404);return None
        def end_headers(self):
            self.send_header("X-Robots-Tag","noindex, nofollow, noarchive")
            self.send_header("Cache-Control","private, no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            super().end_headers()
        def log_message(self,*args): pass
    print(f"Private review: http://127.0.0.1:{port}{base_path}/ (username: owner)",flush=True)
    ThreadingHTTPServer(("127.0.0.1",port),Handler).serve_forever()
