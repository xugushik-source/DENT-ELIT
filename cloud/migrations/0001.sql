CREATE TABLE clinics(id TEXT PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL, city TEXT NOT NULL, language TEXT NOT NULL, synthetic INTEGER NOT NULL,
 status TEXT NOT NULL, version INTEGER NOT NULL, revision INTEGER NOT NULL, config TEXT NOT NULL, current_job TEXT, approval TEXT, draft TEXT, nonce TEXT, created_at TEXT NOT NULL);
CREATE TABLE config_versions(clinic_id TEXT NOT NULL REFERENCES clinics(id), revision INTEGER NOT NULL, config TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(clinic_id,revision));
CREATE TABLE jobs(id TEXT PRIMARY KEY, clinic_id TEXT NOT NULL REFERENCES clinics(id), revision INTEGER NOT NULL, config TEXT NOT NULL, status TEXT NOT NULL,
 report TEXT, error TEXT, lease TEXT, viewed_at TEXT, created_at TEXT NOT NULL, finished_at TEXT);
CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,clinic_id TEXT,kind TEXT NOT NULL,actor TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE INDEX events_clinic ON events(clinic_id,id);
CREATE TABLE settings(id INTEGER PRIMARY KEY CHECK(id=1),paused INTEGER NOT NULL,stored_bytes INTEGER NOT NULL DEFAULT 0);
INSERT INTO settings VALUES(1,0,0);
