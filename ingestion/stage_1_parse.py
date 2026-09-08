"""
Stage 1: Streaming Source Parsers to Staging Claims
Compliance: PRD.md Section 2, ADR-001, ADR-002, ADR-003, INGESTION_PIPELINE.md Stage 1
"""

import csv
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

STAGING_DIR = "data/staging"
STAGING_DB_PATH = os.path.join(STAGING_DIR, "claims.db")

def init_staging_db(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staging_claims (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            source_key TEXT NOT NULL,
            claim_type TEXT NOT NULL,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object_json TEXT NOT NULL,
            extracted_at TEXT NOT NULL
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_source ON staging_claims(source);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_subject ON staging_claims(subject);")
    conn.commit()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def parse_oewn(conn: sqlite3.Connection, path: str):
    if not os.path.exists(path):
        return
    print("  -> Parsing OEWN_2025...")
    cursor = conn.cursor()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    lexicon = data.get("lexicon", {})
    entries = lexicon.get("entries", [])
    synsets = lexicon.get("synsets", [])

    records = []
    for s in synsets:
        synset_id = s["id"]
        records.append((
            str(uuid.uuid4()), "OEWN_2025", synset_id, "SYNSET",
            synset_id, "DEFINED_AS", json.dumps({"definition": s.get("definition", ""), "pos": s.get("pos", "")}),
            now_iso()
        ))

    for e in entries:
        entry_id = e["id"]
        lemma = e["lemma"]
        pos = e["pos"]
        records.append((
            str(uuid.uuid4()), "OEWN_2025", entry_id, "LEXICAL_ENTRY",
            lemma, "HAS_POS", json.dumps({"pos": pos, "entry_id": entry_id}),
            now_iso()
        ))
        for sense in e.get("senses", []):
            records.append((
                str(uuid.uuid4()), "OEWN_2025", sense["id"], "SENSE_MEMBERSHIP",
                lemma, "MEMBER_OF_SYNSET", json.dumps({"synset_id": sense["synset"], "sense_id": sense["id"]}),
                now_iso()
            ))

    cursor.executemany("""
        INSERT INTO staging_claims (id, source, source_key, claim_type, subject, predicate, object_json, extracted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    print(f"     Materialized {len(records)} claims from OEWN_2025.")

def parse_kaikki(conn: sqlite3.Connection, path: str):
    if not os.path.exists(path):
        return
    print("  -> Parsing WIKTIONARY_KAIKKI_20260805 (Streaming)...")
    cursor = conn.cursor()
    records = []
    batch_size = 5000

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            word = item.get("word")
            pos = item.get("pos")
            if not word or not pos:
                continue

            claim_id = str(uuid.uuid4())
            payload = {
                "pos": pos,
                "lang_code": item.get("lang_code", "en"),
                "sounds": item.get("sounds", []),
                "senses": item.get("senses", [])
            }
            records.append((
                claim_id, "WIKTIONARY_KAIKKI_20260805", f"{word}:{pos}", "LEXICAL_RECORD",
                word, "ATTESTED_AS", json.dumps(payload), now_iso()
            ))

            if len(records) >= batch_size:
                cursor.executemany("""
                    INSERT INTO staging_claims (id, source, source_key, claim_type, subject, predicate, object_json, extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, records)
                conn.commit()
                records.clear()

    if records:
        cursor.executemany("""
            INSERT INTO staging_claims (id, source, source_key, claim_type, subject, predicate, object_json, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, records)
        conn.commit()
    print("     Finished streaming WIKTIONARY_KAIKKI claims.")

def parse_unimorph(conn: sqlite3.Connection, path: str):
    if not os.path.exists(path):
        return
    print("  -> Parsing UNIMORPH_ENG...")
    cursor = conn.cursor()
    records = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 3:
                continue
            lemma, surface, features = row[0].strip(), row[1].strip(), row[2].strip()
            claim_id = str(uuid.uuid4())
            payload = {"surface": surface, "features": features}
            records.append((
                claim_id, "UNIMORPH_ENG", f"{lemma}:{surface}:{features}", "INFLECTION_RECORD",
                lemma, "HAS_INFLECTION", json.dumps(payload), now_iso()
            ))

    cursor.executemany("""
        INSERT INTO staging_claims (id, source, source_key, claim_type, subject, predicate, object_json, extracted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    print(f"     Materialized {len(records)} claims from UNIMORPH_ENG.")

def parse_subtlex(conn: sqlite3.Connection, path: str):
    if not os.path.exists(path):
        return
    print("  -> Parsing SUBTLEX_US_R1...")
    cursor = conn.cursor()
    records = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            word = row.get("Word", "").strip()
            if not word:
                continue
            claim_id = str(uuid.uuid4())
            records.append((
                claim_id, "SUBTLEX_US_R1", word, "USAGE_FREQUENCY",
                word, "HAS_FREQUENCY", json.dumps(row), now_iso()
            ))

    cursor.executemany("""
        INSERT INTO staging_claims (id, source, source_key, claim_type, subject, predicate, object_json, extracted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    print(f"     Materialized {len(records)} claims from SUBTLEX_US_R1.")

def run_stage_1() -> bool:
    print("[STAGE 1] Initiating streaming claims extraction...")
    os.makedirs(STAGING_DIR, exist_ok=True)
    conn = sqlite3.connect(STAGING_DB_PATH)
    try:
        init_staging_db(conn)
        parse_oewn(conn, "data/sources/oewn_2025.json")
        parse_kaikki(conn, "data/sources/kaikki_english_20260805.jsonl")
        parse_unimorph(conn, "data/sources/unimorph_eng.tsv")
        parse_subtlex(conn, "data/sources/subtlex_us_r1.tsv")
        print("[SUCCESS] Stage 1 finished. Claims ledger built at data/staging/claims.db.")
        return True
    except Exception as e:
        print(f"[ERROR] Stage 1 failed: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if not run_stage_1():
        sys.exit(1)
