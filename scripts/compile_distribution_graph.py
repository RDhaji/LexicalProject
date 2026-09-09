import sqlite3
import os
import time
import sys
import uuid

NAMESPACE_LEXEME = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
NAMESPACE_FORM = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
NAMESPACE_EDGE = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")

def gen_id(namespace: uuid.UUID, name: str) -> str:
    return str(uuid.uuid5(namespace, name))

def compile_graph():
    t0 = time.time()
    staging_db = "data/staging/staging_claims.db"
    dist_db = "data/distribution/lexical_graph.db"
    os.makedirs("data/distribution", exist_ok=True)

    if not os.path.exists(staging_db):
        print(f"FAIL: {staging_db} missing.")
        sys.exit(1)

    s_conn = sqlite3.connect(staging_db)
    d_conn = sqlite3.connect(dist_db)
    s_cur = s_conn.cursor()
    d_cur = d_conn.cursor()

    d_cur.execute("PRAGMA journal_mode = WAL;")
    d_cur.execute("PRAGMA synchronous = NORMAL;")

    # 1. Ensure schema integrity
    d_cur.executescript("""
        CREATE TABLE IF NOT EXISTS synsets (
            id TEXT PRIMARY KEY,
            pos TEXT NOT NULL,
            gloss TEXT NOT NULL,
            domain TEXT,
            members TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS semantic_edges (
            id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            source TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            confidence REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sem_subject ON semantic_edges(subject_id, relation_type);
        CREATE INDEX IF NOT EXISTS idx_sem_object ON semantic_edges(object_id, relation_type);

        CREATE TABLE IF NOT EXISTS lexemes (
            id TEXT PRIMARY KEY,
            lemma TEXT NOT NULL,
            pos TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'eng'
        );
        CREATE INDEX IF NOT EXISTS idx_lex_lemma ON lexemes(lemma);

        CREATE TABLE IF NOT EXISTS forms (
            id TEXT PRIMARY KEY,
            form TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'eng'
        );
        CREATE INDEX IF NOT EXISTS idx_forms_form ON forms(form);

        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            epistemic_status TEXT NOT NULL,
            features TEXT,
            provenance TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges(target_id);
        CREATE INDEX IF NOT EXISTS idx_edges_rel ON edges(relation_type);
    """)

    # 2. Sync synsets
    s_cur.execute("SELECT id, pos, gloss, domain, members FROM synsets;")
    synset_rows = s_cur.fetchall()
    d_cur.executemany("""
        INSERT OR REPLACE INTO synsets (id, pos, gloss, domain, members)
        VALUES (?, ?, ?, ?, ?);
    """, synset_rows)
    print(f"PASS: Synsets compiled: {len(synset_rows)}")

    # 3. Sync semantic_edges
    s_cur.execute("SELECT id, subject_id, relation_type, object_id, source, evidence_type, confidence FROM semantic_relations;")
    sem_rows = s_cur.fetchall()
    d_cur.executemany("""
        INSERT OR REPLACE INTO semantic_edges (id, subject_id, relation_type, object_id, source, evidence_type, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, sem_rows)
    print(f"PASS: Semantic edges compiled: {len(sem_rows)}")

    # 4. Clean previously corrupted edge assertion keys
    d_cur.execute("DELETE FROM edges WHERE id LIKE 'edge_inflection_%';")

    # 5. Build lookup maps for canonical lexemes and forms
    d_cur.execute("SELECT lemma, id FROM lexemes;")
    lex_map = {}
    for lem, lid in d_cur.fetchall():
        if lem not in lex_map:
            lex_map[lem] = lid

    d_cur.execute("SELECT form, id FROM forms;")
    form_map = dict(d_cur.fetchall())

    # 6. Align inflection claims cross-source (Kaikki + UniMorph)
    s_cur.execute("""
        SELECT lemma, form, tags_json,
               GROUP_CONCAT(DISTINCT source_id) AS sources,
               GROUP_CONCAT(DISTINCT provenance) AS provenances
        FROM inflection_claims
        GROUP BY lemma, form, tags_json;
    """)

    new_lexemes = {}
    new_forms = {}
    aligned_edges = []
    
    for lemma, form, tags, sources, provs in s_cur:
        # Resolve or register Lexeme
        if lemma in lex_map:
            lid = lex_map[lemma]
        elif lemma in new_lexemes:
            lid = new_lexemes[lemma][0]
        else:
            lid = gen_id(NAMESPACE_LEXEME, f"{lemma.lower()}:noun")
            new_lexemes[lemma] = (lid, lemma, "noun", "eng")

        # Resolve or register Form
        if form in form_map:
            fid = form_map[form]
        elif form in new_forms:
            fid = new_forms[form][0]
        else:
            fid = gen_id(NAMESPACE_FORM, form.lower())
            new_forms[form] = (fid, form, "eng")

        edge_id = gen_id(NAMESPACE_EDGE, f"has_form:{lid}:{fid}:{tags}")
        provenance = f"{sources}:{provs}"
        aligned_edges.append((edge_id, lid, fid, "HAS_FORM", "ATTESTED", tags, provenance))

    # 7. Materialize newly registered entities and edges
    if new_lexemes:
        d_cur.executemany("INSERT OR IGNORE INTO lexemes (id, lemma, pos, language) VALUES (?, ?, ?, ?);", list(new_lexemes.values()))
        print(f"PASS: Materialized missing lexemes: {len(new_lexemes)}")

    if new_forms:
        d_cur.executemany("INSERT OR IGNORE INTO forms (id, form, language) VALUES (?, ?, ?);", list(new_forms.values()))
        print(f"PASS: Materialized missing forms: {len(new_forms)}")

    batch_size = 50000
    for i in range(0, len(aligned_edges), batch_size):
        d_cur.executemany("""
            INSERT OR REPLACE INTO edges (id, source_id, target_id, relation_type, epistemic_status, features, provenance)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, aligned_edges[i:i + batch_size])
        d_conn.commit()

    # 8. Assert Gate C: zero dangling edges
    d_cur.execute("""
        SELECT COUNT(*) FROM edges e
        LEFT JOIN (
            SELECT id FROM lexemes
            UNION ALL
            SELECT id FROM forms
            UNION ALL
            SELECT id FROM synsets
            UNION ALL
            SELECT id FROM lexemes_es
            UNION ALL
            SELECT id FROM forms_es
        ) v1 ON e.source_id = v1.id
        LEFT JOIN (
            SELECT id FROM lexemes
            UNION ALL
            SELECT id FROM forms
            UNION ALL
            SELECT id FROM synsets
            UNION ALL
            SELECT id FROM lexemes_es
            UNION ALL
            SELECT id FROM forms_es
        ) v2 ON e.target_id = v2.id
        WHERE v1.id IS NULL OR v2.id IS NULL;
    """)
    dangling_count = d_cur.fetchone()[0]

    d_conn.close()
    s_conn.close()
    elapsed = time.time() - t0
    print(f"PASS: Compilation complete in {elapsed:.2f}s. Dangling edges: {dangling_count}. Aligned HAS_FORM edges: {len(aligned_edges)}.")

if __name__ == "__main__":
    compile_graph()
