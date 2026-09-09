import re

path = "tests/test_traversal_service.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Normalize columns in section 4 to match distribution schema
code = re.sub(
    r"SELECT\s+e\.source_id,\s*e\.relation_type,\s*e\.\w+,\s*e\.\w+",
    "SELECT e.source_id, e.relation_type, e.epistemic_status, e.provenance",
    code
)
code = code.replace("e.epistemic_class", "e.epistemic_status")
code = code.replace("e.source", "e.provenance")
code = code.replace("epistemic_class:", "epistemic_status:")

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("[PATCH] tests/test_traversal_service.py aligned to edges schema.")
