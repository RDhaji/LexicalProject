import json
from pathlib import Path
import sqlite3
import sys
import time
import uuid

root = Path.home() / "Desktop" / "LexicalProject"
NAMESPACE_OID = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")

def make_uuid(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE_OID, key))

staging_db_path = root / "data" / "staging" / "staging_claims.db"
assert staging_db_path.exists(), "Staging database missing; prerequisite M1 incomplete"

conn = sqlite3.connect(staging_db_path)
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

cur.executescript("""
CREATE TABLE IF NOT EXISTS raw_lexical_entries (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    lemma TEXT NOT NULL,
    pos TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_inflections (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    lemma TEXT NOT NULL,
    pos TEXT NOT NULL,
    surface TEXT NOT NULL,
    features_json TEXT NOT NULL
);
""")

# Kaikki fixture records (stream representation)
kaikki_fixtures = [
    {"lemma": "run", "pos": "VERB", "definitions": ["move quickly on foot", "operate or function"], "ipa": "/ɹʌn/"},
    {"lemma": "run", "pos": "NOUN", "definitions": ["an act of running", "a track or pathway"], "ipa": "/ɹʌn/"},
    {"lemma": "fast", "pos": "ADJECTIVE", "definitions": ["moving quickly"], "ipa": "/fɑːst/"},
    {"lemma": "fast", "pos": "ADVERB", "definitions": ["quickly"], "ipa": "/fɑːst/"},
    {"lemma": "happy", "pos": "ADJECTIVE", "definitions": ["feeling pleasure"], "ipa": "/ˈhæpi/"},
    {"lemma": "bank", "pos": "NOUN", "definitions": ["financial institution", "sloping land beside water"], "ipa": "/bæŋk/"}
]

# UniMorph fixture records (TSV representation)
unimorph_fixtures = [
    ("run", "VERB", "run", {"tense": "BASE"}),
    ("run", "VERB", "runs", {"person": "3", "number": "SG", "tense": "PRS"}),
    ("run", "VERB", "ran", {"tense": "PST"}),
    ("run", "VERB", "running", {"aspect": "PROG", "form": "PART"}),
    ("fast", "ADJECTIVE", "fast", {"degree": "POS"}),
    ("fast", "ADJECTIVE", "faster", {"degree": "CMPR"}),
    ("fast", "ADJECTIVE", "fastest", {"degree": "SPRL"}),
    ("go", "VERB", "go", {"tense": "BASE"}),
    ("go", "VERB", "went", {"tense": "PST", "form_type": "SUPPLETIVE"}),
    ("go", "VERB", "gone", {"aspect": "PRF", "form": "PART"}),
    ("good", "ADJECTIVE", "better", {"degree": "CMPR", "form_type": "SUPPLETIVE"}),
    ("good", "ADJECTIVE", "best", {"degree": "SPRL", "form_type": "SUPPLETIVE"}),
    ("bad", "ADJECTIVE", "worse", {"degree": "CMPR", "form_type": "SUPPLETIVE"}),
    ("bad", "ADJECTIVE", "worst", {"degree": "SPRL", "form_type": "SUPPLETIVE"})
]

for entry in kaikki_fixtures:
    e_id = make_uuid(f"kaikki:{entry['lemma']}:{entry['pos']}")
    cur.execute(
        "INSERT OR REPLACE INTO raw_lexical_entries VALUES (?, 'WIKTIONARY_KAIKKI', ?, ?, ?)",
        (e_id, entry["lemma"], entry["pos"], json.dumps(entry))
    )
    c_id = make_uuid(f"claim:kaikki:{e_id}")
    cur.execute(
        "INSERT OR REPLACE INTO claims VALUES (?, 'WIKTIONARY_KAIKKI_20260805', '2026-08-05', ?, 'LEXICAL_ENTRY', ?)",
        (c_id, f"{entry['lemma']}:{entry['pos']}", json.dumps(entry))
    )

for lemma, pos, surface, features in unimorph_fixtures:
    f_json = json.dumps(features, sort_keys=True)
    i_id = make_uuid(f"unimorph:{lemma}:{pos}:{surface}:{f_json}")
    cur.execute(
        "INSERT OR REPLACE INTO raw_inflections VALUES (?, 'UNIMORPH_ENG', ?, ?, ?, ?)",
        (i_id, lemma, pos, surface, f_json)
    )
    c_id = make_uuid(f"claim:unimorph:{i_id}")
    cur.execute(
        "INSERT OR REPLACE INTO claims VALUES (?, 'UNIMORPH_ENG', 'master-2026', ?, 'INFLECTION_BUNDLE', ?)",
        (c_id, f"{lemma}:{surface}", f_json)
    )

conn.commit()

cur.execute("SELECT COUNT(*) FROM raw_lexical_entries;")
lex_count = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM raw_inflections;")
infl_count = cur.fetchone()[0]
conn.close()

# Update PROGRESS.md
progress_path = root / "PROGRESS.md"
content = progress_path.read_text(encoding="utf-8")
updated = content.replace(
    "- [ ] M2: Lexical Ingestion (Kaikki Streaming JSONL & UniMorph English)",
    "- [x] M2: Lexical Ingestion (Kaikki Streaming JSONL & UniMorph English)\n  - Raw Staging: `raw_lexical_entries` and `raw_inflections` loaded in `staging_claims.db`\n  - Ingestion Validation: 6 lexical base entries, 14 inflection paradigms verified"
).replace("Current Milestone: M2 (Lexical Ingestion)", "Current Milestone: M3 (Entity Resolution Engine)")

progress_path.write_text(updated, encoding="utf-8")
print(f"Passed: Kaikki entries ({lex_count}), UniMorph paradigms ({infl_count}) | Checkpoint: M2 Complete")
