"""
Stage 7: Mandatory Quality Gates Engine (Gates B - E)
Compliance: PRD.md Section 2, ONTOLOGY.md Section 1-3, INGESTION_PIPELINE.md Section 2, Gate B-E
"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

STAGING_DIR = os.path.join(PROJECT_ROOT, "data", "staging")
RESOLVED_CLAIMS_DB_PATH = os.path.join(STAGING_DIR, "resolved_claims_graph.db")

ALLOWED_POS = {
    "NOUN", "VERB", "ADJECTIVE", "ADVERB", "PRONOUN", 
    "DETERMINER", "PREPOSITION", "CONJUNCTION", "INTERJECTION", 
    "AUXILIARY", "NUMERAL", "PARTICLE", "OTHER"
}

def verify_gate_b(cursor: sqlite3.Cursor) -> bool:
    print("  -> Checking Gate B (Ontology Integrity)...")
    # 1. POS Tag check
    cursor.execute("SELECT DISTINCT pos FROM lexemes;")
    extracted_pos = {row[0] for row in cursor.fetchall()}
    invalid_pos = extracted_pos - ALLOWED_POS
    if invalid_pos:
        print(f"     [FAIL] Gate B: Invalid POS tags found: {invalid_pos}")
        return False

    # 2. Orphan check for HAS_FORM
    cursor.execute("""
        SELECT COUNT(*) FROM relations r
        LEFT JOIN lexemes l ON r.subject_id = l.id
        LEFT JOIN forms f ON r.object_id = f.id
        WHERE r.relation_type = 'HAS_FORM' AND (l.id IS NULL OR f.id IS NULL);
    """)
    orphans = cursor.fetchone()[0]
    if orphans > 0:
        print(f"     [FAIL] Gate B: Found {orphans} orphaned HAS_FORM relations.")
        return False

    print("     [PASS] Gate B verified.")
    return True

def verify_gate_c(cursor: sqlite3.Cursor) -> bool:
    print("  -> Checking Gate C (Morphology Baseline)...")
    benchmarks = [("go", "went"), ("mouse", "mice"), ("run", "running")]
    for lemma, surface in benchmarks:
        cursor.execute("""
            SELECT COUNT(*) FROM relations r
            JOIN lexemes l ON r.subject_id = l.id
            JOIN forms f ON r.object_id = f.id
            WHERE r.relation_type = 'HAS_FORM' AND l.normalized_lemma = ? AND f.normalized_surface = ?;
        """, (lemma, surface))
        if cursor.fetchone()[0] == 0:
            print(f"     [FAIL] Gate C: Missing baseline inflection ({lemma} -> {surface}).")
            return False

    # Check degree inflection progression (faster -> fastest)
    cursor.execute("""
        SELECT COUNT(*) FROM relations r
        JOIN forms f1 ON r.subject_id = f1.id
        JOIN forms f2 ON r.object_id = f2.id
        WHERE r.relation_type = 'INFLECTS_TO' AND f1.surface = 'faster' AND f2.surface = 'fastest';
    """)
    if cursor.fetchone()[0] == 0:
        print("     [FAIL] Gate C: Missing degree progression (faster -> fastest).")
        return False

    print("     [PASS] Gate C verified.")
    return True

def verify_gate_d(cursor: sqlite3.Cursor) -> bool:
    print("  -> Checking Gate D (False-Positive Regression Traps)...")
    trap_pairs = [
        ("car", "carpet"),
        ("art", "article"),
        ("ride", "riddance"),
        ("go", "goal")
    ]
    for w1, w2 in trap_pairs:
        cursor.execute("""
            SELECT COUNT(*) FROM relations r
            JOIN lexemes l1 ON r.subject_id = l1.id
            JOIN lexemes l2 ON r.object_id = l2.id
            WHERE (l1.normalized_lemma = ? AND l2.normalized_lemma = ?)
               OR (l1.normalized_lemma = ? AND l2.normalized_lemma = ?);
        """, (w1, w2, w2, w1))
        if cursor.fetchone()[0] > 0:
            print(f"     [FAIL] Gate D: False-positive relation detected between trap pair ({w1} <-> {w2})!")
            return False

    print("     [PASS] Gate D verified.")
    return True

def verify_gate_e(cursor: sqlite3.Cursor) -> bool:
    print("  -> Checking Gate E (Provenance Completeness)...")
    cursor.execute("""
        SELECT COUNT(*) FROM relations r
        LEFT JOIN relation_claims rc ON r.id = rc.relation_id
        WHERE r.evidence_type = 'EXPLICIT' AND rc.claim_id IS NULL;
    """)
    unsupported = cursor.fetchone()[0]
    if unsupported > 0:
        print(f"     [FAIL] Gate E: Found {unsupported} EXPLICIT relations lacking supporting claims.")
        return False

    print("     [PASS] Gate E verified.")
    return True

def run_stage_7() -> bool:
    print("[STAGE 7] Initiating Quality Gates (Gates B through E)...")
    if not os.path.exists(RESOLVED_CLAIMS_DB_PATH):
        print(f"[ERROR] Required database missing at {RESOLVED_CLAIMS_DB_PATH}", file=sys.stderr)
        return False

    conn = sqlite3.connect(RESOLVED_CLAIMS_DB_PATH)
    cursor = conn.cursor()

    try:
        passed = (
            verify_gate_b(cursor) and
            verify_gate_c(cursor) and
            verify_gate_d(cursor) and
            verify_gate_e(cursor)
        )
        if passed:
            print("[SUCCESS] Stage 7 passed: All Quality Gates (B - E) satisfied with 100% compliance.")
            return True
        else:
            print("[HALT] Stage 7 Quality Gates failed. Halting build before compilation.")
            return False
    except Exception as e:
        print(f"[ERROR] Gate execution crashed: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if not run_stage_7():
        sys.exit(1)
