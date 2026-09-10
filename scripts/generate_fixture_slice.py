import sqlite3
import os

src_path = "data/distribution/lexical_graph.db"
dst_path = "data/distribution/fixture_slice.db"

if os.path.exists(dst_path):
    os.remove(dst_path)

s = sqlite3.connect(src_path)
d = sqlite3.connect(dst_path)

# 1. Replicate exact schema and indexes
tables = ["lexemes", "forms", "edges", "pronunciations", "search_phonetic_index"]
for t in tables:
    for row in s.execute("SELECT sql FROM sqlite_master WHERE tbl_name=? AND sql IS NOT NULL", (t,)).fetchall():
        d.execute(row[0])

# 2. Slice 7 canonical vertical fixtures
fixtures = ["run", "fast", "happy", "go", "good", "bad", "bank"]
q_fix = ",".join("?" for _ in fixtures)
lexemes = s.execute(f"SELECT * FROM lexemes WHERE lemma IN ({q_fix})", fixtures).fetchall()
q_lex_placeholders = ",".join("?" for _ in lexemes[0])
d.executemany(f"INSERT INTO lexemes VALUES ({q_lex_placeholders})", lexemes)
lex_ids = list({r[0] for r in lexemes})

# 3. Pull associated forms connected via HAS_FORM
q_lex = ",".join("?" for _ in lex_ids)
form_edges = s.execute(f"SELECT target_id FROM edges WHERE source_id IN ({q_lex}) AND relation_type='HAS_FORM'", lex_ids).fetchall()
form_ids = list({r[0] for r in form_edges})

if form_ids:
    q_forms = ",".join("?" for _ in form_ids)
    forms = s.execute(f"SELECT * FROM forms WHERE id IN ({q_forms})", form_ids).fetchall()
    if forms:
        q_forms_placeholders = ",".join("?" for _ in forms[0])
        d.executemany(f"INSERT INTO forms VALUES ({q_forms_placeholders})", forms)

valid_entity_ids = list(set(lex_ids).union(set(form_ids)))
q_valid = ",".join("?" for _ in valid_entity_ids)

# 4. Zero Dangling Edges (Gate C): strictly intra-slice endpoints
edges = s.execute(
    f"SELECT * FROM edges WHERE source_id IN ({q_valid}) AND target_id IN ({q_valid})",
    valid_entity_ids + valid_entity_ids
).fetchall()
if edges:
    q_edge_placeholders = ",".join("?" for _ in edges[0])
    d.executemany(f"INSERT INTO edges VALUES ({q_edge_placeholders})", edges)

# 5. Populate pronunciations
prons = s.execute(f"SELECT * FROM pronunciations WHERE target_id IN ({q_valid})", valid_entity_ids).fetchall()
if prons:
    q_pron_placeholders = ",".join("?" for _ in prons[0])
    d.executemany(f"INSERT INTO pronunciations VALUES ({q_pron_placeholders})", prons)

# 6. Populate search_phonetic_index (matching target_id schema)
phonetics = s.execute(f"SELECT * FROM search_phonetic_index WHERE target_id IN ({q_valid})", valid_entity_ids).fetchall()
if phonetics:
    q_phone_placeholders = ",".join("?" for _ in phonetics[0])
    d.executemany(f"INSERT INTO search_phonetic_index VALUES ({q_phone_placeholders})", phonetics)

d.commit()

counts = {t: d.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}
s.close()
d.close()
print("SLICE_GENERATION_COMPLETE:", counts)
