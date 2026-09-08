"""
Unit & Regression Tests for Stage 5 Controlled Inference Engine
Compliance: PRD.md Section 2, ONTOLOGY.md Section 3, ADR-002, ADR-005, INGESTION_PIPELINE.md Stage 5
"""

import os
import sys
import sqlite3
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.stage_5_inference import run_stage_5, INFERRED_DB_PATH

class TestStage5Inference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(INFERRED_DB_PATH):
            os.remove(INFERRED_DB_PATH)
        success = run_stage_5()
        assert success, "Stage 5 inference execution failed during test setup."

    def setUp(self):
        self.conn = sqlite3.connect(INFERRED_DB_PATH)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_epistemic_classification_on_inferred_relations(self):
        """Invariant ONTOLOGY.md §3: Inferred relations must carry INFERRED or GENERATED evidence_type."""
        self.cursor.execute("SELECT DISTINCT evidence_type FROM resolved_relations WHERE resolution_status = 'INFERRED';")
        types = {row[0] for row in self.cursor.fetchall()}
        self.assertTrue(types.issubset({"INFERRED", "GENERATED"}), f"Invalid evidence_type for inferred relations: {types}")

    def test_confidence_score_ceiling(self):
        """Invariant: Inferred relations cannot carry 1.0 confidence (reserved for EXPLICIT)."""
        self.cursor.execute("SELECT confidence FROM resolved_relations WHERE evidence_type = 'INFERRED';")
        scores = [row[0] for row in self.cursor.fetchall()]
        for s in scores:
            self.assertLessEqual(s, 0.85, f"Inferred relation confidence exceeds allowed 0.85 threshold: {s}")

    def test_inflects_to_chain(self):
        """Benchmark: Degree chain generated between Form entities (INFLECTS_TO: faster -> fastest)."""
        self.cursor.execute("""
            SELECT r.id, f1.surface, f2.surface, r.relation_type
            FROM resolved_relations r
            JOIN resolved_forms f1 ON r.subject_id = f1.id
            JOIN resolved_forms f2 ON r.object_id = f2.id
            WHERE r.relation_type = 'INFLECTS_TO'
              AND f1.surface = 'faster' AND f2.surface = 'fastest';
        """)
        row = self.cursor.fetchone()
        self.assertIsNotNone(row, "Missing INFLECTS_TO candidate relation between 'faster' and 'fastest'.")

    def test_negative_heuristic_firewall(self):
        """Negative Invariant ADR-005: Zero inferred relations for substring traps (car ≠ carpet)."""
        self.cursor.execute("""
            SELECT r.id, l1.normalized_lemma, l2.normalized_lemma
            FROM resolved_relations r
            JOIN resolved_lexemes l1 ON r.subject_id = l1.id
            JOIN resolved_lexemes l2 ON r.object_id = l2.id
            WHERE (l1.normalized_lemma = 'car' AND l2.normalized_lemma = 'carpet')
               OR (l1.normalized_lemma = 'carpet' AND l2.normalized_lemma = 'car');
        """)
        rows = self.cursor.fetchall()
        self.assertEqual(len(rows), 0, "Violated ADR-005: Substring false-positive edge created.")

if __name__ == "__main__":
    unittest.main()
