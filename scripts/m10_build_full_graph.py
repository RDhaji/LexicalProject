import sqlite3
import uuid
import time
import os

NAMESPACE_LEXEME = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
NAMESPACE_FORM = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
NAMESPACE_EDGE = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")

def gen_id(namespace, name):
    return str(uuid.uuid5(namespace, name))

def build_graph():
    start = time.time()
    out_dir = "data/distribution"
    os.makedirs(out_dir, exist_ok=True)
    db_path = os.path.join(out_dir, "lexical_graph.db")
    stg_path = "data/staging/staging_claims.db"

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("ATTACH DATABASE ? AS staging;", (stg_path,))

    cur.executescript("""
    PRAGMA journal_mode = OFF;
    PRAGMA synchronous = OFF;
    PRAGMA cache_size = -2000000;
    PRAGMA temp_store = MEMORY;

    CREATE TABLE lexemes (
        id TEXT PRIMARY KEY,
        lemma TEXT NOT NULL,
        pos TEXT NOT NULL,
        language TEXT NOT NULL DEFAULT 'eng'
    );

    CREATE TABLE forms (
        id TEXT PRIMARY KEY,
        form TEXT NOT NULL,
        language TEXT NOT NULL DEFAULT 'eng'
    );

    CREATE TABLE edges (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        epistemic_status TEXT NOT NULL,
        features TEXT,
        provenance TEXT NOT NULL
    );
    """)

    print("INFO | Materializing distinct Lexemes...")
    cur.execute("""
    SELECT DISTINCT lemma, LOWER(pos)
    FROM (
        SELECT lemma, pos FROM staging.staging_lexical_entries
        UNION
        SELECT lemma, pos FROM staging.staging_inflections
    ) WHERE lemma IS NOT NULL AND pos IS NOT NULL;
    """)
    lexemes_raw = cur.fetchall()
    lex_records = [(gen_id(NAMESPACE_LEXEME, f"{l.lower()}:{p}"), l, p, 'eng') for l, p in lexemes_raw]
    cur.executemany("INSERT OR IGNORE INTO lexemes (id, lemma, pos, language) VALUES (?, ?, ?, ?);", lex_records)
    conn.commit()
    print(f"INFO | Ingested {len(lex_records):,} lexemes.")

    print("INFO | Materializing distinct Forms...")
    cur.execute("SELECT DISTINCT form FROM staging.staging_inflections WHERE form IS NOT NULL;")
    forms_raw = cur.fetchall()
    form_records = [(gen_id(NAMESPACE_FORM, f.lower()), f, 'eng') for (f,) in forms_raw]
    cur.executemany("INSERT OR IGNORE INTO forms (id, form, language) VALUES (?, ?, ?);", form_records)
    conn.commit()
    print(f"INFO | Ingested {len(form_records):,} forms.")

    print("INFO | Materializing Inflection Edges (HAS_FORM)...")
    cur.execute("""
    SELECT DISTINCT lemma, LOWER(pos), form, features
    FROM staging.staging_inflections
    WHERE lemma IS NOT NULL AND form IS NOT NULL;
    """)
    infl_rows = cur.fetchall()
    edge_records = []
    for l, p, f, feat in infl_rows:
        src_id = gen_id(NAMESPACE_LEXEME, f"{l.lower()}:{p}")
        tgt_id = gen_id(NAMESPACE_FORM, f.lower())
        e_id = gen_id(NAMESPACE_EDGE, f"{src_id}:HAS_FORM:{tgt_id}:{feat}")
        edge_records.append((e_id, src_id, tgt_id, "HAS_FORM", "ATTESTED", feat, "UNIMORPH"))
        if len(edge_records) >= 50000:
            cur.executemany("INSERT OR IGNORE INTO edges VALUES (?, ?, ?, ?, ?, ?, ?);", edge_records)
            edge_records.clear()
    if edge_records:
        cur.executemany("INSERT OR IGNORE INTO edges VALUES (?, ?, ?, ?, ?, ?, ?);", edge_records)
        edge_records.clear()
    conn.commit()

    print("INFO | Materializing Semantic Edges (OEWN)...")
    cur.execute("""
    SELECT DISTINCT r.lemma, LOWER(r.pos), r.target_synset_id, r.relation_type
    FROM staging.staging_semantic_relations r
    WHERE r.target_synset_id IS NOT NULL AND r.lemma IS NOT NULL AND r.pos IS NOT NULL;
    """)
    sem_rows = cur.fetchall()
    for l, p, tgt_syn, rel in sem_rows:
        src_id = gen_id(NAMESPACE_LEXEME, f"{l.lower()}:{p}")
        e_id = gen_id(NAMESPACE_EDGE, f"{src_id}:{rel}:{tgt_syn}")
        edge_records.append((e_id, src_id, tgt_syn, rel, "EXPLICIT", None, "OEWN_2025"))
        if len(edge_records) >= 50000:
            cur.executemany("INSERT OR IGNORE INTO edges VALUES (?, ?, ?, ?, ?, ?, ?);", edge_records)
            edge_records.clear()
    if edge_records:
        cur.executemany("INSERT OR IGNORE INTO edges VALUES (?, ?, ?, ?, ?, ?, ?);", edge_records)

    print("INFO | Building production index coverage...")
    cur.executescript("""
    CREATE INDEX idx_lex_lemma ON lexemes(lemma);
    CREATE INDEX idx_forms_form ON forms(form);
    CREATE INDEX idx_edges_src ON edges(source_id);
    CREATE INDEX idx_edges_tgt ON edges(target_id);
    CREATE INDEX idx_edges_rel ON edges(relation_type);
    PRAGMA journal_mode = DELETE;
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM lexemes;")
    c_lex = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM forms;")
    c_forms = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM edges;")
    c_edges = cur.fetchone()[0]

    conn.close()
    duration = time.time() - start
    print(f"PASS | Distribution Graph Built: {c_lex:,} lexemes, {c_forms:,} forms, {c_edges:,} edges | Duration: {duration:.2f}s")

if __name__ == "__main__":
    build_graph()
