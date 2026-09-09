import json, os, sqlite3

def export_ontolex_lemon(db_path, output_path, fixture_lemmas=None):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    query = "SELECT id, lemma, pos FROM lexemes"
    params = ()
    if fixture_lemmas:
        placeholders = ",".join("?" for _ in fixture_lemmas)
        query += f" WHERE lemma IN ({placeholders})"
        params = tuple(fixture_lemmas)
    
    lex_rows = cur.execute(query, params).fetchall()
    entries = []
    for lid, lemma, pos in lex_rows:
        forms_rows = cur.execute(
            "SELECT f.id, f.form, e.epistemic_class "
            "FROM edges e JOIN forms f ON e.target_id = f.id "
            "WHERE e.source_id = ? AND e.relation_type = 'HAS_FORM'", (lid,)
        ).fetchall()
        form_nodes = [
            {
                "@id": f"urn:uuid:{fid}",
                "@type": "ontolex:Form",
                "ontolex:writtenRep": form,
                "lexical:epistemicClass": f_ep
            }
            for fid, form, f_ep in forms_rows
        ]
        entry = {
            "@id": f"urn:uuid:{lid}",
            "@type": "ontolex:LexicalEntry",
            "ontolex:canonicalForm": {
                "@type": "ontolex:Form",
                "ontolex:writtenRep": lemma
            },
            "lexical:partOfSpeech": pos,
            "ontolex:lexicalForm": form_nodes
        }
        entries.append(entry)
    
    doc = {
        "@context": {
            "ontolex": "http://www.w3.org/ns/lemon/ontolex#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "lexical": "https://lexicalproject.org/ontology#"
        },
        "@graph": entries
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(doc, f, indent=2)
    conn.close()
    return len(entries)

if __name__ == "__main__":
    db = "data/lexical_graph.db"
    out = "data/distribution/export_ontolex_lemon.jsonld"
    n = export_ontolex_lemon(db, out)
    print(f"EXPORT_ONTOLEX_LEMON_SUCCESS|entries={n}|dest={out}")
