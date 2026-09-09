import re

path = "tests/test_traversal_service.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace("f.normalized_surface", "f.form")
code = code.replace("f.surface", "f.form")
code = code.replace("JOIN relations r", "JOIN edges e")
code = code.replace("JOIN edges r", "JOIN edges e")
code = code.replace("r.object_id", "e.object_id")
code = code.replace("r.subject_id", "e.subject_id")
code = code.replace("r.relation_type", "e.relation_type")

code = re.sub(
    r"form_id,\s*surface,\s*norm_surface,\s*lex_id,\s*lemma,\s*pos\s*=\s*exact",
    "form_id, form_val, lex_id, lemma, pos = exact",
    code
)
code = code.replace("{norm_surface[:2]}", "{form_val[:2]}")
code = code.replace("norm_surface[:2]", "form_val[:2]")
code = code.replace("form '{surface}'", "form '{form_val}'")

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("[PATCH] tests/test_traversal_service.py updated successfully.")
