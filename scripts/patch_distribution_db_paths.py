import re

for filepath in ["tests/test_client_integration.py", "tests/test_quality_gate_g.py"]:
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    # Point DB path to data/distribution/lexical_graph.db matching the 'Distribution DB' assertions
    code = code.replace(
        'os.path.join(PROJECT_ROOT, "data", "compiled", "lexical_graph.db")',
        'os.path.join(PROJECT_ROOT, "data", "distribution", "lexical_graph.db")'
    )
    code = code.replace(
        'os.path.join(PROJECT_ROOT, "data/compiled/lexical_graph.db")',
        'os.path.join(PROJECT_ROOT, "data/distribution/lexical_graph.db")'
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

print("[PATCH] Updated DB path to data/distribution/lexical_graph.db in integration and Gate G tests.")
