import os
import sys
import unittest
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.stage_8_compiler import SQLiteGraphCompiler

class TestStage8Compiler(unittest.TestCase):

    def setUp(self):
        self.compiler = SQLiteGraphCompiler()
        self.test_db = "/Users/rd/Desktop/LexicalProject/data/test_lexical_graph.db"
        os.makedirs(os.path.dirname(self.test_db), exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_compilation_and_indexing(self):
        lexemes = [
            {"id": "l1", "lemma": "run", "normalized_lemma": "run", "pos": "VERB"},
            {"id": "l2", "lemma": "runner", "normalized_lemma": "runner", "pos": "NOUN"}
        ]
        relations = [
            {"id": "r1", "subject_id": "l2", "subject_type": "LEXEME",
             "relation_type": "DERIVED_FROM", "object_id": "l1", "object_type": "LEXEME",
             "evidence_type": "EXPLICIT", "confidence": 1.0}
        ]

        self.compiler.compile_database(self.test_db, lexemes, relations)
        self.assertTrue(os.path.exists(self.test_db))

        conn = sqlite3.connect(self.test_db)
        cur = conn.cursor()

        # Check records
        cur.execute("SELECT count(*) FROM lexemes;")
        self.assertEqual(cur.fetchone()[0], 2)

        # Check FTS5 index
        cur.execute("SELECT lemma FROM lexemes_fts WHERE lexemes_fts MATCH 'run*';")
        matches = [r[0] for r in cur.fetchall()]
        self.assertIn("run", matches)
        self.assertIn("runner", matches)

        # Check covering index plan
        cur.execute("EXPLAIN QUERY PLAN SELECT object_id FROM relations WHERE subject_id = 'l2' AND relation_type = 'DERIVED_FROM';")
        plan = cur.fetchone()[3]
        self.assertIn("USING COVERING INDEX", plan)

        conn.close()

if __name__ == "__main__":
    unittest.main()
