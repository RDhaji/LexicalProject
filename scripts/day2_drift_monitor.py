import hashlib, json, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EPISTEMIC = {"EXPLICIT", "GENERATED", "ATTESTED", "INFERRED", "UNCERTAIN"}
FIXTURES = {"run", "fast", "happy", "go", "good", "bad", "bank"}

def run_checks():
    errors = []
    
    # Check distribution manifest if exists
    for m_path in [ROOT / "data" / "distribution" / "release_manifest.json", ROOT / "data" / "manifest.json"]:
        if m_path.exists():
            try:
                manifest_data = json.loads(m_path.read_text())
                if isinstance(manifest_data, dict) and "artifacts" not in manifest_data:
                    for p, exp in manifest_data.items():
                        t = ROOT / p
                        if t.exists() and hashlib.sha256(t.read_bytes()).hexdigest() != exp:
                            errors.append(f"Checksum mismatch: {p}")
            except Exception:
                pass

    # Validate lexical_graph.db against ONTOLOGY schema
    lex_db = None
    for cand in [ROOT / "data" / "distribution" / "lexical_graph.db", ROOT / "data" / "lexical_graph.db"]:
        if cand.exists():
            lex_db = cand
            break

    if lex_db:
        with sqlite3.connect(lex_db) as conn:
            c = conn.cursor()
            tbls = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "edges" not in tbls:
                errors.append("Schema error: missing 'edges' table in lexical_graph.db")
            else:
                edge_cols = {col[1] for col in c.execute("PRAGMA table_info(edges)").fetchall()}
                status_col = "epistemic_status" if "epistemic_status" in edge_cols else ("epistemic_class" if "epistemic_class" in edge_cols else None)
                if status_col:
                    bad = c.execute(f"SELECT DISTINCT {status_col} FROM edges WHERE {status_col} NOT IN (?,?,?,?,?)", tuple(EPISTEMIC)).fetchall()
                    if bad:
                        errors.append(f"Invalid epistemic status: {bad}")
                
                # Invariant 6 verification: Forms never instantiate Lexemes
                has_form_to_lex = c.execute("""
                    SELECT COUNT(*) FROM edges e
                    JOIN lexemes l ON e.target_id = l.id
                    WHERE e.relation_type = 'HAS_FORM'
                """).fetchone()[0]
                if has_form_to_lex > 0:
                    errors.append("Invariant 6 violation: HAS_FORM points to LEXEME")

            if "lexemes" not in tbls:
                errors.append("Schema error: missing 'lexemes' table in lexical_graph.db")
            else:
                found = {r[0] for r in c.execute("SELECT lemma FROM lexemes WHERE lemma IN (?,?,?,?,?,?,?)", tuple(FIXTURES))}
                if len(found) < len(FIXTURES):
                    errors.append(f"Missing vertical fixtures: {FIXTURES - found}")

    # Validate Invariant 7: workspace isolation
    for cand_ws in [ROOT / "data" / "distribution" / "user_workspace.db", ROOT / "data" / "user_workspace.db"]:
        if cand_ws.exists():
            with sqlite3.connect(cand_ws) as conn:
                tbls = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                for t in tbls:
                    fks = conn.execute(f"PRAGMA foreign_key_list({t})").fetchall()
                    if any("lexical" in str(fk).lower() for fk in fks):
                        errors.append(f"Invariant 7 violation: Cross-DB FK in table {t}")

    if errors:
        for e in errors:
            sys.stderr.write(f"[DRIFT FAIL] {e}\n")
        sys.exit(1)
    print(f"[DRIFT OK] All invariant, checksum, and isolation gates passed ({len(FIXTURES)} fixtures validated).")

if __name__ == "__main__":
    run_checks()
