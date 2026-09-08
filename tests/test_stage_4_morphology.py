"""
Unit & Regression Tests for Stage 4 Morphology Build & Separation
Compliance: PRD.md Section 2, MORPHOLOGY.md, ADR-003, ADR-005, INGESTION_PIPELINE.md Stage 4
"""

import os
import sys
import sqlite3
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.stage_4_morphology import run_stage_4, MORPHOLOGY_DB_PATH

class TestStage4Morphology(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(MORPHOLOGY_DB_PATH):
            os.remove(MORPHOLOGY_DB_PATH)
        success = run_stage_4()
        assert success, "Stage 4 morphology execution failed during test setup."

    def setUp(self):
        self.conn = sqlite3.connect(MORPHOLOGY_DB_PATH)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_morpheme_table_schema(self):
        """Verify morpheme entity table adheres to ONTOLOGY.md Section 1.5."""
        self.cursor.execute("PRAGMA table_info(resolved_morphemes);")
        columns = {row[1] for row in self.cursor.fetchall()}
        expected = {"id", "shape", "type", "status"}
        self.assertTrue(expected.issubset(columns), f"Missing columns in resolved_morphemes: {expected - columns}")

    def test_inflection_derivation_physical_isolation(self):
        """Invariant ADR-003 & MORPHOLOGY.md: Forms NEVER participate in DERIVED_FROM edges."""
        self.cursor.execute("""
            SELECT r.id, r.subject_type, r.object_type 
            FROM resolved_relations r 
            WHERE r.relation_type = 'DERIVED_FROM' 
              AND (r.subject_type != 'LEXEME' OR r.object_type != 'LEXEME');
        """)
        invalid_derivations = self.cursor.fetchall()
        self.assertEqual(len(invalid_derivations), 0, "Found DERIVED_FROM relation not connecting two Lexemes.")

    def test_has_form_purity(self):
        """Invariant: HAS_FORM relations link Lexeme strictly to Form."""
        self.cursor.execute("""
            SELECT r.id, r.subject_type, r.object_type 
            FROM resolved_relations r 
            WHERE r.relation_type = 'HAS_FORM' 
              AND (r.subject_type != 'LEXEME' OR r.object_type != 'FORM');
        """)
        invalid_has_forms = self.cursor.fetchall()
        self.assertEqual(len(invalid_has_forms), 0, "Found HAS_FORM relation not mapping Lexeme -> Form.")

    def test_negative_heuristic_trap_pairs(self):
        """Negative Invariant ADR-005: Stemmer inversion/substrings prohibited (car != carpet, art != article)."""
        self.cursor.execute("""
            SELECT r.id, l1.normalized_lemma, l2.normalized_lemma 
            FROM resolved_relations r
            JOIN resolved_lexemes l1 ON r.subject_id = l1.id
            JOIN resolved_lexemes l2 ON r.object_id = l2.id
            WHERE (l1.normalized_lemma = 'car' AND l2.normalized_lemma = 'carpet')
               OR (l1.normalized_lemma = 'carpet' AND l2.normalized_lemma = 'car')
               OR (l1.normalized_lemma = 'art' AND l2.normalized_lemma = 'article')
               OR (l1.normalized_lemma = 'article' AND l2.normalized_lemma = 'art');
        """)
        traps = self.cursor.fetchall()
        self.assertEqual(len(traps), 0, f"False-positive derivation detected: {traps}")

    def test_benchmark_inflections_present(self):
        """Benchmark Check: go -> went, mouse -> mice, run -> running."""
        benchmarks = [("go", "went"), ("mouse", "mice"), ("run", "running")]
        for lemma, surface in benchmarks:
            self.cursor.execute("""
                SELECT COUNT(*) 
                FROM resolved_relations r
                JOIN resolved_lexemes l ON r.subject_id = l.id
                JOIN resolved_forms f ON r.object_id = f.id
                WHERE r.relation_type = 'HAS_FORM' 
                  AND l.normalized_lemma = ? 
                  AND f.normalized_surface = ?;
            """, (lemma, surface))
            count = self.cursor.fetchone()[0]
            self.assertGreater(count, 0, f"Benchmark inflection pair ({lemma} -> {surface}) missing.")

if __name__ == "__main__":
    unittest.main()
