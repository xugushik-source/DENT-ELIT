import base64
import hmac
import json
import mimetypes
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote

from factory.policy import ROOT, validate
from office.store import Store
from office.workflow import Director


def server(data, port, password, actor="owner"):
    if len(password) < 16: raise ValueError("Пароль кабинета должен содержать минимум 16 символов")
    if data.resolve().is_relative_to(ROOT): raise ValueError("База и материалы должны находиться вне публичного репозитория")
    store = Store(data)
    # Only one Director may recover/execute this durable local queue.
    lock=(store.root/"office.lock").open("a+b")
    try:
        if __import__('os').name == "nt":
            import msvcrt
            lock.seek(0);lock.write(b"0");lock.flush();lock.seek(0)
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        lock.close();raise ValueError("Эта база уже обслуживается другим управляющим процессом")
    origin = f"http://127.0.0.1:{port}"
    director = Director(store,origin,actor)
    expected = "Basic " + base64.b64encode(("owner:"+password).encode()).decode()
    csrf = secrets.token_urlsafe(32)
    web = ROOT/"office/web"

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup();self.connection.settimeout(15)
        def log_message(self,*args): pass
        def response_headers(self,code,mime,length=None):
            self.send_response(code)
            self.send_header("Content-Type",mime)
            self.send_header("Cache-Control","private, no-store")
            self.send_header("X-Robots-Tag","noindex, nofollow, noarchive")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Referrer-Policy","no-referrer")
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; frame-ancestors 'self'; form-action 'none'")
            if length is not None: self.send_header("Content-Length",str(length))
            self.end_headers()
        def json(self,data,code=200):
            blob=json.dumps(data,ensure_ascii=False).encode();self.response_headers(code,"application/json; charset=utf-8",len(blob));self.wfile.write(blob)
        def auth(self):
            if not hmac.compare_digest(self.headers.get("Authorization",""),expected):
                self.send_response(401);self.send_header("WWW-Authenticate",'Basic realm="Order & Profit owner"');self.send_header("Cache-Control","no-store");self.end_headers();return False
            return True
        def file(self,path):
            if path.is_symlink() or not path.is_file(): return self.json({"error":"Не найдено"},404)
            data=path.read_bytes();self.response_headers(200,mimetypes.guess_type(path.name)[0] or "application/octet-stream",len(data));self.wfile.write(data)
        def do_GET(self):
            if not self.auth(): return
            path=unquote(urlsplit(self.path).path)
            try:
                if path=="/api/bootstrap": return self.json({"csrf":csrf,"settings":store.settings(),"clinics":store.list()})
                if path=="/api/clinics": return self.json(store.list())
                if path.startswith("/api/clinics/"): return self.json(store.get(path.split("/")[3]))
                if path.startswith("/demo/"):
                    parts=path.split("/");jid=parts[2]
                    with store.connect() as db:
                        job=db.execute("SELECT * FROM jobs WHERE id=?",(jid,)).fetchone()
                    if not job or not job["report"] or job["status"] not in ("DONE","SUPERSEDED"): return self.json({"error":"Демо не готово"},404)
                    report=json.loads(job["report"])
                    root=store.root/"builds"/job["clinic_id"]/report["buildId"]/"site"
                    relative="/".join(parts[3:]) or "index.html"
                    file=(root/relative).resolve()
                    if not file.is_relative_to(root.resolve()): return self.json({"error":"Недопустимый путь"},400)
                    if file.is_dir(): file=file/"index.html"
                    if not file.is_file(): file=root/"404.html"
                    return self.file(file)
                if path in ("/","/app.js","/style.css"):
                    return self.file(web/("index.html" if path=="/" else path[1:]))
                return self.json({"error":"Не найдено"},404)
            except (ValueError,KeyError,TypeError) as e: self.json({"error":str(e)},400)
        def do_POST(self):
            if not self.auth(): return
            if self.headers.get("X-CSRF-Token") != csrf or self.headers.get("Origin",origin) != origin:
                return self.json({"error":"Запрос не подтверждён кабинетом"},403)
            if self.headers.get("Content-Type","").split(";")[0] != "application/json": return self.json({"error":"Требуется JSON"},415)
            try:
                length=int(self.headers.get("Content-Length","0"))
                if not 0<length<=2000000: return self.json({"error":"Недопустимый размер запроса"},413)
                body=json.loads(self.rfile.read(length));path=urlsplit(self.path).path
                if path=="/api/director":
                    if not isinstance(body.get("paused"),bool): raise ValueError("paused должен быть логическим значением")
                    store.pause(body["paused"]);return self.json(store.settings())
                if path=="/api/sample":
                    from office.sample import create_sample
                    return self.json(create_sample(store),201)
                if path=="/api/clinics":
                    import subprocess
                    commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
                    return self.json(store.create(body["name"],body["country"],body["city"],body.get("language","ru"),commit),201)
                parts=path.strip("/").split("/")
                if len(parts)!=4 or parts[:2]!=["api","clinics"]: return self.json({"error":"Отправка и публикация не реализованы; маршрут отсутствует"},404)
                cid,action=parts[2:]
                version=body.get("version")
                if action=="config": return self.json(store.save(cid,version,body["config"]))
                if action=="validate":
                    c=store.get(cid);pending,used=validate(c["config"],store.root/"assets"/cid)
                    return self.json({"valid":True,"pending":pending,"usedAssets":sorted(used)})
                if action=="build": return self.json({"jobId":store.queue(cid,version)},202)
                if action=="viewed": director.review(cid,version);return self.json(store.get(cid))
                if action=="approve": return self.json(director.approve(cid,version,body.get("pendingPaths",[])))
                if action=="revise": return self.json(director.revise(cid,version,body.get("comment","")))
                if action=="draft": return self.json(director.draft(cid,version))
                return self.json({"error":"Неизвестное действие"},404)
            except Exception as error:
                from jsonschema.exceptions import ValidationError
                if isinstance(error,(ValueError,KeyError,TypeError,ValidationError)):
                    return self.json({"error":str(error)[:2500]},400)
                self.json({"error":"Внутренняя ошибка. Задание и данные сохранены; проверьте локальный процесс."},500)

    class OwnerServer(ThreadingHTTPServer):
        def server_close(self):
            if hasattr(self,"director"):
                self.director.stop.set();self.worker.join(timeout=30)
            super().server_close();lock.close()
    try: http=OwnerServer(("127.0.0.1",port),Handler)
    except Exception: lock.close();raise
    thread=threading.Thread(target=director.run,daemon=True);thread.start()
    http.store,http.director,http.worker=store,director,thread
    return http
