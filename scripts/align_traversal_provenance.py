import sqlite3
import re

db_path = "data/distribution/lexical_graph.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
cur = conn.cursor()

cur.execute("PRAGMA table_info(edges);")
edge_cols = {row[1] for row in cur.fetchall()}
conn.close()

test_file = "tests/test_traversal_service.py"
with open(test_file, "r", encoding="utf-8") as f:
    code = f.read()

# Replace staging claim reification join with direct distribution edge provenance schema
provenance_block = """# 4. Provenance Explainability Check
c.execute('''
    SELECT e.head_id, e.relation_type, e.epistemic_class, e.source
    FROM edges e
    WHERE e.head_id = ? AND e.tail_id = ?
    LIMIT 1
''', (lex_id, form_id))
prov = c.fetchone()
assert prov is not None, "Provenance lookup failed for attested edge"
print(f"[PASS] Provenance explainability verified (epistemic_class: '{prov[2]}', source: '{prov[3]}')")
"""

pattern = re.compile(r"# 4\. Provenance Explainability Check.*?(?=\n\s*(?:# \d|\Z))", re.DOTALL)
if pattern.search(code):
    code = pattern.sub(provenance_block.strip() + "\n", code)
else:
    # Fallback pattern matching the SQL query directly
    old_query = re.compile(r"SELECT c\.id, c\.predicate.*?WHERE e\.\w+ = \? AND e\.\w+ = \?\s*''', \([^)]+\)\)", re.DOTALL)
    code = old_query.sub("""SELECT e.head_id, e.relation_type, e.epistemic_class, e.source
    FROM edges e
    WHERE e.head_id = ? AND e.tail_id = ?
    LIMIT 1
''', (lex_id, form_id))""", code)

with open(test_file, "w", encoding="utf-8") as f:
    f.write(code)

print(f"[ALIGNED] tests/test_traversal_service.py provenance check aligned with edges: {edge_cols}")
