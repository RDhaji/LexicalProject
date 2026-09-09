import os
import glob
import sqlite3
import time
import re
import sys
from pathlib import Path

try:
    from yaml import CSafeLoader as Loader
except ImportError:
    from yaml import SafeLoader as Loader
import yaml

SYNSET_ID_RE = re.compile(r"^\d{8}-[a-z]$")
FIXTURE_LEMMAS = {"run", "fast", "happy", "go", "good", "bad", "bank"}

REL_KEYS = [
    "hypernym", "instance_hypernym", "hyponym", "instance_hyponym",
    "similar", "also", "meronym", "holonym", "antonym", "entails"
]

def materialize_edges(fixture_only=False):
    t0 = time.time()
    db_path = "data/staging/staging_claims.db"
    yaml_dir = "data/raw/oewn_2025/src/yaml"
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS semantic_relations (
            id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            source TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            confidence REAL NOT NULL
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sr_sub ON semantic_relations(subject_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sr_obj ON semantic_relations(object_id);")

    allowed_synsets = None
    if fixture_only:
        cur.execute("SELECT id, members FROM synsets;")
        allowed_synsets = set()
        for s_id, mems in cur.fetchall():
            m_set = (mems or "").lower().replace(",", " ").replace(";", " ").split()
            if any(fl in m_set for fl in FIXTURE_LEMMAS):
                allowed_synsets.add(s_id)
        print(f"INFO: Fixture mode active. Matched {len(allowed_synsets)} synsets.")

    yaml_files = sorted(glob.glob(os.path.join(yaml_dir, "*.yaml")))
    batch = []
    total_inserted = 0

    for yf in yaml_files:
        with open(yf, "r", encoding="utf-8") as f:
            doc = yaml.load(f, Loader=Loader)
            if not isinstance(doc, dict):
                continue
            
            for k, val in doc.items():
                if not isinstance(val, dict) or not SYNSET_ID_RE.match(k):
                    continue
                
                synset_id = k
                if allowed_synsets is not None and synset_id not in allowed_synsets:
                    continue

                for rk in REL_KEYS:
                    targets = val.get(rk, [])
                    if isinstance(targets, list):
                        for tgt in targets:
                            if isinstance(tgt, str) and SYNSET_ID_RE.match(tgt):
                                rel_type = rk.upper()
                                edge_id = f"oewn_{synset_id}_{rel_type}_{tgt}"
                                batch.append((edge_id, synset_id, rel_type, tgt, "OEWN_2025", "EXPLICIT", 1.0))
                                
                                if len(batch) >= 20000:
                                    cur.executemany("""
                                        INSERT OR IGNORE INTO semantic_relations
                                        (id, subject_id, relation_type, object_id, source, evidence_type, confidence)
                                        VALUES (?, ?, ?, ?, ?, ?, ?);
                                    """, batch)
                                    total_inserted += len(batch)
                                    batch = []

    if batch:
        cur.executemany("""
            INSERT OR IGNORE INTO semantic_relations
            (id, subject_id, relation_type, object_id, source, evidence_type, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, batch)
        total_inserted += len(batch)

    conn.commit()

    # Integrity verification
    cur.execute("""
        SELECT COUNT(*) FROM semantic_relations sr
        LEFT JOIN synsets s1 ON sr.subject_id = s1.id
        LEFT JOIN synsets s2 ON sr.object_id = s2.id
        WHERE s1.id IS NULL OR s2.id IS NULL;
    """)
    dangling = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM semantic_relations;")
    total_in_db = cur.fetchone()[0]

    conn.close()
    elapsed = time.time() - t0
    print(f"PASS: Materialized {total_inserted} edges into staging_claims.db ({elapsed:.2f}s). Total: {total_in_db}. Dangling: {dangling}")

    if dangling > 0:
        print(f"FAIL: Invariant 8 violation: {dangling} dangling semantic edges found.")
        sys.exit(1)

if __name__ == "__main__":
    is_fixture = "--fixture" in sys.argv
    materialize_edges(fixture_only=is_fixture)
