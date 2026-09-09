"""
End-to-End Client Traversal & Latency Integration Test
Compliance: ARCHITECTURE.md Section 4, ADR-006
"""

import os
import sqlite3
import sys
import time
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

COMPILED_DB_PATH = os.path.join(PROJECT_ROOT, "data", "distribution", "lexical_graph.db")

class TestClientIntegration(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.exists(COMPILED_DB_PATH), "Distribution DB missing")
        self.conn = sqlite3.connect(f"file:{COMPILED_DB_PATH}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()

    def test_client_assets_exist(self):
        """Verify all PWA assets are present with non-zero size."""
        assets = ["client/index.html", "client/sw.js", "client/db_client.js", "client/worker.js"]
        for a in assets:
            path = os.path.join(PROJECT_ROOT, a)
            self.assertTrue(os.path.exists(path) and os.path.getsize(path) > 0, f"Asset missing: {a}")

    def test_exact_lookup_latency(self):
        """Invariant: Exact match lookup must execute under 50ms."""
        cursor = self.conn.cursor()
        t0 = time.perf_counter()
        cursor.execute("SELECT id, lemma, pos FROM lexemes WHERE lemma = 'go';")
        rows = cursor.fetchall()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertGreater(len(rows), 0, "No records returned for 'go'")
        self.assertLess(elapsed_ms, 50.0, f"Lookup exceeded 50ms threshold: {elapsed_ms:.2f}ms")

    def test_bounded_graph_expansion_latency(self):
        """Invariant ARCHITECTURE.md §4: Bounded expansion (D <= 3) must execute under 250ms."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM lexemes WHERE lemma = 'go' LIMIT 1;")
        root_id = cursor.fetchone()["id"]

        t0 = time.perf_counter()
        # Depth 1
        cursor.execute("""
            SELECT e.target_id, e.relation_type FROM edges e WHERE e.source_id = ?
        """, (root_id,))
        depth1 = cursor.fetchall()

        # Depth 2
        depth1_ids = [row["target_id"] for row in depth1]
        depth2 = []
        if depth1_ids:
            placeholders = ",".join(["?"] * len(depth1_ids))
            cursor.execute(f"""
                SELECT e.target_id, e.relation_type 
                FROM edges e 
                WHERE e.source_id IN ({placeholders})
            """, depth1_ids)
            depth2 = cursor.fetchall()

        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(elapsed_ms, 250.0, f"Traversal exceeded 250ms bound: {elapsed_ms:.2f}ms")

if __name__ == "__main__":
    unittest.main()
