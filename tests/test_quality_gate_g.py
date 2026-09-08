"""
Quality Gate G: Performance Bounds Verification Suite
Compliance: PRD.md Section 9 (Gate G), ARCHITECTURE.md Section 4

Invariant:
All graph queries (Depth D <= 3) must execute in < 250ms across all benchmark fixture seeds:
['run', 'fast', 'happy', 'go', 'good', 'bad', 'bank'].
"""

import os
import sqlite3
import sys
import time
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

COMPILED_DB_PATH = os.path.join(PROJECT_ROOT, "data", "compiled", "lexical_graph.db")


class TestQualityGateG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(COMPILED_DB_PATH):
            raise unittest.SkipTest(f"Distribution DB not found at: {COMPILED_DB_PATH}")
        cls.conn = sqlite3.connect(f"file:{COMPILED_DB_PATH}?mode=ro", uri=True)
        cls.conn.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn"):
            cls.conn.close()

    def test_benchmark_seeds_depth_3_performance_bounds(self):
        """Verify graph traversal (D <= 3) completes under 250ms SLA for all benchmark seeds."""
        benchmark_seeds = ["run", "fast", "happy", "go", "good", "bad", "bank"]
        cursor = self.conn.cursor()

        for seed in benchmark_seeds:
            cursor.execute("SELECT id FROM lexemes WHERE lemma = ? LIMIT 1;", (seed,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, f"Benchmark seed '{seed}' missing from database")
            root_id = row["id"]

            t0 = time.perf_counter()

            # Depth 1
            cursor.execute(
                "SELECT target_id, relation_type FROM edges WHERE source_id = ?;",
                (root_id,),
            )
            d1_rows = cursor.fetchall()
            d1_ids = list({r["target_id"] for r in d1_rows})

            # Depth 2
            d2_ids = []
            if d1_ids:
                placeholders = ",".join(["?"] * len(d1_ids))
                cursor.execute(
                    f"SELECT target_id, relation_type FROM edges WHERE source_id IN ({placeholders});",
                    d1_ids,
                )
                d2_rows = cursor.fetchall()
                d2_ids = list({r["target_id"] for r in d2_rows})

            # Depth 3
            if d2_ids:
                placeholders = ",".join(["?"] * len(d2_ids))
                cursor.execute(
                    f"SELECT target_id, relation_type FROM edges WHERE source_id IN ({placeholders});",
                    d2_ids,
                )
                cursor.fetchall()

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.assertLess(
                elapsed_ms,
                250.0,
                f"Gate G violation on seed '{seed}': {elapsed_ms:.2f}ms exceeds 250ms threshold",
            )


if __name__ == "__main__":
    unittest.main()
