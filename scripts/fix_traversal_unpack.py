import re

path = "tests/test_traversal_service.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Normalize SELECT clause to exact 5 columns matching (f.id, f.form, l.id, l.lemma, l.pos)
code = re.sub(
    r"SELECT\s+f\.id,\s*f\.form,(\s*f\.\w+,)?\s*l\.id,\s*l\.lemma,\s*l\.pos",
    "SELECT f.id, f.form, l.id, l.lemma, l.pos",
    code,
    flags=re.MULTILINE
)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("[FIX] Traversal test SELECT statement normalized to 5 columns.")
