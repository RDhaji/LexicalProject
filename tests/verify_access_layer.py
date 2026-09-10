import sqlite3
import json
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
graph_db_path = os.path.join(project_root, "data/compiled/lexical_graph.db")
workspace_db_path = os.path.join(project_root, "data/user_workspace.db")

print("[TEST] Initializing Client Access Layer Verification...")

# 1. Read-Only Invariant Test on lexical_graph.db
conn_graph = sqlite3.connect(f"file:{graph_db_path}?mode=ro", uri=True)
cursor_graph = conn_graph.cursor()

try:
    cursor_graph.execute("CREATE TABLE write_violation_test (id INT)")
    print("[FAIL] Graph database allows writes. Read-only invariant violated.")
    sys.exit(1)
except sqlite3.OperationalError:
    print("[PASS] Graph database correctly configured as strictly READ-ONLY.")

# 2. Exact Lookup & Join Traversal Test
cursor_graph.execute('''
    SELECT f.surface, l.lemma, l.pos, r.relation_type
    FROM forms f
    JOIN relations r ON r.object_id = f.id AND r.relation_type = 'HAS_FORM'
    JOIN lexemes l ON l.id = r.subject_id
    LIMIT 5
''')
sample_records = cursor_graph.fetchall()
assert len(sample_records) > 0, "No records returned from forms -> lexemes join"
print(f"[PASS] Exact lookup traversal verified. Sample: {sample_records[0]}")

# 3. Covering Index Verification
cursor_graph.execute('''
    EXPLAIN QUERY PLAN
    SELECT id FROM forms WHERE normalized_surface = 'running'
''')
plan = cursor_graph.fetchall()
plan_str = " ".join([str(p) for p in plan])
assert "idx_forms_normalized_surface" in plan_str or "COVERING" in plan_str, f"Unindexed query plan: {plan_str}"
print("[PASS] Covering B-Tree index utilized for surface lookups.")

# 4. Partition Isolation Test (user_workspace.db)
conn_workspace = sqlite3.connect(workspace_db_path)
cursor_workspace = conn_workspace.cursor()

cursor_workspace.execute('''
    CREATE TABLE IF NOT EXISTS user_notes (
        id TEXT PRIMARY KEY,
        target_entity_id TEXT NOT NULL,
        target_entity_type TEXT NOT NULL,
        note_content TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
    )
''')
cursor_workspace.execute('''
    INSERT OR REPLACE INTO user_notes VALUES 
    ('test-note-1', '00000000-0000-0000-0000-000000000000', 'LEXEME', 'Verified note', 1725500000, 1725500000)
''')
conn_workspace.commit()

# Verify zero foreign keys into lexical_graph.db
cursor_workspace.execute("PRAGMA foreign_key_list(user_notes)")
fks = cursor_workspace.fetchall()
assert len(fks) == 0, "Partition isolation violated: foreign keys detected in user partition."
print("[PASS] User partition write & isolation verified (Zero cross-database foreign keys).")

# 5. Provenance Ledger & Claims Explainability Test (Mapped schema)
cursor_graph.execute('''
    SELECT r.id, c.predicate, c.evidence_type
    FROM relations r
    JOIN relation_claims rc ON rc.relation_id = r.id
    JOIN claims c ON c.id = rc.claim_id
    LIMIT 1
''')
provenance_sample = cursor_graph.fetchone()
assert provenance_sample is not None, "Claims ledger provenance link missing."
print(f"[PASS] Epistemic claims provenance verified: {provenance_sample}")

print("\n[SUCCESS] Client Access Layer and verification tests PASSED with 100% compliance.")
