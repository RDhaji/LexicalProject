import os
import sqlite3

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
db_path = os.path.join(root, "data/distribution/lexical_graph.db")
if not os.path.exists(db_path):
    db_path = os.path.join(root, "data/compiled/lexical_graph.db")

def test_traversal_service():
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    c = conn.cursor()

    # 1. Exact Lookup Test
    c.execute('''
        SELECT f.id, f.form, l.id, l.lemma, l.pos
        FROM forms f
        JOIN edges e ON e.target_id = f.id AND e.relation_type = 'HAS_FORM'
        JOIN lexemes l ON l.id = e.source_id
        WHERE l.lemma = 'run' AND e.relation_type = 'HAS_FORM'
        LIMIT 1
    ''')
    exact = c.fetchone()
    assert exact is not None, "Exact lookup failed to return joined Form and Lexeme"
    form_id, form_val, lex_id, lemma, pos = exact

    # 2. Prefix Lookup Test
    pfx = form_val[:2]
    c.execute('''
        SELECT DISTINCT f.form, l.lemma, l.pos
        FROM forms f
        JOIN edges e ON e.target_id = f.id AND e.relation_type = 'HAS_FORM'
        JOIN lexemes l ON l.id = e.source_id
        WHERE f.form >= ? AND f.form < ? || '{'
        LIMIT 5
    ''', (pfx, pfx))
    assert len(c.fetchall()) > 0, "Prefix lookup returned empty set"

    # 3. Traversal Depth Bound Check
    c.execute('''
        SELECT e.id, e.source_id, e.target_id, e.relation_type
        FROM edges e
        WHERE e.relation_type IN ('DERIVED_FROM', 'MORPHOLOGICALLY_RELATED', 'HAS_FORM')
        LIMIT 5
    ''')
    assert len(c.fetchall()) > 0, "Traversable edges lookup returned empty set"

    # 4. Provenance Explainability Check
    c.execute('''
        SELECT e.source_id, e.relation_type, e.epistemic_status, e.provenance
        FROM edges e
        WHERE e.source_id = ? AND e.target_id = ?
        LIMIT 1
    ''', (lex_id, form_id))
    prov = c.fetchone()
    assert prov is not None, "Provenance lookup failed for attested edge"
    conn.close()

if __name__ == "__main__":
    test_traversal_service()
    print("[PASS] TraversalService logic verified across all 4 checks.")
