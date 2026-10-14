import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from factory.scaffold import scaffold


def now(): return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "factory.sqlite3"
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS clinics(id TEXT PRIMARY KEY, workspace TEXT NOT NULL DEFAULT 'order-profit', name TEXT NOT NULL,
              country TEXT NOT NULL, city TEXT NOT NULL, language TEXT NOT NULL, synthetic INTEGER NOT NULL,
              status TEXT NOT NULL, version INTEGER NOT NULL, revision INTEGER NOT NULL, config TEXT NOT NULL,
              current_job TEXT, approval TEXT, draft TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS config_versions(clinic_id TEXT NOT NULL REFERENCES clinics(id), revision INTEGER NOT NULL,
              config TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(clinic_id, revision));
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, clinic_id TEXT NOT NULL REFERENCES clinics(id), revision INTEGER NOT NULL,
              config TEXT NOT NULL, status TEXT NOT NULL, report TEXT, error TEXT, viewed_at TEXT, created_at TEXT NOT NULL, finished_at TEXT);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, clinic_id TEXT REFERENCES clinics(id),
              kind TEXT NOT NULL, actor TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1), paused INTEGER NOT NULL);
            INSERT OR IGNORE INTO settings VALUES(1,0);
            ''')

    def connect(self):
        db = sqlite3.connect(self.db, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @contextmanager
    def tx(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback(); raise
        finally: db.close()

    def event(self, db, clinic_id, kind, detail=None, actor="owner"):
        db.execute("INSERT INTO events(clinic_id,kind,actor,detail,created_at) VALUES(?,?,?,?,?)",
                   (clinic_id,kind,actor,json.dumps(detail or {},ensure_ascii=False),now()))

    @staticmethod
    def card(row):
        d = dict(row)
        for key in ("config","approval","draft"):
            d[key] = json.loads(d[key]) if d[key] else None
        d["synthetic"] = bool(d["synthetic"])
        return d

    def list(self):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM clinics ORDER BY created_at DESC").fetchall()
            return [{k:v for k,v in self.card(r).items() if k not in ("config","approval","draft")} for r in rows]

    def get(self, clinic_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM clinics WHERE id=?",(clinic_id,)).fetchone()
            if not row: raise ValueError("Карточка не найдена")
            d = self.card(row)
            job = db.execute("SELECT * FROM jobs WHERE id=?",(d["current_job"],)).fetchone()
            if job:
                d["job"] = dict(job);d["job"].pop("config")
                d["job"]["report"] = json.loads(job["report"]) if job["report"] else None
            else: d["job"] = None
            d["events"] = [dict(r) for r in db.execute("SELECT kind,actor,detail,created_at FROM events WHERE clinic_id=? ORDER BY id DESC",(clinic_id,))]
            for e in d["events"]: e["detail"] = json.loads(e["detail"])
            return d

    def create(self, name, country, city, language, commit, synthetic=False, config=None):
        if language not in ("ru","en","hy"): raise ValueError("Язык: ru, en или hy")
        if any(not isinstance(x,str) or not x.strip() or len(x)>200 for x in (name,country,city)): raise ValueError("Заполните название, страну и город")
        c = config or scaffold([language],commit)
        cid = c["clinicId"]
        c["synthetic"] = bool(synthetic)
        with self.tx() as db:
            db.execute("INSERT INTO clinics(id,name,country,city,language,synthetic,status,version,revision,config,created_at) VALUES(?,?,?,?,?,?,'DATA_REQUIRED',1,1,?,?)",
                       (cid,name.strip(),country.strip(),city.strip(),language,int(synthetic),json.dumps(c,ensure_ascii=False),now()))
            db.execute("INSERT INTO config_versions VALUES(?,?,?,?)",(cid,1,json.dumps(c,ensure_ascii=False),now()))
            self.event(db,cid,"CARD_CREATED",{"synthetic":synthetic})
        (self.root / "assets" / cid).mkdir(parents=True,exist_ok=True)
        return self.get(cid)

    def save(self, cid, expected_version, config):
        from jsonschema import Draft202012Validator, FormatChecker
        from factory.policy import ROOT
        schema = json.loads((ROOT / "schemas/clinic.schema.json").read_text())
        Draft202012Validator(schema,format_checker=FormatChecker()).validate(config)
        with self.tx() as db:
            r = db.execute("SELECT * FROM clinics WHERE id=?",(cid,)).fetchone()
            if not r or r["version"] != expected_version: raise ValueError("Карточка изменилась; обновите её перед сохранением")
            if config["clinicId"] != cid or bool(config["synthetic"]) != bool(r["synthetic"]): raise ValueError("Нельзя менять принадлежность или тестовый режим конфигурации")
            if config["deploymentMode"] != "demo" or config["languages"]["default"] != r["language"]: raise ValueError("Режим демо и язык должны совпадать с карточкой")
            from factory.policy import facts, APPROVED
            before=dict(facts(json.loads(r["config"])))
            recheck=[]
            for path,fact in facts(config):
                previous=before.get(path)
                if previous and previous["value"] != fact["value"] and previous["status"] in APPROVED and fact["status"] in APPROVED:
                    if all(previous[key]==fact[key] for key in ("sourceIds","checkedAt","reviewer")):
                        fact["status"]="SOURCED";recheck.append(path)
            revision = r["revision"] + 1
            config["revision"] = revision
            body = json.dumps(config,ensure_ascii=False)
            db.execute("UPDATE clinics SET config=?,revision=?,version=version+1,status='DATA_REQUIRED',current_job=NULL,approval=NULL,draft=NULL WHERE id=?",(body,revision,cid))
            db.execute("INSERT INTO config_versions VALUES(?,?,?,?)",(cid,revision,body,now()))
            self.event(db,cid,"CONFIG_SAVED",{"revision":revision,"approvalInvalidated":True,"requiresReverification":recheck})
        return self.get(cid)

    def queue(self, cid, expected_version):
        from factory.policy import validate
        c = self.get(cid)
        validate(c["config"],self.root/"assets"/cid)
        with self.tx() as db:
            r = db.execute("SELECT * FROM clinics WHERE id=?",(cid,)).fetchone()
            if r["version"] != expected_version: raise ValueError("Карточка изменилась; обновите её")
            active = db.execute("SELECT id FROM jobs WHERE clinic_id=? AND status IN ('QUEUED','RUNNING') AND revision=?",(cid,r["revision"])).fetchone()
            if active: return active["id"]
            if db.execute("SELECT paused FROM settings").fetchone()[0]: raise ValueError("Управляющий процесс остановлен")
            jid = str(uuid.uuid4())
            db.execute("INSERT INTO jobs(id,clinic_id,revision,config,status,created_at) VALUES(?,?,?,?,'QUEUED',?)",(jid,cid,r["revision"],r["config"],now()))
            db.execute("UPDATE clinics SET status='QUEUED',version=version+1,current_job=?,approval=NULL,draft=NULL WHERE id=?",(jid,cid))
            self.event(db,cid,"BUILD_QUEUED",{"jobId":jid,"revision":r["revision"]})
            return jid

    def recover(self):
        with self.tx() as db:
            for job in db.execute("SELECT * FROM jobs WHERE status='RUNNING'").fetchall():
                db.execute("UPDATE jobs SET status='QUEUED' WHERE id=?",(job["id"],))
                self.event(db,job["clinic_id"],"JOB_RECOVERED",{"jobId":job["id"]},"director")

    def claim(self):
        with self.tx() as db:
            if db.execute("SELECT paused FROM settings").fetchone()[0]: return None
            job = db.execute("SELECT * FROM jobs WHERE status='QUEUED' ORDER BY created_at LIMIT 1").fetchone()
            if not job: return None
            db.execute("UPDATE jobs SET status='RUNNING' WHERE id=?",(job["id"],))
            db.execute("UPDATE clinics SET status='BUILDING',version=version+1 WHERE id=? AND revision=? AND current_job=?",(job["clinic_id"],job["revision"],job["id"]))
            self.event(db,job["clinic_id"],"BUILD_STARTED",{"jobId":job["id"]},"director")
            return dict(job)

    def finish(self, job, report=None, error=None):
        with self.tx() as db:
            c = db.execute("SELECT revision,current_job FROM clinics WHERE id=?",(job["clinic_id"],)).fetchone()
            stale = c["revision"] != job["revision"] or c["current_job"] != job["id"]
            status = "SUPERSEDED" if stale else ("FAILED" if error else "DONE")
            db.execute("UPDATE jobs SET status=?,report=?,error=?,finished_at=? WHERE id=?",(status,json.dumps(report,ensure_ascii=False) if report else None,error,now(),job["id"]))
            if not stale:
                db.execute("UPDATE clinics SET status=?,version=version+1 WHERE id=?",("BUILD_FAILED" if error else "DEMO_READY",job["clinic_id"]))
            self.event(db,job["clinic_id"],"BUILD_"+status,{"jobId":job["id"],"error":error,"buildId":report["buildId"] if report else None},"director")

    def pause(self, paused):
        with self.tx() as db:
            db.execute("UPDATE settings SET paused=?",(int(paused),))
            self.event(db,None,"DIRECTOR_PAUSED" if paused else "DIRECTOR_RESUMED")

    def settings(self):
        with self.connect() as db: return {"paused":bool(db.execute("SELECT paused FROM settings").fetchone()[0]),"mode":"DRY_RUN","mailConnected":False,"publicAccess":False}
