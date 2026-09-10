import os
import unittest

class TestStage53VisualizerViews(unittest.TestCase):

    def setUp(self):
        self.graph_js = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "js", "graph_view.js"))
        self.paradigm_js = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "js", "paradigm_view.js"))

    def test_view_components_exist(self):
        self.assertTrue(os.path.exists(self.graph_js))
        self.assertTrue(os.path.exists(self.paradigm_js))

    def test_graph_renderer_contract(self):
        with open(self.graph_js, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("class LexicalGraphVisualizer", content)
        self.assertIn("createElementNS", content)
        self.assertIn("LEXEME", content)

    def test_paradigm_inspector_contract(self):
        with open(self.paradigm_js, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("class ParadigmInspector", content)
        self.assertIn("Surface", content)
        self.assertIn("Features", content)

if __name__ == "__main__":
    unittest.main()
