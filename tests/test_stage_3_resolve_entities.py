"""
Unit & Regression Tests for Stage 3 Entity Resolution
Compliance: ONTOLOGY.md Section 1, ADR-002, ADR-003, INGESTION_PIPELINE.md Stage 3
"""

import os
import sys
import sqlite3
import unittest
import uuid

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.stage_3_resolve_entities import run_stage_3, RESOLVED_DB_PATH, NAMESPACE_LEXICAL

class TestStage3EntityResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(RESOLVED_DB_PATH):
            os.remove(RESOLVED_DB_PATH)
        success = run_stage_3()
        assert success, "Stage 3 entity resolution failed during test setup."

    def setUp(self):
        self.conn = sqlite3.connect(RESOLVED_DB_PATH)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_deterministic_uuidv5_generation(self):
        """Verify Lexeme IDs match deterministic UUIDv5 calculation from natural key."""
        self.cursor.execute("SELECT id, lexeme_key FROM resolved_lexemes LIMIT 10;")
        rows = self.cursor.fetchall()
        self.assertGreater(len(rows), 0, "No resolved lexemes found.")
        for entity_id, lexeme_key in rows:
            expected_uuid = str(uuid.uuid5(NAMESPACE_LEXICAL, lexeme_key))
            self.assertEqual(entity_id, expected_uuid, f"UUIDv5 mismatch for natural key {lexeme_key}")

    def test_lexeme_deduplication_across_sources(self):
        """Verify cross-source unification: Multiple sources assert 'car:NOUN', yielding 1 Lexeme record."""
        self.cursor.execute("SELECT COUNT(*) FROM resolved_lexemes WHERE normalized_lemma = 'car' AND pos = 'NOUN';")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 1, f"Expected exactly 1 resolved Lexeme for 'car:NOUN', found {count}.")

    def test_source_presence_aggregation(self):
        """Verify source_presence JSON aggregates distinct authoritative claims."""
        self.cursor.execute("SELECT source_presence FROM resolved_lexemes WHERE normalized_lemma = 'car' AND pos = 'NOUN';")
        row = self.cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertIn("WIKTIONARY_KAIKKI_20260805", row[0])

    def test_form_resolution_separation(self):
        """Verify Form entities are materialized in resolved_forms, not resolved_lexemes (ADR-003)."""
        self.cursor.execute("SELECT COUNT(*) FROM resolved_forms WHERE surface = 'went';")
        form_count = self.cursor.fetchone()[0]
        self.assertGreater(form_count, 0, "Inflected form 'went' missing from resolved_forms.")

        self.cursor.execute("SELECT COUNT(*) FROM resolved_lexemes WHERE normalized_lemma = 'went';")
        lexeme_count = self.cursor.fetchone()[0]
        self.assertEqual(lexeme_count, 0, "Violated ADR-003: Inflected surface 'went' present in resolved_lexemes.")

    def test_has_form_relational_linkage(self):
        """Verify HAS_FORM edge links Lexeme 'go' to Form 'went'."""
        self.cursor.execute("""
            SELECT r.relation_type, l.normalized_lemma, f.surface
            FROM resolved_relations r
            JOIN resolved_lexemes l ON r.subject_id = l.id
            JOIN resolved_forms f ON r.object_id = f.id
            WHERE r.relation_type = 'HAS_FORM' AND l.normalized_lemma = 'go' AND f.surface = 'went';
        """)
        row = self.cursor.fetchone()
        self.assertIsNotNone(row, "HAS_FORM link missing between Lexeme 'go' and Form 'went'.")

    def test_negative_substring_false_positives(self):
        """Negative Invariant: No relational link between 'car' and 'carpet' (ADR-005)."""
        self.cursor.execute("""
            SELECT * FROM resolved_relations r
            JOIN resolved_lexemes l1 ON r.subject_id = l1.id
            JOIN resolved_lexemes l2 ON r.object_id = l2.id
            WHERE (l1.normalized_lemma = 'car' AND l2.normalized_lemma = 'carpet')
               OR (l1.normalized_lemma = 'carpet' AND l2.normalized_lemma = 'car');
        """)
        rows = self.cursor.fetchall()
        self.assertEqual(len(rows), 0, "Violated negative constraint: False positive relation between 'car' and 'carpet'.")

if __name__ == "__main__":
    unittest.main()
