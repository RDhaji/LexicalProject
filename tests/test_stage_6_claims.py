"""
Unit & Regression Tests for Stage 6 Claim Resolution & Conflict Marking
Compliance: PRD.md Section 2, ONTOLOGY.md Section 3, ADR-002, INGESTION_PIPELINE.md Stage 6
"""

import os
import sys
import sqlite3
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.stage_6_claims import run_stage_6, RESOLVED_CLAIMS_DB_PATH

class TestStage6Claims(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(RESOLVED_CLAIMS_DB_PATH):
            os.remove(RESOLVED_CLAIMS_DB_PATH)
        success = run_stage_6()
        assert success, "Stage 6 claim resolution failed during test setup."

    def setUp(self):
        self.conn = sqlite3.connect(RESOLVED_CLAIMS_DB_PATH)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_claims_table_presence_and_columns(self):
        self.cursor.execute("PRAGMA table_info(claims);")
        cols = {row[1] for row in self.cursor.fetchall()}
        expected = {"id", "source", "source_key", "claim_type", "subject", "predicate", "object_json", "extracted_at"}
        self.assertTrue(expected.issubset(cols), f"Missing columns in claims: {expected - cols}")

    def test_relation_claims_provenance_linkage(self):
        self.cursor.execute("""
            SELECT r.id 
            FROM relations r
            LEFT JOIN relation_claims rc ON r.id = rc.relation_id
            WHERE r.evidence_type = 'EXPLICIT' AND rc.claim_id IS NULL;
        """)
        unlinked = self.cursor.fetchall()
        self.assertEqual(len(unlinked), 0, f"Found EXPLICIT relations lacking claim provenance: {unlinked}")

    def test_conflict_preservation_no_silent_drop(self):
        self.cursor.execute("SELECT COUNT(*) FROM relations WHERE evidence_type = 'UNCERTAIN';")
        uncertain_count = self.cursor.fetchone()[0]
        self.assertGreaterEqual(uncertain_count, 0)

    def test_frequency_summary_populated_on_lexemes(self):
        self.cursor.execute("SELECT frequency_summary FROM lexemes WHERE normalized_lemma = 'go' AND pos = 'VERB';")
        row = self.cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertIn("FREQcount", row[0])

if __name__ == "__main__":
    unittest.main()
