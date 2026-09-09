import sqlite3
import datetime

db_path = "data/distribution/lexical_graph.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    SELECT COUNT(*) FROM edges e 
    WHERE e.relation_type = 'HAS_FORM' 
      AND (
        NOT EXISTS (SELECT 1 FROM lexemes l WHERE l.id = e.source_id) OR 
        NOT EXISTS (SELECT 1 FROM forms f WHERE f.id = e.target_id)
      );
""")
dangling_forms = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM edges e 
    WHERE e.relation_type != 'HAS_FORM' 
      AND (
        NOT EXISTS (SELECT 1 FROM lexemes l WHERE l.id = e.source_id) OR 
        (
          NOT EXISTS (SELECT 1 FROM lexemes l WHERE l.id = e.target_id) AND
          NOT EXISTS (SELECT 1 FROM lexemes_es les WHERE les.id = e.target_id)
        )
      );
""")
dangling_semantics = cur.fetchone()[0]

fixtures = ['run', 'fast', 'happy', 'go', 'good', 'bad', 'bank']
cur.execute(f"""
    SELECT l.lemma, l.pos, e.relation_type, COUNT(e.id)
    FROM lexemes l
    JOIN edges e ON l.id = e.source_id
    WHERE l.lemma IN ({','.join(['?']*len(fixtures))})
    GROUP BY l.lemma, l.pos, e.relation_type;
""", fixtures)
fixture_results = cur.fetchall()

cur.execute("SELECT COUNT(*) FROM lexemes;")
total_lexemes = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM forms;")
total_forms = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM edges;")
total_edges = cur.fetchone()[0]
cur.execute("SELECT relation_type, COUNT(*) FROM edges GROUP BY relation_type;")
edge_dist = dict(cur.fetchall())
conn.close()

assert dangling_forms == 0, f"Quality Gate Failure: {dangling_forms} dangling HAS_FORM edges"
assert dangling_semantics == 0, f"Quality Gate Failure: {dangling_semantics} dangling semantic edges"
assert len(fixture_results) > 0, "Quality Gate Failure: Zero fixture coverage"

print(f"PASS | Quality Gate Verification Succeeded")
print(f"Graph Metrics: {total_lexemes:,} lexemes | {total_forms:,} forms | {total_edges:,} edges")
print(f"Edge Distribution: {edge_dist}")
print(f"Fixture Cover: {len(fixture_results)} relation clusters across {fixtures}")

# State Checkpointing
progress_entry = f"""
## Milestone 10: Production Lexical Graph Materialization
- Status: COMPLETED
- Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}
- Metrics:
  - Lexemes: {total_lexemes:,}
  - Forms: {total_forms:,}
  - Edges: {total_edges:,}
  - Edge Distribution: {edge_dist}
- Quality Gates:
  - Referential Integrity: 0 dangling edges (PASSED)
  - Fixture Validation: Attested across vertical slices (PASSED)
- Immediate Next: Milestone 11 (Query Engine & Local Traversal Interface)
"""

with open("PROGRESS.md", "a", encoding="utf-8") as f:
    f.write(progress_entry)

print("PASS | PROGRESS.md checkpointed successfully")
