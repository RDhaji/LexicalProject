import sqlite3
import os

db_path = "data/staging/staging_claims.db"
os.makedirs(os.path.dirname(db_path), exist_ok=True)
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.executescript("""
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS staging_lexical_entries (
    source_id TEXT NOT NULL,
    lemma TEXT NOT NULL,
    pos TEXT NOT NULL,
    raw_payload JSON,
    source TEXT NOT NULL,
    PRIMARY KEY (source, source_id)
);

CREATE TABLE IF NOT EXISTS staging_inflections (
    lemma TEXT NOT NULL,
    form TEXT NOT NULL,
    pos TEXT NOT NULL,
    features TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staging_semantic_relations (
    synset_id TEXT NOT NULL,
    target_synset_id TEXT,
    relation_type TEXT NOT NULL,
    lemma TEXT,
    pos TEXT,
    definition TEXT,
    source TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_stg_lex_lemma ON staging_lexical_entries(lemma);
CREATE INDEX IF NOT EXISTS idx_stg_infl_lemma ON staging_inflections(lemma);
CREATE INDEX IF NOT EXISTS idx_stg_sem_synset ON staging_semantic_relations(synset_id);
""")

conn.commit()
conn.close()
print("PASS | Staging schema initialized with WAL mode.")
