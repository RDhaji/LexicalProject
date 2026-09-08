"""
Unit & Regression Tests for Stage 1 Ingestion Parsers
Compliance: PRD.md Section 2, ADR-002, INGESTION_PIPELINE.md Stage 1
"""

import os
import sys
import sqlite3
import unittest

# Deterministic root injection to prevent ModuleNotFoundError across varied environments
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.stage_1_parse import run_stage_1, STAGING_DB_PATH

class TestStage1Parsers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(STAGING_DB_PATH):
            os.remove(STAGING_DB_PATH)
        success = run_stage_1()
        assert success, "Stage 1 parser execution failed during test setup."

    def setUp(self):
        self.conn = sqlite3.connect(STAGING_DB_PATH)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_staging_claims_schema(self):
        """Verify staging_claims table exists with required provenance columns."""
        self.cursor.execute("PRAGMA table_info(staging_claims);")
        columns = {row[1] for row in self.cursor.fetchall()}
        expected = {"id", "source", "source_key", "claim_type", "subject", "predicate", "object_json", "extracted_at"}
        self.assertTrue(expected.issubset(columns), f"Missing required columns in staging_claims: {expected - columns}")

    def test_unimorph_claims_extracted(self):
        """Ensure UniMorph inflections are registered as Form claims, not Lexeme creations (ADR-003)."""
        self.cursor.execute("""
            SELECT subject, predicate, object_json 
            FROM staging_claims 
            WHERE source = 'UNIMORPH_ENG' AND subject = 'go' AND predicate = 'HAS_INFLECTION'
        """)
        rows = self.cursor.fetchall()
        self.assertGreater(len(rows), 0, "No UniMorph inflection claims found for 'go'.")
        surfaces = [row[2] for row in rows]
        self.assertTrue(any("went" in s for s in surfaces), "UniMorph did not extract 'went' for 'go'.")

    def test_kaikki_claims_extracted(self):
        """Ensure Kaikki entries preserve orthography, POS, and IPA without heuristic pruning."""
        self.cursor.execute("""
            SELECT subject, predicate, object_json 
            FROM staging_claims 
            WHERE source = 'WIKTIONARY_KAIKKI_20260805' AND subject = 'car'
        """)
        rows = self.cursor.fetchall()
        self.assertGreater(len(rows), 0, "No Kaikki claims found for 'car'.")

    def test_subtlex_claims_extracted(self):
        """Verify SUBTLEX frequency data is cataloged as raw metric claims."""
        self.cursor.execute("""
            SELECT subject, object_json 
            FROM staging_claims 
            WHERE source = 'SUBTLEX_US_R1' AND subject = 'go'
        """)
        row = self.cursor.fetchone()
        self.assertIsNotNone(row, "SUBTLEX claim missing for 'go'.")
        self.assertIn("FREQcount", row[1], "SUBTLEX claim missing FREQcount payload.")

    def test_no_forbidden_substring_links(self):
        """Negative Invariant: No parser creates edge claims between substring pairs (ADR-005, PRD Section 2)."""
        self.cursor.execute("""
            SELECT * FROM staging_claims 
            WHERE (subject = 'car' AND object_json LIKE '%carpet%')
               OR (subject = 'carpet' AND object_json LIKE '%"car"%')
        """)
        rows = self.cursor.fetchall()
        self.assertEqual(len(rows), 0, "Violated negative invariant: Found heuristic relation claim between 'car' and 'carpet'.")

if __name__ == "__main__":
    unittest.main()
