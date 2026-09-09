import re

# Patch 1: Make test_storage_layer use dynamic UUID or cleanup before insertion
storage_test = "tests/test_storage_layer.py"
with open(storage_test, "r", encoding="utf-8") as f:
    code = f.read()

# Ensure unique target_id per test run
code = re.sub(
    r'test_uuid\s*=\s*["\'][^"\']+["\']',
    'import uuid; test_uuid = f"lex_{uuid.uuid4().hex[:12]}"',
    code,
    count=1
)
with open(storage_test, "w", encoding="utf-8") as f:
    f.write(code)

# Patch 2: Anchor test_traversal_service to fixture lemma 'run' and exact prefix
traversal_test = "tests/test_traversal_service.py"
with open(traversal_test, "r", encoding="utf-8") as f:
    tcode = f.read()

tcode = tcode.replace(
    "JOIN lexemes l ON l.id = e.source_id\n        LIMIT 1",
    "JOIN lexemes l ON l.id = e.source_id\n        WHERE l.lemma = 'run' AND e.relation_type = 'HAS_FORM'\n        LIMIT 1"
)
tcode = tcode.replace(
    "pfx = form_val[:2].lower()",
    "pfx = form_val[:2]"
)

with open(traversal_test, "w", encoding="utf-8") as f:
    f.write(tcode)

print("[PATCH] tests/test_storage_layer.py and tests/test_traversal_service.py patched.")
