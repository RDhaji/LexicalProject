import sqlite3
import re

db_path = "data/distribution/lexical_graph.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
c = conn.cursor()
c.execute("PRAGMA table_info(edges);")
cols = [row[1] for row in c.fetchall()]
conn.close()

# Identify active column names in edges table
src = next((col for col in cols if col in ("head_id", "subject_id", "source_id")), "head_id")
tgt = next((col for col in cols if col in ("tail_id", "object_id", "target_id")), "tail_id")
rel = next((col for col in cols if col in ("relation_type", "type", "relation")), "relation_type")

path = "tests/test_traversal_service.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Replace any lingering alias mismatches (e.g., r.id -> e.id) and column variants
code = re.sub(r"\br\.id\b", "e.id", code)
code = re.sub(r"\be\.(head_id|subject_id|source_id)\b", f"e.{src}", code)
code = re.sub(r"\be\.(tail_id|object_id|target_id)\b", f"e.{tgt}", code)
code = re.sub(r"\be\.(relation_type|type|relation)\b", f"e.{rel}", code)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print(f"[ALIGNED] tests/test_traversal_service.py normalized with columns: id, {src}, {tgt}, {rel}")
