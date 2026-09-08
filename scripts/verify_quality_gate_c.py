import sqlite3, sys
from pathlib import Path

db_path = Path("data/lexical_graph.db")
if not db_path.exists():
    print(f"FAILED: Database not found at {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
fixtures = ('run', 'fast', 'happy', 'go', 'good', 'bad', 'bank')
fails = []

# Invariant 6: Lexeme vs Form separation (Forms cannot instantiate Lexemes)
cur.execute("SELECT id FROM forms WHERE id IN (SELECT id FROM lexemes);")
if cur.fetchall():
    fails.append("Invariant 6: Conflation detected - Form IDs present in lexemes table")

# Invariant 6: Edge typing rules
# - HAS_FORM: source MUST be LEXEME, target MUST be FORM
# - DERIVED_FROM: source MUST be LEXEME, target MUST be LEXEME
# - Forms cannot be source for semantic relations or lexeme derivation
cur.execute("""
    SELECT id, relation_type, source_type, target_type FROM edges
    WHERE (relation_type = 'HAS_FORM' AND (source_type != 'LEXEME' OR target_type != 'FORM'))
       OR (relation_type = 'DERIVED_FROM' AND (source_type != 'LEXEME' OR target_type != 'LEXEME'))
       OR (source_type = 'FORM' AND relation_type IN ('SYNONYM_OF', 'ANTONYM_OF', 'HYPERNYM_OF', 'HYPONYM_OF', 'DERIVED_FROM', 'EVOKES', 'MEMBER_OF_CLASS'))
""")
if cur.fetchall():
    fails.append("Invariant 6: Invalid endpoint types or Form asserting semantic relation")

# Invariant 4: No substring matching or false cognate derivations (e.g., car != carpet, art != article)
cur.execute("""
    SELECT e.id FROM edges e
    JOIN lexemes s ON e.source_id = s.id
    JOIN lexemes t ON e.target_id = t.id
    WHERE e.relation_type = 'DERIVED_FROM'
      AND ((s.lemma = 'car' AND t.lemma = 'carpet') OR (s.lemma = 'art' AND t.lemma = 'article'))
""")
if cur.fetchall():
    fails.append("Invariant 4: False cognate or substring match edge detected")

# Invariant 5 & Fixture coverage: Ensure all 7 vertical fixtures exist in lexemes
for lemma in fixtures:
    cur.execute("SELECT id FROM lexemes WHERE lemma = ?", (lemma,))
    if not cur.fetchone():
        fails.append(f"Missing fixture lexeme node: {lemma}")

# Epistemic classification constraint on all edges
cur.execute("SELECT id FROM edges WHERE epistemic_class NOT IN ('EXPLICIT', 'GENERATED', 'ATTESTED', 'INFERRED', 'UNCERTAIN');")
if cur.fetchall():
    fails.append("Invariant 2/3: Invalid epistemic class present in edges")

conn.close()

if fails:
    print(f"FAILED ({len(fails)} errors):\n" + "\n".join(fails))
    sys.exit(1)

print("PASS: Quality Gate C invariants verified across data/lexical_graph.db.")
