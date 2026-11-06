"""Persistent sales queue. Network transport is separate; ambiguous sends never retry."""
import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from office.store import now


def address(value):
    result = parseaddr(value)[1].strip().lower()
    if not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', result) or '\r' in value or '\n' in value:
        raise ValueError('Укажите один корректный email')
    return result


def digest(row):
    return hashlib.sha256(json.dumps([row[k] for k in ('lead_id','recipient','subject','body')], ensure_ascii=False).encode()).hexdigest()


class Sales:
    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS sales_leads(id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
              source TEXT NOT NULL, status TEXT NOT NULL, next_action TEXT NOT NULL, blocked INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sales_messages(provider_id TEXT PRIMARY KEY, lead_id TEXT NOT NULL REFERENCES sales_leads(id),
              thread_id TEXT NOT NULL, direction TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, sent_at TEXT NOT NULL, source TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sales_outbox(id TEXT PRIMARY KEY, lead_id TEXT NOT NULL REFERENCES sales_leads(id),
              recipient TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL, approved_hash TEXT,
              approved_at TEXT, provider_id TEXT, error TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sales_audit(id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT, kind TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sales_sync(id INTEGER PRIMARY KEY CHECK(id=1), checked_at TEXT, error TEXT);
            INSERT OR IGNORE INTO sales_sync(id) VALUES(1);
            ''')

    def audit(self, db, lid, kind, detail):
        db.execute('INSERT INTO sales_audit(lead_id,kind,detail,created_at) VALUES(?,?,?,?)', (lid, kind, json.dumps(detail, ensure_ascii=False), now()))

    def lead(self, name, email, source):
        email = address(email)
        if not all(isinstance(v,str) and v.strip() for v in (name,source)): raise ValueError('Нужны название и источник контакта')
        with self.store.tx() as db:
            old = db.execute('SELECT id FROM sales_leads WHERE email=?',(email,)).fetchone()
            if old: return old['id']
            lid=str(uuid.uuid4())
            db.execute('INSERT INTO sales_leads VALUES(?,?,?,?,?,?,0,?)',(lid,name[:200],email,source[:2000],'NEW','Подготовить персональное предложение',now()))
            self.audit(db,lid,'LEAD_CREATED',{'source':source})
            return lid

    def snapshot(self):
        with self.store.connect() as db:
            return {'leads':[dict(r) for r in db.execute('SELECT * FROM sales_leads ORDER BY updated_at DESC')],
                    'messages':[dict(r) for r in db.execute('SELECT * FROM sales_messages ORDER BY sent_at DESC')],
                    'outbox':[dict(r) for r in db.execute('SELECT * FROM sales_outbox ORDER BY created_at DESC')],
                    'audit':[dict(r) for r in db.execute('SELECT * FROM sales_audit ORDER BY id DESC LIMIT 100')],
                    'sync':dict(db.execute('SELECT * FROM sales_sync').fetchone())}

    def task(self,lid,next_action,blocked=False):
        if not isinstance(next_action,str) or not next_action.strip(): raise ValueError('Укажите следующее действие')
        with self.store.tx() as db:
            if db.execute('UPDATE sales_leads SET next_action=?,blocked=?,updated_at=? WHERE id=?',(next_action[:2000],int(blocked),now(),lid)).rowcount!=1: raise ValueError('Компания не найдена')
            if blocked: db.execute("UPDATE sales_outbox SET status='CANCELLED' WHERE lead_id=? AND status IN ('DRAFT','APPROVED')",(lid,))
            self.audit(db,lid,'TASK_UPDATED',{'next_action':next_action,'blocked':bool(blocked)})

    def draft(self,lid,subject,body):
        if not isinstance(subject,str) or not subject.strip() or '\n' in subject or '\r' in subject or len(subject)>998: raise ValueError('Укажите тему без переносов строки')
        if not isinstance(body,str) or not body.strip() or len(body)>50000: raise ValueError('Укажите текст письма')
        with self.store.tx() as db:
            lead=db.execute('SELECT * FROM sales_leads WHERE id=?',(lid,)).fetchone()
            if not lead or lead['blocked']: raise ValueError('Компания отсутствует или контакт остановлен')
            if db.execute("SELECT id FROM sales_outbox WHERE lead_id=? AND status IN ('DRAFT','APPROVED','SENDING','UNKNOWN')",(lid,)).fetchone(): raise ValueError('Сначала завершите или отмените предыдущее письмо')
            if db.execute("SELECT id FROM sales_outbox WHERE lead_id=? AND subject=? AND body=? AND status='SENT'",(lid,subject.strip(),body.strip())).fetchone(): raise ValueError('Такое письмо уже отправлено')
            oid=str(uuid.uuid4())
            db.execute("INSERT INTO sales_outbox(id,lead_id,recipient,subject,body,status,created_at) VALUES(?,?,?,?,?,'DRAFT',?)",(oid,lid,lead['email'],subject.strip(),body.strip(),now()))
            self.audit(db,lid,'DRAFT_CREATED',{'outbox_id':oid})
            return oid

    def approve(self,oid):
        with self.store.tx() as db:
            row=db.execute("SELECT * FROM sales_outbox WHERE id=? AND status='DRAFT'",(oid,)).fetchone()
            if not row: raise ValueError('Нет черновика для утверждения')
            if db.execute('SELECT blocked FROM sales_leads WHERE id=?',(row['lead_id'],)).fetchone()[0]: raise ValueError('Контакт остановлен')
            db.execute("UPDATE sales_outbox SET status='APPROVED',approved_hash=?,approved_at=? WHERE id=?",(digest(row),now(),oid))
            self.audit(db,row['lead_id'],'CONTENT_APPROVED',{'outbox_id':oid,'hash':digest(row)})

    def cancel(self,oid):
        with self.store.tx() as db:
            row=db.execute('SELECT * FROM sales_outbox WHERE id=?',(oid,)).fetchone()
            if not row or row['status'] not in ('DRAFT','APPROVED'): raise ValueError('Это письмо нельзя отменить')
            db.execute("UPDATE sales_outbox SET status='CANCELLED' WHERE id=?",(oid,))
            self.audit(db,row['lead_id'],'CANCELLED',{'outbox_id':oid})

    def send(self,oid,transport,enabled=False):
        if not enabled: raise ValueError('Реальная отправка отключена владельцем')
        with self.store.tx() as db:
            row=db.execute("SELECT * FROM sales_outbox WHERE id=? AND status='APPROVED'",(oid,)).fetchone()
            if not row or row['approved_hash']!=digest(row): raise ValueError('Нет утверждения этой версии письма')
            lead=db.execute('SELECT * FROM sales_leads WHERE id=?',(row['lead_id'],)).fetchone()
            if lead['blocked'] or lead['email']!=row['recipient']: raise ValueError('Получатель изменён или контакт остановлен')
            cutoff=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
            if db.execute("SELECT COUNT(*) FROM sales_audit WHERE kind='SEND_STARTED' AND created_at>=?",(cutoff,)).fetchone()[0]>=5: raise ValueError('Лимит пилота: 5 попыток отправки за 24 часа')
            db.execute("UPDATE sales_outbox SET status='SENDING' WHERE id=?",(oid,))
            self.audit(db,row['lead_id'],'SEND_STARTED',{'outbox_id':oid}); item=dict(row)
        try:
            result=transport.send(item)
            if not result.get('id'): raise ValueError('Нет идентификатора письма')
        except Exception:
            with self.store.tx() as db:
                db.execute("UPDATE sales_outbox SET status='UNKNOWN',error=? WHERE id=?",('Результат неизвестен. Сверьте отправленные в Gmail; повтор заблокирован.',oid))
                self.audit(db,item['lead_id'],'SEND_UNKNOWN',{'outbox_id':oid})
            return 'UNKNOWN'
        with self.store.tx() as db:
            db.execute("UPDATE sales_outbox SET status='SENT',provider_id=? WHERE id=?",(result['id'],oid))
            db.execute("UPDATE sales_leads SET status='WAITING_REPLY',next_action='Ожидается ответ',updated_at=? WHERE id=?",(now(),item['lead_id']))
            db.execute('INSERT OR IGNORE INTO sales_messages VALUES(?,?,?,?,?,?,?,?)',(result['id'],item['lead_id'],result.get('threadId',''),'OUT',item['subject'],item['body'],now(),'gmail-api'))
            self.audit(db,item['lead_id'],'SENT',{'outbox_id':oid,'provider_id':result['id']})
        return 'SENT'

    def recover(self):
        with self.store.tx() as db: db.execute("UPDATE sales_outbox SET status='UNKNOWN',error='Процесс прерван. Сверьте Gmail перед повтором.' WHERE status='SENDING'")

    def import_messages(self,lid,messages):
        with self.store.tx() as db:
            if not db.execute('SELECT id FROM sales_leads WHERE id=?',(lid,)).fetchone(): raise ValueError('Компания не найдена')
            added=0
            for m in messages:
                if m['direction'] not in ('IN','OUT','BOUNCE'): raise ValueError('Неизвестное направление')
                ts=datetime.fromisoformat(m['sent_at'].replace('Z','+00:00'))
                if ts.tzinfo is None: raise ValueError('Дата должна включать часовой пояс')
                ts=ts.astimezone(timezone.utc).isoformat()
                n=db.execute('INSERT OR IGNORE INTO sales_messages VALUES(?,?,?,?,?,?,?,?)',(m['id'],lid,m['thread_id'],m['direction'],m['subject'],m['body'],ts,m['source'])).rowcount
                if not n: continue
                added+=1
                if m['direction'] in ('IN','BOUNCE'):
                    db.execute("UPDATE sales_outbox SET status='CANCELLED' WHERE lead_id=? AND status IN ('DRAFT','APPROVED')",(lid,))
                    db.execute('UPDATE sales_leads SET blocked=1 WHERE id=?',(lid,))
                latest=db.execute('SELECT direction FROM sales_messages WHERE lead_id=? ORDER BY sent_at DESC LIMIT 1',(lid,)).fetchone()[0]
                status={'IN':'REPLY_REVIEW','OUT':'WAITING_REPLY','BOUNCE':'DELIVERY_REVIEW'}[latest]
                task={'IN':'Прочитать ответ и выбрать следующий шаг','OUT':'Проверить результат переписки','BOUNCE':'Проверить возврат; отправку не повторять'}[latest]
                db.execute('UPDATE sales_leads SET status=?,next_action=?,updated_at=? WHERE id=?',(status,task,now(),lid))
                self.audit(db,lid,'MAIL_IMPORTED',{'provider_id':m['id'],'direction':m['direction'],'sent_at':ts})
            return added

    def sync(self,transport):
        try:
            for lead in self.snapshot()['leads']: self.import_messages(lead['id'],transport.messages(lead['email']))
        except Exception:
            with self.store.tx() as db: db.execute("UPDATE sales_sync SET error='Синхронизация не завершена; проверьте Gmail' WHERE id=1")
            raise ValueError('Синхронизация Gmail не завершена') from None
        with self.store.tx() as db: db.execute('UPDATE sales_sync SET checked_at=?,error=NULL WHERE id=1',(now(),))
