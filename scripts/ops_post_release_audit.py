import sqlite3, sys, time, os

start = time.time()
FIXTURES = ("run", "fast", "happy", "go", "good", "bad", "bank")
EPISTEMIC = {"EXPLICIT", "GENERATED", "ATTESTED", "INFERRED", "UNCERTAIN"}

lg_path = next((p for p in ("data/distribution/lexical_graph.db", "data/lexical_graph.db", "lexical_graph.db") if os.path.exists(p) and os.path.getsize(p) > 32768), "lexical_graph.db")
uw_path = next((p for p in ("data/distribution/user_workspace.db", "data/user_workspace.db", "user_workspace.db") if os.path.exists(p)), "user_workspace.db")

lg_conn, uw_conn = sqlite3.connect(lg_path), sqlite3.connect(uw_path)
assert lg_conn.execute("PRAGMA integrity_check;").fetchone()[0] == "ok", "lexical_graph fail"
assert uw_conn.execute("PRAGMA integrity_check;").fetchone()[0] == "ok", "user_workspace fail"

# Invariant 7: Foreign key boundary verification
for (tbl,) in uw_conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall():
    for fk in uw_conn.execute(f"PRAGMA foreign_key_list({tbl});").fetchall():
        assert "lexical_graph" not in str(fk), f"Invariant 7 violation in {tbl}: {fk}"

# Invariant 6 & Gate A-G: Lexemes fixture validation
q = f"SELECT id, lemma, pos FROM lexemes WHERE lemma IN ({','.join('?' for _ in FIXTURES)})"
lex_rows = lg_conn.execute(q, FIXTURES).fetchall()
assert set(FIXTURES).issubset({r[1] for r in lex_rows}), "Missing fixtures"

# Invariants 2 & 3: Dynamic schema introspection for epistemic classification
found_epistemic = False
for (tbl,) in lg_conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall():
    cols = [c[1] for c in lg_conn.execute(f"PRAGMA table_info({tbl});").fetchall() if "epistemic" in c[1].lower()]
    for col in cols:
        found_epistemic = True
        for (val,) in lg_conn.execute(f"SELECT DISTINCT {col} FROM {tbl} WHERE {col} IS NOT NULL;").fetchall():
            assert val in EPISTEMIC, f"Invalid epistemic class {val} in {tbl}.{col}"

lg_conn.close()
uw_conn.close()
print(f"AUDIT_COMPLETE|db={lg_path}|fixtures={len(lex_rows)}|epistemic_verified={found_epistemic}|duration={time.time()-start:.2f}s")
