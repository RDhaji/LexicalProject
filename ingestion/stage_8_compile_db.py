"""
Stage 8: SQLite Database Compilation, B-Tree Indexing & FTS5 Search Layer
Compliance: ARCHITECTURE.md Section 1-4, ADR-006, ADR-007, INGESTION_PIPELINE.md Stage 8
"""

import os
import shutil
import sqlite3
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

STAGING_DIR = os.path.join(PROJECT_ROOT, "data", "staging")
COMPILED_DIR = os.path.join(PROJECT_ROOT, "data", "compiled")
RESOLVED_CLAIMS_DB_PATH = os.path.join(STAGING_DIR, "resolved_claims_graph.db")
COMPILED_DB_PATH = os.path.join(COMPILED_DIR, "lexical_graph.db")

def run_stage_8() -> bool:
    print("[STAGE 8] Initiating SQLite Compilation & Search Indexing...")
    if not os.path.exists(RESOLVED_CLAIMS_DB_PATH):
        print(f"[ERROR] Stage 7 verified database missing at {RESOLVED_CLAIMS_DB_PATH}", file=sys.stderr)
        return False

    os.makedirs(COMPILED_DIR, exist_ok=True)
    if os.path.exists(COMPILED_DB_PATH):
        os.remove(COMPILED_DB_PATH)

    shutil.copyfile(RESOLVED_CLAIMS_DB_PATH, COMPILED_DB_PATH)

    conn = sqlite3.connect(COMPILED_DB_PATH)
    cursor = conn.cursor()

    try:
        print("  -> Compiling Covering B-Tree Indices...")
        # 1. Covering compound indices (ARCHITECTURE.md Section 3 & 4)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_covering_relations_adj ON relations (subject_id, relation_type, object_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_rev_adj ON relations (object_id, relation_type, subject_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lexemes_norm ON lexemes (normalized_lemma, pos);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_forms_surf ON forms (normalized_surface);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_claims_join ON relation_claims (relation_id, claim_id);")

        print("  -> Compiling SQLite FTS5 Full-Text Search Engine...")
        # 2. SQLite FTS5 Search Table (ARCHITECTURE.md Section 4)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                target_id UNINDEXED,
                target_type UNINDEXED,
                term,
                extra_text
            );
        """)

        # Populate search index with canonical lemmas
        cursor.execute("""
            INSERT INTO search_index (target_id, target_type, term, extra_text)
            SELECT id, 'LEXEME', lemma, normalized_lemma || ' ' || pos FROM lexemes;
        """)

        # Populate search index with attested surface forms
        cursor.execute("""
            INSERT INTO search_index (target_id, target_type, term, extra_text)
            SELECT id, 'FORM', surface, normalized_surface || ' ' || form_type FROM forms;
        """)

        print("  -> Optimizing B-Trees and Query Planner Statistics (ANALYZE & VACUUM)...")
        conn.commit()
        cursor.execute("ANALYZE;")
        conn.commit()
        cursor.execute("VACUUM;")
        conn.close()

        print(f"[SUCCESS] Stage 8 completed. Distribution graph compiled: {COMPILED_DB_PATH}")
        return True

    except Exception as e:
        print(f"[ERROR] Stage 8 compilation failed: {e}", file=sys.stderr)
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    if not run_stage_8():
        sys.exit(1)
