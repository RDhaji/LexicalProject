import json, os, pytest
from scripts.export_academic_interchange import export_ontolex_lemon

def test_academic_interchange_ontolex_lemon():
    db_path = "data/lexical_graph.db"
    out_path = "data/distribution/export_ontolex_lemon.jsonld"
    fixtures = ["run", "fast", "happy", "go", "good", "bad", "bank"]
    count = export_ontolex_lemon(db_path, out_path, fixture_lemmas=fixtures)
    assert count >= 7
    assert os.path.exists(out_path)
    with open(out_path) as f:
        data = json.load(f)
    assert "@graph" in data
    assert len(data["@graph"]) >= 7
    for entry in data["@graph"]:
        assert entry["@type"] == "ontolex:LexicalEntry"
        assert "ontolex:canonicalForm" in entry
        for form in entry.get("ontolex:lexicalForm", []):
            assert form["@type"] == "ontolex:Form"
            assert "lexical:epistemicClass" in form
