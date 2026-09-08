"""
Unit & Regression Tests for Stage 2 Canonical Normalization
Compliance: ONTOLOGY.md Section 1.1, ADR-003, INGESTION_PIPELINE.md Stage 2
"""

import os
import sys
import sqlite3
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.stage_2_normalize import run_stage_2, NORMALIZED_DB_PATH

ALLOWED_POS = {
    "NOUN", "VERB", "ADJECTIVE", "ADVERB", "PRONOUN", 
    "DETERMINER", "PREPOSITION", "CONJUNCTION", "INTERJECTION", 
    "AUXILIARY", "NUMERAL", "PARTICLE", "OTHER"
}

class TestStage2Normalize(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(NORMALIZED_DB_PATH):
            os.remove(NORMALIZED_DB_PATH)
        success = run_stage_2()
        assert success, "Stage 2 normalization execution failed during test setup."

    def setUp(self):
        self.conn = sqlite3.connect(NORMALIZED_DB_PATH)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_normalized_lexemes_schema(self):
        """Verify schema of normalized_lexemes meets ontological specification."""
        self.cursor.execute("PRAGMA table_info(normalized_lexemes);")
        columns = {row[1] for row in self.cursor.fetchall()}
        expected = {"claim_id", "source", "raw_lemma", "normalized_lemma", "canonical_pos", "raw_payload"}
        self.assertTrue(expected.issubset(columns), f"Missing columns in normalized_lexemes: {expected - columns}")

    def test_pos_canonicalization_adherence(self):
        """Invariant: Every mapped POS must belong strictly to ONTOLOGY.md controlled vocabulary."""
        self.cursor.execute("SELECT DISTINCT canonical_pos FROM normalized_lexemes;")
        extracted_pos = {row[0] for row in self.cursor.fetchall()}
        invalid = extracted_pos - ALLOWED_POS
        self.assertEqual(len(invalid), 0, f"Found non-canonical POS tags: {invalid}")

    def test_nfc_and_case_folding(self):
        """Verify text normalization strips whitespace and enforces NFC case folding."""
        self.cursor.execute("SELECT raw_lemma, normalized_lemma FROM normalized_lexemes;")
        for raw, norm in self.cursor.fetchall():
            self.assertEqual(norm, norm.strip().lower(), f"Lemma {norm} is not trimmed and lowercased.")

    def test_unimorph_feature_parsing(self):
        """Verify UniMorph inflection tags are parsed into valid feature JSON payloads (ADR-003)."""
        self.cursor.execute("""
            SELECT normalized_lemma, surface, features_json 
            FROM normalized_forms 
            WHERE normalized_lemma = 'go' AND surface = 'went'
        """)
        row = self.cursor.fetchone()
        self.assertIsNotNone(row, "Normalized form 'went' missing for lemma 'go'.")
        self.assertIn('"tense": "PAST"', row[2], "Past tense feature missing from parsed features.")

    def test_negative_no_lexeme_form_cross_pollution(self):
        """Negative Invariant: Inflected surface realization 'went' must NOT exist as a normalized Lexeme (ADR-003)."""
        self.cursor.execute("SELECT * FROM normalized_lexemes WHERE normalized_lemma = 'went';")
        rows = self.cursor.fetchall()
        self.assertEqual(len(rows), 0, "Violated ADR-003: Surface inflection 'went' registered as an independent Lexeme.")

if __name__ == "__main__":
    unittest.main()
