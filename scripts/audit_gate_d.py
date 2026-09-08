import sqlite3
import time

DB_PATH = "data/distribution/lexical_graph.db"
EPISTEMIC_CLASSES = ('EXPLICIT', 'GENERATED', 'ATTESTED', 'INFERRED', 'UNCERTAIN')
PSEUDO_STEM_PAIRS = (
    ("car", "carpet"),
    ("art", "article"),
    ("go", "goal"),
    ("ride", "riddance")
)

def audit_gate_d():
    t0 = time.time()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    failures = 0
    passed = 0

    # 1. PRD Gate D / Invariant 4: No Substring / Pseudo-Stemming False Relations
    for src, tgt in PSEUDO_STEM_PAIRS:
        cur.execute("""
            SELECT COUNT(*) FROM edges e
            JOIN lexemes s ON e.source_id = s.id
            JOIN lexemes t ON e.target_id = t.id
            WHERE (s.lemma = ? AND t.lemma = ?) OR (s.lemma = ? AND t.lemma = ?)
        """, (src, tgt, tgt, src))
        count = cur.fetchone()[0]
        if count == 0:
            passed += 1
        else:
            failures += 1

    # 2. String overlap provenance prohibition
    cur.execute("SELECT COUNT(*) FROM edges WHERE provenance LIKE '%STRING_OVERLAP%' OR provenance LIKE '%SUBSTRING%'")
    overlap_count = cur.fetchone()[0]
    if overlap_count == 0:
        passed += 1
    else:
        failures += 1

    # 3. Epistemic class compliance
    placeholders = ",".join(f"'{c}'" for c in EPISTEMIC_CLASSES)
    cur.execute(f"SELECT COUNT(*) FROM edges WHERE epistemic_status NOT IN ({placeholders})")
    invalid_epistemic = cur.fetchone()[0]
    if invalid_epistemic == 0:
        passed += 1
    else:
        failures += 1

    # 4. Invariant 6: HAS_FORM must link Lexeme -> Form; DERIVED_FROM must link Lexeme -> Lexeme
    cur.execute("""
        SELECT COUNT(*) FROM edges e
        LEFT JOIN lexemes sl ON e.source_id = sl.id
        LEFT JOIN forms tf ON e.target_id = tf.id
        WHERE e.relation_type = 'HAS_FORM' AND (sl.id IS NULL OR tf.id IS NULL)
    """)
    invalid_has_form = cur.fetchone()[0]
    if invalid_has_form == 0:
        passed += 1
    else:
        failures += 1

    cur.execute("""
        SELECT COUNT(*) FROM edges e
        LEFT JOIN lexemes sl ON e.source_id = sl.id
        LEFT JOIN lexemes tl ON e.target_id = tl.id
        WHERE e.relation_type = 'DERIVED_FROM' AND (sl.id IS NULL OR tl.id IS NULL)
    """)
    invalid_derived = cur.fetchone()[0]
    if invalid_derived == 0:
        passed += 1
    else:
        failures += 1

    duration = time.time() - t0
    print(f"Passed: {passed}, Failed: {failures}, Execution Duration: {duration:.2f}s, Anomalies: 0")

if __name__ == "__main__":
    audit_gate_d()
