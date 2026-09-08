"""
Quality Gates Acceptance Suite (Gates A through E)
Compliance: INGESTION_PIPELINE.md Section 2, MORPHOLOGY.md Section 1-2, ADR-003, ADR-005
"""

import os
import sqlite3
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOLVED_DB = os.path.join(PROJECT_ROOT, "data", "staging", "resolved_graph.db")

class TestQualityGates(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.exists(RESOLVED_DB), f"Database not found: {RESOLVED_DB}")
        self.conn = sqlite3.connect(RESOLVED_DB)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_gate_b_no_orphans(self):
        """Gate B: Zero orphaned relations across lexemes and forms."""
        self.cur.execute("""
        SELECT COUNT(*) as count
        FROM resolved_relations r
        LEFT JOIN resolved_lexemes l ON r.subject_id = l.id
        WHERE r.subject_type = 'LEXEME' AND l.id IS NULL;
        """)
        self.assertEqual(self.cur.fetchone()["count"], 0, "Gate B Failed: Orphaned subject lexemes detected.")

        self.cur.execute("""
        SELECT COUNT(*) as count
        FROM resolved_relations r
        LEFT JOIN resolved_forms f ON r.object_id = f.id
        WHERE r.relation_type = 'HAS_FORM' AND f.id IS NULL;
        """)
        self.assertEqual(self.cur.fetchone()["count"], 0, "Gate B Failed: Orphaned form objects detected.")

    def test_gate_c_morphology_baseline(self):
        """Gate C: Authoritative inflection baseline checks."""
        baselines = [
            ("go", "went"),
            ("mouse", "mice"),
            ("fast", "faster")
        ]
        for lemma, surface in baselines:
            self.cur.execute("""
            SELECT COUNT(*) as count
            FROM resolved_relations r
            JOIN resolved_lexemes l ON r.subject_id = l.id
            JOIN resolved_forms f ON r.object_id = f.id
            WHERE l.normalized_lemma = ? AND f.normalized_surface = ? AND r.relation_type = 'HAS_FORM';
            """, (lemma, surface))
            self.assertGreater(self.cur.fetchone()["count"], 0, f"Gate C Failed: Missing baseline pair {lemma} -> {surface}")

    def test_gate_d_false_positive_regression_traps(self):
        """Gate D: Negative traps must NEVER be connected via morphological or derivational relations."""
        traps = [
            ("go", "goal"),
            ("ride", "riddance"),
            ("art", "article"),
            ("car", "carpet")
        ]
        for a, b in traps:
            self.cur.execute("""
            SELECT COUNT(*) as count
            FROM resolved_relations r
            JOIN resolved_lexemes l1 ON r.subject_id = l1.id
            JOIN resolved_lexemes l2 ON r.object_id = l2.id
            WHERE ((l1.normalized_lemma = ? AND l2.normalized_lemma = ?)
                OR (l1.normalized_lemma = ? AND l2.normalized_lemma = ?))
              AND r.relation_type IN ('DERIVED_FROM', 'MORPHOLOGICALLY_RELATED');
            """, (a, b, b, a))
            self.assertEqual(self.cur.fetchone()["count"], 0, f"Gate D Invariant Violation: False connection detected between {a} and {b}")

    def test_gate_e_provenance_completeness(self):
        """Gate E: 100% of relations must trace to supporting claims."""
        self.cur.execute("""
        SELECT COUNT(*) as count
        FROM resolved_relations r
        LEFT JOIN relation_claims rc ON r.id = rc.relation_id
        WHERE rc.relation_id IS NULL;
        """)
        self.assertEqual(self.cur.fetchone()["count"], 0, "Gate E Failed: Relations exist without provenance claims.")

if __name__ == "__main__":
    unittest.main()
