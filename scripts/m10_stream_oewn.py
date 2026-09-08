import os
import glob
import sqlite3
import time
import re

try:
    from yaml import CSafeLoader as Loader
except ImportError:
    from yaml import SafeLoader as Loader
import yaml

SYNSET_ID_RE = re.compile(r"^\d{8}-[a-z]$")

def ingest_oewn():
    start = time.time()
    db_path = "data/staging/staging_claims.db"
    yaml_dir = "data/raw/oewn_2025/src/yaml"
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    yaml_files = sorted(glob.glob(os.path.join(yaml_dir, "*.yaml")))
    total_files = len(yaml_files)
    print(f"INFO | Processing {total_files} OEWN files using {Loader.__name__}...")
    
    entry_batch = []
    sem_batch = []

    REL_KEYS = [
        "hypernym", "instance_hypernym", "hyponym", "instance_hyponym",
        "similar", "also", "meronym", "holonym", "antonym", "entails"
    ]
    
    for idx, yf in enumerate(yaml_files, 1):
        fname = os.path.basename(yf)
        t0 = time.time()
        with open(yf, "r", encoding="utf-8") as f:
            doc = yaml.load(f, Loader=Loader)
            if not isinstance(doc, dict):
                continue
                
            for k, val in doc.items():
                if not isinstance(val, dict):
                    continue
                    
                if SYNSET_ID_RE.match(k):
                    synset_id = k
                    pos = val.get("partOfSpeech", synset_id[-1])
                    defs = val.get("definition", [])
                    definition = defs[0] if isinstance(defs, list) and defs else (defs if isinstance(defs, str) else None)
                    
                    sem_batch.append((synset_id, None, "SYNSET_DEF", None, pos, definition, "OEWN_2025"))
                    
                    for rk in REL_KEYS:
                        targets = val.get(rk, [])
                        if isinstance(targets, list):
                            for tgt in targets:
                                if isinstance(tgt, str):
                                    sem_batch.append((synset_id, tgt, rk.upper(), None, pos, definition, "OEWN_2025"))
                        elif isinstance(targets, str):
                            sem_batch.append((synset_id, targets, rk.upper(), None, pos, definition, "OEWN_2025"))
                            
                    for mem in val.get("members", []):
                        if isinstance(mem, str):
                            sem_batch.append((synset_id, None, "MEMBER", mem, pos, None, "OEWN_2025"))
                else:
                    lemma = k
                    for pos, pdata in val.items():
                        source_id = f"oewn:{lemma}:{pos}"
                        entry_batch.append((source_id, lemma, pos, None, "OEWN_2025"))

        if len(sem_batch) >= 20000:
            cur.executemany("""
                INSERT INTO staging_semantic_relations 
                (synset_id, target_synset_id, relation_type, lemma, pos, definition, source) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, sem_batch)
            sem_batch.clear()
            
        if len(entry_batch) >= 20000:
            cur.executemany("""
                INSERT OR IGNORE INTO staging_lexical_entries 
                (source_id, lemma, pos, raw_payload, source) 
                VALUES (?, ?, ?, ?, ?)
            """, entry_batch)
            entry_batch.clear()

        print(f"[{idx}/{total_files}] Ingested {fname} ({time.time() - t0:.2f}s)")

    if sem_batch:
        cur.executemany("""
            INSERT INTO staging_semantic_relations 
            (synset_id, target_synset_id, relation_type, lemma, pos, definition, source) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sem_batch)
    if entry_batch:
        cur.executemany("""
            INSERT OR IGNORE INTO staging_lexical_entries 
            (source_id, lemma, pos, raw_payload, source) 
            VALUES (?, ?, ?, ?, ?)
        """, entry_batch)

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM staging_semantic_relations WHERE source = 'OEWN_2025';")
    sem_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM staging_lexical_entries WHERE source = 'OEWN_2025';")
    entry_count = cur.fetchone()[0]
    conn.close()
    
    print(f"PASS | OEWN 2025 Ingested: {entry_count} entries, {sem_count} semantic claims | Total Duration: {time.time() - start:.2f}s")

if __name__ == "__main__":
    ingest_oewn()
