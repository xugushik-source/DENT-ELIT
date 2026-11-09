"""Private durable task queue. Store DB on a persistent server volume, never in git."""
import json
import sqlite3
import time
import uuid


class Queue:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, key TEXT UNIQUE NOT NULL, kind TEXT NOT NULL,
            payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'READY',
            attempts INTEGER NOT NULL DEFAULT 0, due REAL NOT NULL DEFAULT 0,
            owner TEXT, lease REAL, result TEXT, error TEXT)''')

    def enqueue(self, key, kind, payload):
        if kind not in {'discover', 'verify', 'draft', 'send', 'reply', 'demo', 'notify'}:
            raise ValueError('Unsupported task')
        self.db.execute('INSERT OR IGNORE INTO jobs(id,key,kind,payload) VALUES(?,?,?,?)',
                        (str(uuid.uuid4()), key, kind, json.dumps(payload)))

    def claim(self, owner, seconds=300):
        now = time.time()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            # A send might have reached the provider before the worker died.
            self.db.execute("UPDATE jobs SET state='UNKNOWN',error='Lease expired during send; reconcile Gmail, never retry' WHERE state='RUNNING' AND lease<? AND kind='send'", (now,))
            self.db.execute("UPDATE jobs SET state='READY',owner=NULL,lease=NULL WHERE state='RUNNING' AND lease<? AND kind<>'send' AND attempts<5", (now,))
            self.db.execute("UPDATE jobs SET state='BLOCKED',error='Retry budget exhausted' WHERE state='RUNNING' AND lease<? AND attempts>=5", (now,))
            row = self.db.execute("SELECT * FROM jobs WHERE state='READY' AND due<=? ORDER BY due,rowid LIMIT 1", (now,)).fetchone()
            if row:
                self.db.execute("UPDATE jobs SET state='RUNNING',owner=?,lease=?,attempts=attempts+1 WHERE id=?", (owner, now+seconds, row['id']))
                row = dict(self.db.execute('SELECT * FROM jobs WHERE id=?', (row['id'],)).fetchone())
                row['payload'] = json.loads(row['payload'])
            self.db.execute('COMMIT')
            return row
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def finish(self, job, owner, result):
        self._settle(job, owner, 'DONE', result=result)

    def fail(self, job, owner, error, transient=False):
        state = 'UNKNOWN' if job['kind']=='send' else ('READY' if transient and job['attempts']<5 else 'BLOCKED')
        self._settle(job, owner, state, error=str(error)[:1000], due=time.time()+min(3600, 30*2**job['attempts']))

    def _settle(self, job, owner, state, result=None, error=None, due=0):
        changed = self.db.execute("UPDATE jobs SET state=?,result=?,error=?,due=?,owner=NULL,lease=NULL WHERE id=? AND owner=? AND state='RUNNING' AND lease>=?", (state,json.dumps(result),error,due,job['id'],owner,time.time())).rowcount
        if changed != 1:
            raise RuntimeError('Lost lease; do not repeat external side effects')

    def counts(self):
        return dict(self.db.execute('SELECT state,count(*) FROM jobs GROUP BY state'))


def run_once(queue, handlers, owner=None):
    """Handlers must use idempotent CRM RPCs; send must use approved Gmail connector."""
    owner = owner or str(uuid.uuid4())
    job = queue.claim(owner)
    if not job:
        return False
    try:
        handler = handlers.get(job['kind'])
        if handler is None:
            raise RuntimeError('Required authorized adapter is not installed')
        result = handler(job['payload'])
    except Exception as exc:
        queue.fail(job, owner, exc)
    else:
        # Never catch persistence failure and run the handler again.
        queue.finish(job, owner, result)
    return True
