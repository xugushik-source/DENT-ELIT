import importlib.util
import json
import threading
from dataclasses import asdict
from pathlib import Path

from factory.policy import ROOT, validate, value
from factory.report import check, manifest
from factory.crm import approve
from office.store import now

spec = importlib.util.spec_from_file_location("factory_cli",ROOT/"factory.py")
engine = importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)


class Director:
    def __init__(self, store, origin, actor="owner"):
        self.store,self.origin,self.actor = store,origin,actor
        self.stop = threading.Event()

    def step(self):
        job = self.store.claim()
        if not job: return False
        try:
            folder = self.store.root/"jobs"/job["id"]
            folder.mkdir(parents=True,exist_ok=True)
            config = folder/"clinic.json";config.write_text(job["config"],encoding="utf-8")
            report = engine.build(config,self.store.root/"assets"/job["clinic_id"],self.store.root/"builds",self.origin,"/demo/"+job["id"])
            self.store.finish(job,report)
        except Exception as error:
            self.store.finish(job,error=str(error)[:2000])
        return True

    def run(self):
        self.store.recover()
        while not self.stop.is_set():
            if not self.step(): self.stop.wait(.25)

    def tested(self, cid):
        c = self.store.get(cid)
        job = c["job"]
        if not job or job["status"] != "DONE" or job["revision"] != c["revision"]: raise ValueError("Нужна завершённая сборка текущей версии")
        r = job["report"]
        folder = self.store.root/"builds"/cid/r["buildId"]
        validate(c["config"],self.store.root/"assets"/cid)
        if manifest(folder/"site") != r["files"]: raise ValueError("Файлы демо изменились после тестов")
        check(folder/"site",r["basePath"],r["origin"])
        return c,job,r,folder

    def review(self,cid,version):
        c,job,r,folder = self.tested(cid)
        with self.store.tx() as db:
            row = db.execute("SELECT version,current_job FROM clinics WHERE id=?",(cid,)).fetchone()
            if row["version"] != version or row["current_job"] != job["id"]: raise ValueError("Демо изменилось; обновите карточку")
            db.execute("UPDATE jobs SET viewed_at=? WHERE id=?",(now(),job["id"]))
            self.store.event(db,cid,"OWNER_REVIEW_RECORDED",{"buildId":r["buildId"],"synthetic":c["synthetic"]},self.actor)

    def approve(self,cid,version,pending_paths):
        c,job,r,folder = self.tested(cid)
        if not job["viewed_at"]: raise ValueError("Сначала откройте демо и отметьте, что просмотрели его")
        approval = asdict(approve(r,self.actor,pending_paths))
        approval["configRevision"] = c["revision"]
        approval["simulation"] = c["synthetic"]
        with self.store.tx() as db:
            row = db.execute("SELECT version,current_job FROM clinics WHERE id=?",(cid,)).fetchone()
            if row["version"] != version or row["current_job"] != job["id"]: raise ValueError("Версия изменилась; утверждение отклонено")
            db.execute("UPDATE clinics SET status='OWNER_APPROVED',approval=?,draft=NULL,version=version+1 WHERE id=?",(json.dumps(approval),cid))
            self.store.event(db,cid,"OWNER_APPROVED",approval,self.actor)
        return self.store.get(cid)

    def revise(self,cid,version,comment):
        if not isinstance(comment,str) or not comment.strip() or len(comment)>4000: raise ValueError("Укажите замечания")
        with self.store.tx() as db:
            result = db.execute("UPDATE clinics SET status='REVISION_REQUESTED',approval=NULL,draft=NULL,version=version+1 WHERE id=? AND version=?",(cid,version))
            if result.rowcount != 1: raise ValueError("Карточка изменилась")
            self.store.event(db,cid,"REVISION_REQUESTED",{"comment":comment.strip()},self.actor)
        return self.store.get(cid)

    def draft(self,cid,version):
        c,job,r,folder = self.tested(cid)
        a = c["approval"]
        if c["status"] not in ("OWNER_APPROVED","DRAFT_READY") or not a or a["build_id"] != r["buildId"] or a["configRevision"] != c["revision"]:
            raise ValueError("Сначала утвердите текущую версию демо")
        from office.proposal import proposal
        draft = proposal(c,r)
        with self.store.tx() as db:
            row = db.execute("SELECT version,approval FROM clinics WHERE id=?",(cid,)).fetchone()
            if row["version"] != version or row["approval"] != json.dumps(a): raise ValueError("Утверждение изменилось; черновик не создан")
            db.execute("UPDATE clinics SET status='DRAFT_READY',draft=?,version=version+1 WHERE id=?",(json.dumps(draft,ensure_ascii=False),cid))
            self.store.event(db,cid,"PROPOSAL_DRAFTED",{"buildId":r["buildId"],"delivery":"NOT_SENT","synthetic":c["synthetic"]},self.actor)
        return self.store.get(cid)
