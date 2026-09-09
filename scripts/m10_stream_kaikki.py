import json
import sqlite3
import time
import sys
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING_DB = ROOT / "data" / "staging" / "staging_claims.db"
KAIKKI_FILE = ROOT / "data" / "raw" / "kaikki.org-dictionary-English.jsonl"
KAIKKI_GZ = ROOT / "data" / "raw" / "kaikki.org-dictionary-English.jsonl.gz"

FIXTURE_LEMMAS = {"run", "fast", "happy", "go", "good", "bad", "bank"}

def stream_kaikki(fixture_only: bool = False):
    start = time.time()
    src_file = KAIKKI_FILE if KAIKKI_FILE.exists() else (KAIKKI_GZ if KAIKKI_GZ.exists() else None)
    if not src_file:
        print(f"FAIL: Source not found: {KAIKKI_FILE}")
        sys.exit(1)

    is_gz = str(src_file).endswith(".gz")
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_infl_lemma ON inflection_claims(lemma);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_infl_form ON inflection_claims(form);")

    open_fn = gzip.open if is_gz else open
    claim_batch = []
    form_batch = set()
    inserted_claims = 0

    with open_fn(src_file, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue

            word = entry.get("word")
            lang_code = entry.get("lang_code", "en")
            if not word or lang_code != "en":
                continue

            if fixture_only and word.lower() not in FIXTURE_LEMMAS:
                continue

            forms_list = entry.get("forms", [])
            pos = entry.get("pos", "")

            for f_item in forms_list:
                surface = f_item.get("form")
                if not surface:
                    continue

                tags = f_item.get("tags", [])
                claim_id = f"kaikki_{word}_{pos}_{surface}_{'_'.join(tags)}"
                form_id = f"form_{surface}"
                form_batch.add((form_id, surface, None))

                claim_batch.append((
                    claim_id,
                    "KAIKKI_EN",
                    "2025",
                    word,
                    word,
                    surface,
                    json.dumps(tags),
                    "ATTESTED",
                    "KAIKKI_WIKTIONARY"
                ))

                if len(claim_batch) >= 20000:
                    cur.executemany("""
                        INSERT OR IGNORE INTO inflection_claims 
                        (id, source_id, source_version, entry_identifier, lemma, form, tags_json, epistemic_class, provenance)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, claim_batch)
                    inserted_claims += len(claim_batch)
                    claim_batch = []

            if len(form_batch) >= 20000:
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

    cur.execute("SELECT COUNT(*) FROM inflection_claims;")
    total_claims = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM forms;")
    total_forms = cur.fetchone()[0]

    conn.close()
    elapsed = time.time() - start
    print(f"PASS: Ingested {inserted_claims} claims ({elapsed:.2f}s). Total claims: {total_claims}. Total forms: {total_forms}.")

if __name__ == "__main__":
    is_fixture = "--fixture" in sys.argv
    stream_kaikki(fixture_only=is_fixture)
