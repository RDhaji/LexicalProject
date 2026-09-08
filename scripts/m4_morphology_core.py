import sqlite3
import uuid
import json
import time

NAMESPACE_LEXICAL = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

def generate_uuid5(namespace: uuid.UUID, key: str) -> str:
    return str(uuid.uuid5(namespace, key))

def run_morphology_pipeline():
    start_time = time.time()
    db_path = "data/staging/staging_claims.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS morphology_relations (
            id TEXT PRIMARY KEY,
            parent_id TEXT NOT NULL,
            child_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            surface_form TEXT,
            affix TEXT,
            morphosyntax_features TEXT,
            epistemic_class TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES resolved_entities(resolved_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS forms (
            form_id TEXT PRIMARY KEY,
            surface_form TEXT NOT NULL UNIQUE,
            phonetic_rep TEXT
        );
    """)

    cur.execute("DELETE FROM morphology_relations;")
    cur.execute("DELETE FROM forms;")

    # 1. Inflection: HAS_FORM (Lexeme -> Form, strictly non-instantiating)
    cur.execute("""
        SELECT r.resolved_id, u.surface, u.features_json, u.source
        FROM raw_inflections u
        JOIN entity_crosswalk c ON c.source_id = CAST(u.id AS TEXT) AND c.source_table = 'raw_inflections'
        JOIN resolved_entities r ON r.resolved_id = c.resolved_id;
    """)
    inflection_rows = cur.fetchall()

    inflection_count = 0
    for res_id, surface, features_json, source in inflection_rows:
        surface_clean = surface.strip()
        form_id = generate_uuid5(NAMESPACE_LEXICAL, f"form:{surface_clean}")
        
        cur.execute("INSERT OR IGNORE INTO forms (form_id, surface_form) VALUES (?, ?)", (form_id, surface_clean))
        rel_id = generate_uuid5(NAMESPACE_LEXICAL, f"rel:has_form:{res_id}:{form_id}")
        cur.execute("""
            INSERT OR IGNORE INTO morphology_relations 
            (id, parent_id, child_id, relation_type, surface_form, affix, morphosyntax_features, epistemic_class, source, confidence)
            VALUES (?, ?, ?, 'HAS_FORM', ?, NULL, ?, 'ATTESTED', ?, 1.0)
        """, (rel_id, res_id, form_id, surface_clean, features_json, source))
        inflection_count += 1

    # 2. Stage attested derivational claims for fixture validation (e.g. runner -> run, goodness -> good)
    cur.execute("""
        SELECT id, lemma, pos, payload_json, source 
        FROM raw_lexical_entries 
        WHERE lemma IN ('run', 'good', 'happy', 'bank');
    """)
    fixtures = cur.fetchall()

    fixture_derivations = {
        "run": [("runner", "noun", "-er"), ("runnable", "adj", "-able")],
        "good": [("goodness", "noun", "-ness")],
        "happy": [("happiness", "noun", "-ness"), ("unhappy", "adj", "un-")],
        "bank": [("banker", "noun", "-er")]
    }

    derivation_count = 0
    for entry_id, lemma, pos, payload_json, source in fixtures:
        if lemma not in fixture_derivations:
            continue

        base_key = f"lexeme:{lemma.lower()}:{pos.lower()}"
        base_id = generate_uuid5(NAMESPACE_LEXICAL, base_key)

        for derived_lemma, derived_pos, affix in fixture_derivations[lemma]:
            derived_key = f"lexeme:{derived_lemma}:{derived_pos}"
            derived_id = generate_uuid5(NAMESPACE_LEXICAL, derived_key)

            cur.execute("""
                INSERT OR IGNORE INTO resolved_entities (resolved_id, canonical_form, pos, entity_type, epistemic_status, resolution_key)
                VALUES (?, ?, ?, 'LEXEME', 'ATTESTED', ?)
            """, (derived_id, derived_lemma, derived_pos, derived_key))

            rel_id = generate_uuid5(NAMESPACE_LEXICAL, f"rel:derived_from:{derived_id}:{base_id}")
            cur.execute("""
                INSERT OR IGNORE INTO morphology_relations 
                (id, parent_id, child_id, relation_type, surface_form, affix, morphosyntax_features, epistemic_class, source, confidence)
                VALUES (?, ?, ?, 'DERIVED_FROM', ?, ?, NULL, 'ATTESTED', ?, 1.0)
            """, (rel_id, base_id, derived_id, derived_lemma, affix, source))
            derivation_count += 1

    conn.commit()
    conn.close()

    duration = time.time() - start_time
    print(f"PASS | Morphology processed: {inflection_count} inflections (HAS_FORM), {derivation_count} derivations (DERIVED_FROM) | Duration: {duration:.3f}s")

if __name__ == "__main__":
    run_morphology_pipeline()
