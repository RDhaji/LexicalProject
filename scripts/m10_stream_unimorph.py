import sqlite3
import time
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING_DB = ROOT / "data" / "staging" / "staging_claims.db"
UNIMORPH_FILE = ROOT / "data" / "raw" / "eng.unimorph"
if not UNIMORPH_FILE.exists():
    UNIMORPH_FILE = ROOT / "data" / "raw" / "unimorph_eng.tsv"

FIXTURE_LEMMAS = {"run", "fast", "happy", "go", "good", "bad", "bank"}

def stream_unimorph(fixture_only: bool = False):
    start = time.time()
    if not UNIMORPH_FILE.exists():
        print(f"FAIL: UniMorph data file not found: {UNIMORPH_FILE}")
        sys.exit(1)

    conn = sqlite3.connect(STAGING_DB)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inflection_claims (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            source_version TEXT NOT NULL,
            entry_identifier TEXT NOT NULL,
            lemma TEXT NOT NULL,
            form TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            epistemic_class TEXT NOT NULL CHECK(epistemic_class IN ('EXPLICIT', 'GENERATED', 'ATTESTED', 'INFERRED', 'UNCERTAIN')),
            provenance TEXT NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS forms (
            form_id TEXT PRIMARY KEY,
            surface_form TEXT NOT NULL UNIQUE,
            phonetic_rep TEXT
        );
    """)

    claim_batch = []
    form_batch = set()
    inserted_claims = 0

    with open(UNIMORPH_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue

            lemma, surface, features = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if not lemma or not surface:
                continue

            if fixture_only and lemma.lower() not in FIXTURE_LEMMAS:
                continue

            tags = features.split(";")
            claim_id = f"unimorph_{lemma}_{surface}_{features}"
            form_id = f"form_{surface}"

            form_batch.add((form_id, surface, None))
            claim_batch.append((
                claim_id,
                "UNIMORPH_ENG",
                "2026",
                lemma,
                lemma,
                surface,
                json.dumps(tags),
                "ATTESTED",
                "UNIMORPH"
            ))

            if len(claim_batch) >= 25000:
                cur.executemany("""
                    INSERT OR IGNORE INTO inflection_claims 
                    (id, source_id, source_version, entry_identifier, lemma, form, tags_json, epistemic_class, provenance)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, claim_batch)
                inserted_claims += len(claim_batch)
                claim_batch = []

            if len(form_batch) >= 25000:
                cur.executemany("""
                    INSERT OR IGNORE INTO forms (form_id, surface_form, phonetic_rep)
                    VALUES (?, ?, ?);
                """, list(form_batch))
                form_batch.clear()

    if claim_batch:
        cur.executemany("""
            INSERT OR IGNORE INTO inflection_claims 
            (id, source_id, source_version, entry_identifier, lemma, form, tags_json, epistemic_class, provenance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, claim_batch)
        inserted_claims += len(claim_batch)

    if form_batch:
        cur.executemany("""
            INSERT OR IGNORE INTO forms (form_id, surface_form, phonetic_rep)
            VALUES (?, ?, ?);
        """, list(form_batch))

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM inflection_claims WHERE source_id = 'UNIMORPH_ENG';")
    unimorph_claims = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM forms;")
    total_forms = cur.fetchone()[0]

    conn.close()
    elapsed = time.time() - start
    print(f"PASS: Ingested {inserted_claims} UniMorph claims ({elapsed:.2f}s). Total UniMorph claims: {unimorph_claims}. Total forms: {total_forms}.")

if __name__ == "__main__":
    is_fixture = "--fixture" in sys.argv
    stream_unimorph(fixture_only=is_fixture)
