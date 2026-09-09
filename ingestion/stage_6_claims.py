"""
Stage 6: Claim Resolution & Conflict Marking
Compliance: PRD.md Section 2, ONTOLOGY.md Section 3, ADR-002, INGESTION_PIPELINE.md Stage 6
"""

import json
import os
import shutil
import sqlite3
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

STAGING_DIR = os.path.join(PROJECT_ROOT, "data", "staging")
CLAIMS_DB_PATH = os.path.join(STAGING_DIR, "claims.db")
INFERRED_DB_PATH = os.path.join(STAGING_DIR, "inferred_graph.db")
RESOLVED_CLAIMS_DB_PATH = os.path.join(STAGING_DIR, "resolved_claims_graph.db")

def init_claims_schema(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relation_claims (
            relation_id TEXT NOT NULL,
            claim_id TEXT NOT NULL,
            PRIMARY KEY (relation_id, claim_id),
            FOREIGN KEY (relation_id) REFERENCES relations(id) ON DELETE CASCADE,
            FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rc_rel ON relation_claims(relation_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rc_clm ON relation_claims(claim_id);")
    conn.commit()

def run_stage_6() -> bool:
    print("[STAGE 6] Initiating Claim Resolution & Provenance Linking...")
    if not os.path.exists(INFERRED_DB_PATH):
        print(f"[ERROR] Stage 5 inferred database missing at {INFERRED_DB_PATH}", file=sys.stderr)
        return False
    if not os.path.exists(CLAIMS_DB_PATH):
        print(f"[ERROR] Staging claims database missing at {CLAIMS_DB_PATH}", file=sys.stderr)
        return False

    os.makedirs(STAGING_DIR, exist_ok=True)
    shutil.copyfile(INFERRED_DB_PATH, RESOLVED_CLAIMS_DB_PATH)

    dest_conn = sqlite3.connect(RESOLVED_CLAIMS_DB_PATH)
    dest_cursor = dest_conn.cursor()

    # Normalize entity table names to match distribution schema
    dest_cursor.execute("ALTER TABLE resolved_lexemes RENAME TO lexemes;")
    dest_cursor.execute("ALTER TABLE resolved_forms RENAME TO forms;")
    dest_cursor.execute("ALTER TABLE resolved_relations RENAME TO relations;")
    dest_cursor.execute("ALTER TABLE resolved_morphemes RENAME TO morphemes;")
    dest_conn.commit()

    dest_cursor.execute(f"ATTACH DATABASE '{CLAIMS_DB_PATH}' AS raw_staging;")
    dest_cursor.execute("""
        CREATE TABLE claims AS SELECT * FROM raw_staging.staging_claims;
    """)
    dest_cursor.execute("CREATE INDEX idx_claims_id ON claims(id);")
    dest_cursor.execute("CREATE INDEX idx_claims_subj ON claims(subject);")
    dest_conn.commit()
    init_claims_schema(dest_conn)

    try:
        # Link HAS_FORM relations to supporting raw UNIMORPH_ENG claims
        dest_cursor.execute("""
            INSERT OR IGNORE INTO relation_claims (relation_id, claim_id)
            SELECT r.id, c.id
            FROM relations r
            JOIN lexemes l ON r.subject_id = l.id
            JOIN forms f ON r.object_id = f.id
            JOIN claims c ON c.source = 'UNIMORPH_ENG' 
                         AND c.subject = l.lemma 
                          AND json_extract(c.object_json, '$.surface') = f.surface
            WHERE r.relation_type = 'HAS_FORM';
        """)

        # Link ETYMOLOGICALLY_FROM relations to Kaikki etymology claims
        dest_cursor.execute("""
            INSERT OR IGNORE INTO relation_claims (relation_id, claim_id)
            SELECT r.id, c.id
            FROM relations r
            JOIN claims c ON c.predicate = 'ETYMOLOGICALLY_FROM'
            WHERE r.relation_type = 'ETYMOLOGICALLY_FROM';
        """)
        
        # Attach SUBTLEX frequency summaries directly to canonical Lexemes
        dest_cursor.execute("""
            SELECT subject, object_json FROM claims WHERE source = 'SUBTLEX_US_R1';
        """)
        freq_updates = [
            (obj_json, subject) for subject, obj_json in dest_cursor.fetchall()
        ]
        dest_cursor.executemany("""
            UPDATE lexemes SET frequency_summary = ? WHERE normalized_lemma = ?;
        """, freq_updates)

        dest_cursor.execute("DETACH DATABASE raw_staging;")
        dest_conn.commit()
        print("[SUCCESS] Stage 6 finished. Provenance graph committed to data/staging/resolved_claims_graph.db.")
        return True

    except Exception as e:
        print(f"[ERROR] Stage 6 failed: {e}", file=sys.stderr)
        return False
    finally:
        dest_conn.close()

if __name__ == "__main__":
    if not run_stage_6():
        sys.exit(1)
