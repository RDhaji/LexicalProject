import sqlite3
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DB = ROOT / "data" / "distribution" / "lexical_graph.db"
STAGING_DB = ROOT / "data" / "staging" / "staging_claims.db"

NAMESPACE_FORM = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
NAMESPACE_EDGE = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")

def run():
    t0 = time.perf_counter()
    conn = sqlite3.connect(DIST_DB)
    cur = conn.cursor()
    cur.execute("ATTACH DATABASE ? AS staging;", (str(STAGING_DB),))
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")
    cur.execute("PRAGMA temp_store = MEMORY;")
    cur.execute("PRAGMA cache_size = -500000;")

    print("INFO | Identifying unlinked lexemes in distribution DB...")
    cur.execute("""
        CREATE TEMP TABLE missing_canonical_lexemes AS
        SELECT l.id AS lexeme_id, l.lemma, l.pos
        FROM lexemes l
        WHERE NOT EXISTS (
            SELECT 1 FROM edges e WHERE e.source_id = l.id
        );
    """)
    cur.execute("CREATE INDEX idx_tmp_missing ON missing_canonical_lexemes(lemma, pos);")
    missing_count = cur.execute("SELECT COUNT(*) FROM missing_canonical_lexemes;").fetchone()[0]
    print(f"INFO | Found {missing_count:,} lexemes lacking edges.")

    if missing_count == 0:
        print("INFO | No missing canonical forms to materialize.")
        conn.close()
        return

    print("INFO | Verifying source claims in staging_lexical_entries...")
    cur.execute("""
        CREATE TEMP TABLE verified_canonical_pairs AS
        SELECT DISTINCT m.lexeme_id, m.lemma, m.pos, sle.source
        FROM missing_canonical_lexemes m
        JOIN staging.staging_lexical_entries sle
          ON m.lemma = sle.lemma AND LOWER(m.pos) = LOWER(sle.pos);
    """)
    cur.execute("CREATE INDEX idx_tmp_ver_lemma ON verified_canonical_pairs(lemma);")
    verified_count = cur.execute("SELECT COUNT(*) FROM verified_canonical_pairs;").fetchone()[0]
    print(f"INFO | Verified {verified_count:,} canonical lemma claims.")

    print("INFO | Indexing existing forms in memory for case-sensitive anti-join...")
    cur.execute("CREATE TEMP TABLE existing_form_lookup (form TEXT PRIMARY KEY);")
    cur.execute("INSERT OR IGNORE INTO existing_form_lookup (form) SELECT form FROM forms;")

    print("INFO | Extracting genuinely missing canonical surface forms...")
    cur.execute("""
        CREATE TEMP TABLE missing_forms_to_insert AS
        SELECT DISTINCT v.lemma AS form
        FROM verified_canonical_pairs v
        LEFT JOIN existing_form_lookup ef ON ef.form = v.lemma
        WHERE ef.form IS NULL;
    """)

    missing_forms = [row[0] for row in cur.execute("SELECT form FROM missing_forms_to_insert;").fetchall()]
    print(f"INFO | Inserting {len(missing_forms):,} new surface forms into forms table...")
    
    form_batch = [(str(uuid.uuid5(NAMESPACE_FORM, f)), f, 'eng') for f in missing_forms]
    cur.executemany("INSERT OR IGNORE INTO forms (id, form, language) VALUES (?, ?, ?);", form_batch)
    conn.commit()

    print("INFO | Materializing canonical HAS_FORM edges via dedicated read cursor...")
    read_cur = conn.cursor()
    write_cur = conn.cursor()

    read_cur.execute("""
        SELECT v.lexeme_id, f.id, v.source
        FROM verified_canonical_pairs v
        JOIN forms f ON f.form = v.lemma;
    """)

    edge_batch = []
    inserted_edges = 0
    while True:
        rows = read_cur.fetchmany(50000)
        if not rows:
            break
        for lex_id, form_id, src in rows:
            prov = "KAIKKI_WIKTIONARY" if src == "KAIKKI" else src
            e_id = str(uuid.uuid5(NAMESPACE_EDGE, f"{lex_id}:HAS_FORM:{form_id}:CANONICAL"))
            edge_batch.append((e_id, lex_id, form_id, "HAS_FORM", "ATTESTED", "CANONICAL", prov))
        write_cur.executemany("INSERT OR IGNORE INTO edges VALUES (?, ?, ?, ?, ?, ?, ?);", edge_batch)
        inserted_edges += len(edge_batch)
        conn.commit()
        edge_batch.clear()

    final_lex = cur.execute("SELECT COUNT(*) FROM lexemes;").fetchone()[0]
    final_forms = cur.execute("SELECT COUNT(*) FROM forms;").fetchone()[0]
    final_edges = cur.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]
    conn.close()

    duration = time.perf_counter() - t0
    print(f"MATERIALIZATION_SUCCESS | Duration: {duration:.2f}s | Lexemes: {final_lex:,} | Forms: {final_forms:,} | Edges: {final_edges:,} | New Edges Added: {inserted_edges:,}")

if __name__ == "__main__":
    run()
