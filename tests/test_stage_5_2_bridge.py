import os
import unittest

class TestStage52WorkerBridge(unittest.TestCase):

    def setUp(self):
        self.worker_path = "/Users/rd/Desktop/LexicalProject/web/js/worker.js"
        self.bridge_path = "/Users/rd/Desktop/LexicalProject/web/js/db_bridge.js"

    def test_worker_source_integrity(self):
        self.assertTrue(os.path.exists(self.worker_path))
        with open(self.worker_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("EXACT_LOOKUP", content)
        self.assertIn("TRAVERSE_GRAPH", content)
        self.assertIn("Math.min(params.depth || 1, 3)", content)  # Depth D <= 3 bound

    def test_bridge_rpc_interface(self):
        self.assertTrue(os.path.exists(self.bridge_path))
        with open(self.bridge_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("class LexicalDatabaseBridge", content)
        self.assertIn("exactLookup", content)
        self.assertIn("traverse", content)

if __name__ == "__main__":
    unittest.main()
