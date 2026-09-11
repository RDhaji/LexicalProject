import argparse
import os
import sqlite3
import sys
import time

EPISTEMIC_CLASSES_EDGES = {"EXPLICIT", "GENERATED", "ATTESTED", "INFERRED", "UNCERTAIN"}
EPISTEMIC_CLASSES_PRON = {"ATTESTED", "EXPLICIT"}

def main():
    parser = argparse.ArgumentParser(description="Corpus Claim Provenance and Referential Audit")
    parser.add_argument("--db", required=True, help="Path to SQLite database")
    parser.add_argument("--fixtures", nargs="+", default=["run", "fast", "happy", "go", "good", "bad", "bank"], help="Vertical-slice fixtures")
    parser.add_argument("--log-out", required=True, help="Path to write log output")
    args = parser.parse_args()

    t0 = time.time()
    os.makedirs(os.path.dirname(args.log_out), exist_ok=True)

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_key_check;")
    fk_violations = cur.fetchall()

    cur.execute("SELECT DISTINCT epistemic_class FROM edges;")
    edges_classes = {row[0] for row in cur.fetchall()}
    invalid_edges_classes = sorted(list(edges_classes - EPISTEMIC_CLASSES_EDGES))

    cur.execute("SELECT DISTINCT epistemic_class FROM pronunciations;")
    pron_classes = {row[0] for row in cur.fetchall()}
    invalid_pron_classes = sorted(list(pron_classes - EPISTEMIC_CLASSES_PRON))

    cur.execute("""
        SELECT COUNT(*) FROM pronunciations p
        WHERE (p.target_type = 'LEXEME' AND NOT EXISTS (SELECT 1 FROM lexemes l WHERE l.id = p.target_id))
           OR (p.target_type = 'FORM' AND NOT EXISTS (SELECT 1 FROM forms f WHERE f.id = p.target_id));
    """)
    orphaned_pronunciations = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM edges e
        WHERE (
            (e.source_type = 'LEXEME' AND NOT EXISTS (SELECT 1 FROM lexemes l WHERE l.id = e.source_id) AND NOT EXISTS (SELECT 1 FROM lexemes_es le WHERE le.id = e.source_id))
            OR (e.source_type = 'FORM' AND NOT EXISTS (SELECT 1 FROM forms f WHERE f.id = e.source_id) AND NOT EXISTS (SELECT 1 FROM forms_es fe WHERE fe.id = e.source_id))
            OR (e.target_type = 'LEXEME' AND NOT EXISTS (SELECT 1 FROM lexemes l WHERE l.id = e.target_id) AND NOT EXISTS (SELECT 1 FROM lexemes_es le WHERE le.id = e.target_id))
            OR (e.target_type = 'FORM' AND NOT EXISTS (SELECT 1 FROM forms f WHERE f.id = e.target_id) AND NOT EXISTS (SELECT 1 FROM forms_es fe WHERE fe.id = e.target_id))
        );
    """)
    orphaned_edges = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pronunciations WHERE provenance_id IS NULL OR TRIM(provenance_id) = '';")
    unattributed_pronunciations = cur.fetchone()[0]

    placeholders = ",".join(["?"] * len(args.fixtures))
    cur.execute(f"""
        SELECT l.lemma, COUNT(e.id)
        FROM lexemes l
        LEFT JOIN edges e ON (e.source_id = l.id AND e.source_type = 'LEXEME')
                          OR (e.target_id = l.id AND e.target_type = 'LEXEME')
        WHERE l.lemma IN ({placeholders})
        GROUP BY l.lemma;
    """, args.fixtures)
    fixture_counts = dict(cur.fetchall())

    elapsed = time.time() - t0
    missing_fixtures = [f for f in args.fixtures if f not in fixture_counts or fixture_counts[f] == 0]

    passed = (
        len(fk_violations) == 0
        and len(invalid_edges_classes) == 0
        and len(invalid_pron_classes) == 0
        and orphaned_pronunciations == 0
        and orphaned_edges == 0
        and len(missing_fixtures) == 0
    )

    report = [
        "=== CORPUS PROVENANCE & REFERENTIAL AUDIT ===",
        f"Duration: {elapsed:.2f}s",
        f"FK Violations: {len(fk_violations)}",
        f"Invalid Edges Epistemic Classes: {invalid_edges_classes if invalid_edges_classes else 'None (PASS)'}",
        f"Invalid Pronunciations Epistemic Classes: {invalid_pron_classes if invalid_pron_classes else 'None (PASS)'}",
        f"Orphaned Edges: {orphaned_edges}",
        f"Orphaned Pronunciations: {orphaned_pronunciations}",
        f"Unattributed Pronunciations: {unattributed_pronunciations}",
        f"Fixtures Audited: {len(args.fixtures)} | Missing/Zero Edges: {missing_fixtures if missing_fixtures else 'None (PASS)'}",
        f"Status: {'PASS' if passed else 'FAIL'}"
    ]

    with open(args.log_out, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")

    print("\n".join(report))
    sys.exit(0 if passed else 1)
