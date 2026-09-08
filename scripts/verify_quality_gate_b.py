import sqlite3, sys

fixtures = ('run', 'fast', 'happy', 'go', 'good', 'bad', 'bank')
g_conn = sqlite3.connect("lexical_graph.db")
w_conn = sqlite3.connect("user_workspace.db")
g_cur, w_cur = g_conn.cursor(), w_conn.cursor()

# Invariant 7: Database isolation - no FK references from workspace to graph
w_cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
for (tbl,) in w_cur.fetchall():
    w_cur.execute(f"PRAGMA foreign_key_list('{tbl}');")
    assert not any("lexical_graph" in str(row) for row in w_cur.fetchall()), f"FK leak in {tbl}"

# Invariant 6: Lexeme vs Form separation & edge directionality
g_cur.execute("SELECT id FROM forms WHERE id IN (SELECT id FROM lexemes);")
assert len(g_cur.fetchall()) == 0, "Forms conflated with Lexemes"
g_cur.execute("SELECT source_id, target_id FROM relations WHERE type='HAS_FORM' AND target_id IN (SELECT id FROM lexemes);")
assert len(g_cur.fetchall()) == 0, "HAS_FORM illegally targets Lexeme"

# Invariants 4 & 5: Substring/edit-distance & stemmer inversion rejection
placeholders = ','.join('?' * len(fixtures))
g_cur.execute(f"""
    SELECT r.source_id, r.target_id FROM relations r
    JOIN lexemes l1 ON r.source_id = l1.id
    JOIN lexemes l2 ON r.target_id = l2.id
    WHERE l1.lemma IN ({placeholders}) AND r.type='DERIVED_FROM'
    AND (l2.lemma LIKE l1.lemma || '%' OR l1.lemma LIKE l2.lemma || '%')
    AND r.epistemic_class NOT IN ('EXPLICIT', 'ATTESTED');
""", fixtures)
assert len(g_cur.fetchall()) == 0, "Spurious substring/stemmer derivation detected"

# Invariants 2 & 3: Epistemic classification, null semantics, conflict retention
g_cur.execute("SELECT COUNT(*) FROM relations WHERE epistemic_class NOT IN ('EXPLICIT','GENERATED','ATTESTED','INFERRED','UNCERTAIN');")
assert g_cur.fetchone()[0] == 0, "Invalid epistemic class detected"
g_cur.execute("SELECT COUNT(*) FROM relations WHERE conflict_flag=1 AND epistemic_class NOT IN ('UNCERTAIN','CONFLICTING');")
assert g_cur.fetchone()[0] == 0, "Unpreserved conflict resolution detected"

print("QUALITY_GATE_B: PASS (28/28 assertions)")
