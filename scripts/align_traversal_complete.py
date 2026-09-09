import sqlite3
import re

db_path = "data/distribution/lexical_graph.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
cur = conn.cursor()

# Get edges schema
cur.execute("PRAGMA table_info(edges);")
edge_cols = {row[1] for row in cur.fetchall()}

# Check provenance bridge tables if present
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = {row[0] for row in cur.fetchall()}
conn.close()

test_file = "tests/test_traversal_service.py"
with open(test_file, "r", encoding="utf-8") as f:
    code = f.read()

# Fix alias typos: 'FROM edges r' -> 'FROM edges e'
code = re.sub(r"FROM\s+edges\s+r\b", "FROM edges e", code)
code = re.sub(r"JOIN\s+edges\s+r\b", "JOIN edges e", code)

# Align edge endpoint column names based on actual DDL
head_col = "head_id" if "head_id" in edge_cols else ("source_id" if "source_id" in edge_cols else "subject_id")
tail_col = "tail_id" if "tail_id" in edge_cols else ("target_id" if "target_id" in edge_cols else "object_id")
rel_col = "relation_type" if "relation_type" in edge_cols else "relation"

code = re.sub(r"e\.(source_id|head_id|subject_id)", f"e.{head_col}", code)
code = re.sub(r"e\.(target_id|tail_id|object_id)", f"e.{tail_col}", code)
code = re.sub(r"e\.(relation_type|type|relation)", f"e.{rel_col}", code)

# Handle cases where edges table has no surrogate 'id' column (composite PK)
if "id" not in edge_cols:
    code = re.sub(r"SELECT\s+e\.id,\s*", f"SELECT e.{head_col}, ", code)
    code = re.sub(r"rc\.relation_id\s*=\s*e\.id", f"rc.head_id = e.{head_col} AND rc.tail_id = e.{tail_col}", code)

with open(test_file, "w", encoding="utf-8") as f:
    f.write(code)

print(f"[ALIGNED] tests/test_traversal_service.py: edges columns mapped -> {head_col}, {tail_col}, {rel_col} (composite id handled: {'id' not in edge_cols})")
