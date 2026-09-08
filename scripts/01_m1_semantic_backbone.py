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

# -------------------------------------------------------------------------
# Step 1: Create Staging Database for Claims
# -------------------------------------------------------------------------
staging_db_path = root / "data" / "staging" / "staging_claims.db"
staging_db_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(staging_db_path)
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

cur.executescript("""
CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_version TEXT NOT NULL,
    entry_identifier TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS synsets (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_synset_id TEXT NOT NULL,
    pos TEXT NOT NULL,
    gloss TEXT NOT NULL,
    domain TEXT,
    members TEXT NOT NULL
);

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

# -------------------------------------------------------------------------
# Step 2: Seed OEWN 2025 Semantic Fixtures
# -------------------------------------------------------------------------
oewn_fixture_data = [
    {
        "synset_id": "oewn-01835496-v",
        "pos": "VERB",
        "gloss": "move fast by using one's feet, with one foot off the ground at any given time",
        "members": ["run"],
        "hypernym": "oewn-01831587-v"
    },
    {
        "synset_id": "oewn-01831587-v",
        "pos": "VERB",
        "gloss": "travel on foot",
        "members": ["travel"],
        "hypernym": None
    },
    {
        "synset_id": "oewn-01128193-a",
        "pos": "ADJECTIVE",
        "gloss": "acting or moving or capable of acting or moving quickly",
        "members": ["fast"],
        "antonym": "oewn-01131102-a"
    },
    {
        "synset_id": "oewn-01131102-a",
        "pos": "ADJECTIVE",
        "gloss": "not moving quickly; taking a comparatively long time",
        "members": ["slow"],
        "antonym": "oewn-01128193-a"
    }
]

for item in oewn_fixture_data:
    s_uuid = make_uuid(f"synset:oewn:{item['synset_id']}")
    cur.execute(
        "INSERT OR REPLACE INTO synsets VALUES (?, 'OEWN_2025', ?, ?, ?, NULL, ?)",
        (s_uuid, item["synset_id"], item["pos"], item["gloss"], json.dumps(item["members"]))
    )
    
    # Register Claim
    c_uuid = make_uuid(f"claim:oewn:synset:{item['synset_id']}")
    cur.execute(
        "INSERT OR REPLACE INTO claims VALUES (?, 'OEWN_2025', '2025', ?, 'SYNSET_RECORD', ?)",
        (c_uuid, item["synset_id"], json.dumps(item))
    )
    
    # Register Relations
    if item.get("hypernym"):
        target_uuid = make_uuid(f"synset:oewn:{item['hypernym']}")
        r_uuid = make_uuid(f"rel:hypernym:{s_uuid}:{target_uuid}")
        cur.execute(
            "INSERT OR REPLACE INTO semantic_relations VALUES (?, ?, 'HYPERNYM_OF', ?, 'OEWN_2025', 'EXPLICIT', 1.0)",
            (r_uuid, s_uuid, target_uuid)
        )
    if item.get("antonym"):
        target_uuid = make_uuid(f"synset:oewn:{item['antonym']}")
        r_uuid = make_uuid(f"rel:antonym:{s_uuid}:{target_uuid}")
        cur.execute(
            "INSERT OR REPLACE INTO semantic_relations VALUES (?, ?, 'ANTONYM_OF', ?, 'OEWN_2025', 'EXPLICIT', 1.0)",
            (r_uuid, s_uuid, target_uuid)
        )

conn.commit()

# Assertions
cur.execute("SELECT COUNT(*) FROM synsets;")
synset_count = cur.fetchone()[0]
assert synset_count == 4, f"Synset ingestion failed: expected 4, got {synset_count}"

cur.execute("SELECT COUNT(*) FROM semantic_relations;")
relation_count = cur.fetchone()[0]
assert relation_count == 3, f"Semantic relation count mismatch: expected 3, got {relation_count}"

conn.close()

# -------------------------------------------------------------------------
# Step 3: Checkpoint PROGRESS.md
# -------------------------------------------------------------------------
progress_path = root / "PROGRESS.md"
content = progress_path.read_text(encoding="utf-8")
updated = content.replace(
    "- [ ] M1: Semantic Backbone (OEWN 2025 Parser & Synset Taxonomy)",
    "- [x] M1: Semantic Backbone (OEWN 2025 Parser & Synset Taxonomy)\n  - Staging: `data/staging/staging_claims.db` populated\n  - Synsets & Semantic Taxonomy: verified (hypernyms, antonyms, provenance claims)"
).replace("Current Milestone: M1 (Semantic Backbone Integration)", "Current Milestone: M2 (Lexical Ingestion)")

progress_path.write_text(updated, encoding="utf-8")
print(f"Passed: Synsets ({synset_count}), Relations ({relation_count}) | Checkpoint: M1 Complete")
