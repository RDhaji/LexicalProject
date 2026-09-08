import sqlite3
import os
import time

def compile_graph():
    start_time = time.time()
    staging_db = "data/staging/staging_claims.db"
    dist_dir = "data/distribution"
    dist_db = os.path.join(dist_dir, "lexical_graph.db")

    os.makedirs(dist_dir, exist_ok=True)
    if os.path.exists(dist_db):
        os.remove(dist_db)

    conn_stage = sqlite3.connect(staging_db)
    conn_dist = sqlite3.connect(dist_db)
    cur_stage = conn_stage.cursor()
    cur_dist = conn_dist.cursor()

    cur_dist.execute("PRAGMA journal_mode = OFF;")
    cur_dist.execute("PRAGMA synchronous = 0;")
    cur_dist.execute("PRAGMA page_size = 4096;")

    # 1. Target Read-Optimized Schema
    cur_dist.executescript("""
        CREATE TABLE lexemes (
            id TEXT PRIMARY KEY,
            canonical_form TEXT NOT NULL,
            pos TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            epistemic_status TEXT NOT NULL
        );

        CREATE TABLE forms (
            id TEXT PRIMARY KEY,
            surface_form TEXT NOT NULL UNIQUE
        );

        CREATE TABLE synsets (
            id TEXT PRIMARY KEY,
            pos TEXT NOT NULL,
            gloss TEXT NOT NULL,
            domain TEXT,
            members TEXT NOT NULL
        );

        CREATE TABLE morphology_edges (
            id TEXT PRIMARY KEY,
            parent_id TEXT NOT NULL,
            child_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            surface_form TEXT,
            affix TEXT,
            morphosyntax_features TEXT,
            epistemic_class TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL NOT NULL
        );

        CREATE TABLE semantic_edges (
            id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            source TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            confidence REAL NOT NULL
        );

        CREATE TABLE entity_crosswalk (
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            resolved_id TEXT NOT NULL,
            epistemic_status TEXT NOT NULL,
            PRIMARY KEY (source_table, source_id, resolved_id)
        );
    """)

    # 2. Bulk Migration
    cur_stage.execute("SELECT resolved_id, canonical_form, pos, entity_type, epistemic_status FROM resolved_entities;")
    cur_dist.executemany("INSERT INTO lexemes VALUES (?, ?, ?, ?, ?);", cur_stage.fetchall())

    cur_stage.execute("SELECT form_id, surface_form FROM forms;")
    cur_dist.executemany("INSERT INTO forms VALUES (?, ?);", cur_stage.fetchall())

    cur_stage.execute("SELECT id, pos, gloss, domain, members FROM synsets;")
    cur_dist.executemany("INSERT INTO synsets VALUES (?, ?, ?, ?, ?);", cur_stage.fetchall())

    cur_stage.execute("""
        SELECT id, parent_id, child_id, relation_type, surface_form, affix, morphosyntax_features, epistemic_class, source, confidence 
        FROM morphology_relations;
    """)
    cur_dist.executemany("INSERT INTO morphology_edges VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", cur_stage.fetchall())

    cur_stage.execute("SELECT id, subject_id, relation_type, object_id, source, evidence_type, confidence FROM semantic_relations;")
    cur_dist.executemany("INSERT INTO semantic_edges VALUES (?, ?, ?, ?, ?, ?, ?);", cur_stage.fetchall())

    cur_stage.execute("SELECT source_table, source_id, resolved_id, epistemic_status FROM entity_crosswalk;")
    cur_dist.executemany("INSERT INTO entity_crosswalk VALUES (?, ?, ?, ?);", cur_stage.fetchall())

    conn_dist.commit()

    # 3. B-Tree Covering Indexes (<250ms SLA Guarantee)
    cur_dist.executescript("""
        CREATE INDEX idx_lexemes_canonical ON lexemes(canonical_form, pos);
        CREATE INDEX idx_forms_surface ON forms(surface_form);
        CREATE INDEX idx_morph_parent ON morphology_edges(parent_id, relation_type);
        CREATE INDEX idx_morph_child ON morphology_edges(child_id, relation_type);
        CREATE INDEX idx_sem_subject ON semantic_edges(subject_id, relation_type);
        CREATE INDEX idx_sem_object ON semantic_edges(object_id, relation_type);
        CREATE INDEX idx_crosswalk_src ON entity_crosswalk(source_table, source_id);
    """)

    # 4. Final Vacuum & Analysis
    cur_dist.execute("ANALYZE;")
    cur_dist.execute("PRAGMA optimize;")

    conn_stage.close()
    conn_dist.close()

    compile_duration = time.time() - start_time

    # SLA Benchmark Run
    conn_bench = sqlite3.connect(dist_db)
    cur_bench = conn_bench.cursor()
    bench_start = time.time()

    fixtures = ['run', 'fast', 'happy', 'go', 'good', 'bad', 'bank']
    for f in fixtures:
        cur_bench.execute("""
            SELECT l.canonical_form, l.pos, m.relation_type, m.surface_form, m.affix
            FROM lexemes l
            LEFT JOIN morphology_edges m ON l.id = m.parent_id
            WHERE l.canonical_form = ?;
        """, (f,))
        _ = cur_bench.fetchall()

    bench_duration_ms = (time.time() - bench_start) * 1000
    conn_bench.close()

    db_size_kb = os.path.getsize(dist_db) / 1024
    status = "PASS" if bench_duration_ms < 250.0 else "FAIL"

    print(f"{status} | Compiled: {dist_db} ({db_size_kb:.1f} KB) | SLA Query: {bench_duration_ms:.2f}ms (<250ms SLA) | Total: {compile_duration:.3f}s")

if __name__ == "__main__":
    compile_graph()
