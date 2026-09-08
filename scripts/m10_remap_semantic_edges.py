import sqlite3
import uuid
import time

NAMESPACE_LEXEME = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
NAMESPACE_EDGE = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")

def gen_id(namespace, name):
    return str(uuid.uuid5(namespace, name))

def remap_edges():
    t0 = time.time()
    db_path = "data/distribution/lexical_graph.db"
    stg_path = "data/staging/staging_claims.db"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("ATTACH DATABASE ? AS staging;", (stg_path,))

    print("INFO | Joining OEWN semantic relations via synset members...")
    cur.execute("""
    SELECT DISTINCT 
        LOWER(sm_src.lemma), LOWER(sm_src.pos),
        LOWER(sm_tgt.lemma), LOWER(sm_tgt.pos),
        r.relation_type
    FROM staging.staging_semantic_relations r
    JOIN staging.staging_semantic_relations sm_src 
        ON sm_src.synset_id = r.synset_id AND sm_src.relation_type = 'MEMBER'
    JOIN staging.staging_semantic_relations sm_tgt 
        ON sm_tgt.synset_id = r.target_synset_id AND sm_tgt.relation_type = 'MEMBER'
    WHERE r.relation_type NOT IN ('SYNSET_DEF', 'MEMBER')
      AND sm_src.lemma IS NOT NULL AND sm_tgt.lemma IS NOT NULL;
    """)

    batch = []
    total = 0
    while True:
        rows = cur.fetchmany(50000)
        if not rows:
            break
        for src_l, src_p, tgt_l, tgt_p, rel in rows:
            src_id = gen_id(NAMESPACE_LEXEME, f"{src_l}:{src_p}")
            tgt_id = gen_id(NAMESPACE_LEXEME, f"{tgt_l}:{tgt_p}")
            edge_id = gen_id(NAMESPACE_EDGE, f"{src_id}:{rel}:{tgt_id}")
            batch.append((edge_id, src_id, tgt_id, rel, "EXPLICIT", None, "OEWN_2025"))

        cur.executemany("INSERT OR IGNORE INTO edges VALUES (?, ?, ?, ?, ?, ?, ?);", batch)
        total += len(batch)
        batch.clear()

    conn.commit()
    cur.execute("SELECT relation_type, COUNT(*) FROM edges GROUP BY relation_type;")
    dist = cur.fetchall()
    conn.close()

    print(f"PASS | Semantic Edges Remapped: {total:,} considered | Duration: {time.time() - t0:.2f}s")
    print(f"DISTRIBUTION: {dist}")

if __name__ == "__main__":
    remap_edges()
