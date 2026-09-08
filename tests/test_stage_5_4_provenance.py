import os
import unittest

class TestStage54ProvenanceView(unittest.TestCase):

    def setUp(self):
        self.provenance_js = "/Users/rd/Desktop/LexicalProject/web/js/provenance_view.js"

    def test_provenance_inspector_contract(self):
        self.assertTrue(os.path.exists(self.provenance_js))
        with open(self.provenance_js, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("class ProvenanceInspector", content)
        self.assertIn("EPISTEMIC CLASS", content)
        self.assertIn("EXPLICIT", content)
        self.assertIn("UNCERTAIN", content)
        self.assertIn("Supporting Claims", content)

if __name__ == "__main__":
    unittest.main()
