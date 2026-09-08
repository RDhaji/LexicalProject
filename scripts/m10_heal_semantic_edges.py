import sqlite3
import uuid
import time

NAMESPACE_LEXEME = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

def gen_id(namespace, name):
    return str(uuid.uuid5(namespace, name))

def heal():
    t0 = time.time()
    db_path = "data/distribution/lexical_graph.db"
    stg_path = "data/staging/staging_claims.db"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("ATTACH DATABASE ? AS staging;", (stg_path,))

    cur.execute("""
    SELECT DISTINCT LOWER(sm_tgt.lemma), LOWER(sm_tgt.pos)
    FROM staging.staging_semantic_relations r
    JOIN staging.staging_semantic_relations sm_tgt 
        ON sm_tgt.synset_id = r.target_synset_id AND sm_tgt.relation_type = 'MEMBER'
    WHERE r.relation_type NOT IN ('SYNSET_DEF', 'MEMBER')
      AND sm_tgt.lemma IS NOT NULL AND sm_tgt.pos IS NOT NULL;
    """)
    target_lexemes = cur.fetchall()

    missing = [(gen_id(NAMESPACE_LEXEME, f"{lemma}:{pos}"), lemma, pos, 'eng') for lemma, pos in target_lexemes]
    cur.executemany("INSERT OR IGNORE INTO lexemes (id, lemma, pos, language) VALUES (?, ?, ?, ?);", missing)
    conn.commit()

    cur.execute("""
    DELETE FROM edges 
    WHERE relation_type != 'HAS_FORM' 
      AND (
        NOT EXISTS (SELECT 1 FROM lexemes WHERE lexemes.id = edges.source_id) OR 
        NOT EXISTS (SELECT 1 FROM lexemes WHERE lexemes.id = edges.target_id)
      );
    """)
    purged = cur.rowcount
    conn.commit()

    cur.execute("""
    SELECT COUNT(*) FROM edges 
    WHERE relation_type != 'HAS_FORM' 
      AND (
        NOT EXISTS (SELECT 1 FROM lexemes WHERE lexemes.id = edges.source_id) OR 
        NOT EXISTS (SELECT 1 FROM lexemes WHERE lexemes.id = edges.target_id)
      );
    """)
    dangling_remaining = cur.fetchone()[0]
    cur.execute("SELECT relation_type, COUNT(*) FROM edges GROUP BY relation_type;")
    dist = cur.fetchall()
    conn.close()

    print(f"PASS | Purged invalid: {purged} | Dangling remaining: {dangling_remaining} | Duration: {time.time() - t0:.2f}s")
    print(f"DISTRIBUTION: {dist}")

if __name__ == "__main__":
    heal()
