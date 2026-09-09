import sqlite3

def test_cross_lingual_vertical_fixtures():
    conn = sqlite3.connect("data/lexical_graph.db")
    cur = conn.cursor()
    assert cur.execute("SELECT COUNT(*) FROM lexemes_es").fetchone()[0] >= 7
    cols = {r[1] for r in cur.execute("PRAGMA table_info(edges)").fetchall()}
    ep_col = "epistemic_class" if "epistemic_class" in cols else "epistemic_status"
    trans_edges = cur.execute(
        f"SELECT e.source_id, e.target_id, e.{ep_col}, l.lemma, les.lemma "
        f"FROM edges e "
        f"JOIN lexemes l ON e.source_id = l.id "
        f"JOIN lexemes_es les ON e.target_id = les.id "
        f"WHERE e.relation_type = 'TRANSLATION_OF'"
    ).fetchall()
    assert len(trans_edges) >= 7
    for edge in trans_edges:
        assert edge[2] in ("ATTESTED", "EXPLICIT", "UNCERTAIN")
    form_cross_links = cur.execute(
        "SELECT COUNT(*) FROM edges WHERE relation_type = 'TRANSLATION_OF' AND ("
        "source_id IN (SELECT id FROM forms UNION SELECT id FROM forms_es) OR "
        "target_id IN (SELECT id FROM forms UNION SELECT id FROM forms_es))"
    ).fetchone()[0]
    assert form_cross_links == 0
    bank_edges = [e for e in trans_edges if e[3] == "bank"]
    assert len(bank_edges) > 0
    assert all(e[2] == "UNCERTAIN" for e in bank_edges)
    conn.close()
