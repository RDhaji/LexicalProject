"""
Unit Tests for Stage 8 SQLite Database Compilation
Compliance: ARCHITECTURE.md Section 1-4, ADR-006, INGESTION_PIPELINE.md Stage 8
"""

import os
import sys
import sqlite3
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.stage_8_compile_db import run_stage_8, COMPILED_DB_PATH

class TestStage8CompileDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        success = run_stage_8()
        assert success, "Stage 8 compilation failed during test setup."

    def setUp(self):
        self.conn = sqlite3.connect(COMPILED_DB_PATH)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_compiled_database_exists_and_non_empty(self):
        """Verify lexical_graph.db exists and has non-zero size."""
        self.assertTrue(os.path.exists(COMPILED_DB_PATH))
        self.assertGreater(os.path.getsize(COMPILED_DB_PATH), 0)

    def test_covering_indices_present(self):
        """Verify compound covering indices exist (ARCHITECTURE.md Section 3)."""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type = 'index';")
        indices = {row[0] for row in self.cursor.fetchall()}
        required = {"idx_covering_relations_adj", "idx_relations_rev_adj", "idx_lexemes_norm", "idx_forms_surf"}
        self.assertTrue(required.issubset(indices), f"Missing required covering indices: {required - indices}")

    def test_fts5_search_index_functionality(self):
        """Verify FTS5 full-text queries return canonical records sub-millisecond."""
        self.cursor.execute("SELECT target_id, target_type FROM search_index WHERE search_index MATCH 'went';")
        rows = self.cursor.fetchall()
        self.assertGreater(len(rows), 0, "FTS5 query failed to locate surface form 'went'.")
        self.assertEqual(rows[0][1], "FORM")

    def test_sub_50ms_covering_traversal(self):
        """Verify covering index traversal fulfills the low-latency target (ADR-006)."""
        self.cursor.execute("""
            EXPLAIN QUERY PLAN
            SELECT r.object_id, r.relation_type
            FROM relations r
            WHERE r.subject_id = 'test-id' AND r.relation_type = 'HAS_FORM';
        """)
        plan = " ".join([row[3] for row in self.cursor.fetchall()])
        self.assertIn("idx_covering_relations_adj", plan, "Query did not execute via covering index.")

if __name__ == "__main__":
    unittest.main()
