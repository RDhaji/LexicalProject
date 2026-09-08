import hashlib, json, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EPISTEMIC = {"EXPLICIT", "GENERATED", "ATTESTED", "INFERRED", "UNCERTAIN"}
FIXTURES = {"run", "fast", "happy", "go", "good", "bad", "bank"}

def run_checks():
    errors = []
    m_file = ROOT / "data" / "manifest.json"
    if m_file.exists():
        for p, exp in json.loads(m_file.read_text()).items():
            t = ROOT / p
            if not t.exists() or hashlib.sha256(t.read_bytes()).hexdigest() != exp:
                errors.append(f"Checksum mismatch: {p}")

    lex_db = ROOT / "data" / "lexical_graph.db"
    if lex_db.exists():
        with sqlite3.connect(lex_db) as conn:
            c = conn.cursor()
            tbls = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "edges" not in tbls:
                errors.append("Schema error: missing 'edges' table in lexical_graph.db")
            else:
                bad = c.execute("SELECT DISTINCT epistemic_class FROM edges WHERE epistemic_class NOT IN (?,?,?,?,?)", tuple(EPISTEMIC)).fetchall()
                if bad: errors.append(f"Invalid epistemic classes: {bad}")
                if c.execute("SELECT COUNT(*) FROM edges WHERE relation_type = 'HAS_FORM' AND target_type = 'LEXEME'").fetchone()[0] > 0:
                    errors.append("Invariant 6 violation: HAS_FORM points to LEXEME")
            if "lexemes" not in tbls:
                errors.append("Schema error: missing 'lexemes' table in lexical_graph.db")
            else:
                found = {r[0] for r in c.execute("SELECT lemma FROM lexemes WHERE lemma IN (?,?,?,?,?,?,?)", tuple(FIXTURES))}
                if len(found) < len(FIXTURES): errors.append(f"Missing vertical fixtures: {FIXTURES - found}")

    ws_db = ROOT / "data" / "user_workspace.db"
    if ws_db.exists():
        with sqlite3.connect(ws_db) as conn:
            tbls = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tbls:
                fks = conn.execute(f"PRAGMA foreign_key_list({t})").fetchall()
                if any("lexical" in str(fk).lower() for fk in fks):
                    errors.append(f"Invariant 7 violation: Cross-DB FK in table {t}")

    if errors:
        for e in errors: sys.stderr.write(f"[DRIFT FAIL] {e}\n")
        sys.exit(1)
    print(f"[DRIFT OK] All invariant, checksum, and isolation gates passed ({len(FIXTURES)} fixtures validated).")

if __name__ == "__main__":
    run_checks()
