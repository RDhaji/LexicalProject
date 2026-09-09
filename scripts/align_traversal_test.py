import sqlite3
import os
import re

db_path = "data/distribution/lexical_graph.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
c = conn.cursor()
c.execute("PRAGMA table_info(edges);")
cols = [row[1] for row in c.fetchall()]
conn.close()

# Identify source/target or head/tail column naming
src_col = next((c for c in cols if c in ("source_id", "head_id", "subject_id")), None)
tgt_col = next((c for c in cols if c in ("target_id", "tail_id", "object_id")), None)
rel_col = next((c for c in cols if c in ("relation", "relation_type", "type")), None)

path = "tests/test_traversal_service.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

code = re.sub(r"e\.(object_id|target_id|tail_id)", f"e.{tgt_col}", code)
code = re.sub(r"e\.(subject_id|source_id|head_id)", f"e.{src_col}", code)
code = re.sub(r"e\.(relation_type|type|relation)", f"e.{rel_col}", code)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print(f"[ALIGNED] tests/test_traversal_service.py: edges schema mapped ({src_col}, {rel_col}, {tgt_col})")
