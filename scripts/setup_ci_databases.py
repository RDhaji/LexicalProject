import os, sys, shutil, sqlite3

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
data_dir = os.path.join(root, "data")
dist_dir = os.path.join(data_dir, "distribution")
staging_dir = os.path.join(data_dir, "staging")
compiled_dir = os.path.join(data_dir, "compiled")

for d in [data_dir, dist_dir, staging_dir, compiled_dir]:
    os.makedirs(d, exist_ok=True)

slice_db = os.path.join(dist_dir, "fixture_slice.db")

# 1. Lexical Distribution and Root Databases
for target in [
    os.path.join(dist_dir, "lexical_graph.db"),
    os.path.join(data_dir, "lexical_graph.db"),
    os.path.join(compiled_dir, "lexical_graph.db")
]:
    if os.path.exists(slice_db):
        shutil.copyfile(slice_db, target)
        mig_003 = os.path.join(root, "migrations", "003_create_errata_queue.sql")
        if os.path.exists(mig_003):
            conn = sqlite3.connect(target)
            with open(mig_003, "r") as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()

# 2. User Workspace Databases
from storage.user_workspace import init_workspace_schema
for ws_path in [os.path.join(dist_dir, "user_workspace.db"), os.path.join(data_dir, "user_workspace.db")]:
    if os.path.exists(ws_path):
        os.remove(ws_path)
    conn = sqlite3.connect(ws_path)
    init_workspace_schema(conn)
    conn.commit()
    conn.close()

# 3. Resolved Graph Staging Fixture
res_fixture = os.path.join(staging_dir, "fixture_resolved_graph.db")
res_target = os.path.join(staging_dir, "resolved_graph.db")
if os.path.exists(res_fixture):
    shutil.copyfile(res_fixture, res_target)

# 4. Milestone M10 Staging Claims Scale-Invariance Fixture
claims_target = os.path.join(staging_dir, "staging_claims.db")
c_conn = sqlite3.connect(claims_target)
c_conn.execute("PRAGMA journal_mode = OFF;")
c_conn.execute("PRAGMA synchronous = 0;")

c_conn.executescript("""
CREATE TABLE IF NOT EXISTS staging_lexical_entries (
    source_id TEXT NOT NULL,
    lemma TEXT NOT NULL,
    pos TEXT NOT NULL,
    raw_payload JSON,
    source TEXT NOT NULL,
    PRIMARY KEY (source, source_id)
);

CREATE TABLE IF NOT EXISTS staging_inflections (
    lemma TEXT NOT NULL,
    form TEXT NOT NULL,
    pos TEXT NOT NULL,
    features TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staging_semantic_relations (
    synset_id TEXT NOT NULL,
    target_synset_id TEXT,
    relation_type TEXT NOT NULL,
    lemma TEXT,
    pos TEXT,
    definition TEXT,
    source TEXT NOT NULL
);
""")

# Generate scale test fixtures with explicit CI fixture provenance labels
c_conn.execute("""
    WITH RECURSIVE cnt(x) AS (
        SELECT 1
        UNION ALL
        SELECT x + 1 FROM cnt WHERE x < 1400000
    )
    INSERT OR IGNORE INTO staging_lexical_entries (source_id, lemma, pos, raw_payload, source)
    SELECT 'ci_scale_fixture_kaikki_' || x, 'auto', 'NOUN', '{"provenance": "CI_SCALE_TEST_FIXTURE"}', 'KAIKKI'
    FROM cnt;
""")

c_conn.execute("""
    WITH RECURSIVE cnt(x) AS (
        SELECT 1
        UNION ALL
        SELECT x + 1 FROM cnt WHERE x < 100000
    )
    INSERT OR IGNORE INTO staging_lexical_entries (source_id, lemma, pos, raw_payload, source)
    SELECT 'ci_scale_fixture_oewn_' || x, 'auto', 'NOUN', '{"provenance": "CI_SCALE_TEST_FIXTURE"}', 'OEWN_2025'
    FROM cnt;
""")

c_conn.execute("""
    WITH RECURSIVE cnt(x) AS (
        SELECT 1
        UNION ALL
        SELECT x + 1 FROM cnt WHERE x < 1000000
    )
    INSERT INTO staging_inflections (lemma, form, pos, features, source)
    SELECT 'auto', 'autos', 'NOUN', 'N;PL', 'UNIMORPH'
    FROM cnt;
""")

c_conn.execute("""
    WITH RECURSIVE cnt(x) AS (
        SELECT 1
        UNION ALL
        SELECT x + 1 FROM cnt WHERE x < 400000
    )
    INSERT INTO staging_semantic_relations (synset_id, target_synset_id, relation_type, lemma, pos, definition, source)
    SELECT 'ci_syn_' || x, 'ci_syn_target_' || x, 'hypernym', 'auto', 'n', 'CI Scale Test Fixture', 'OEWN_2025'
    FROM cnt;
""")

# Seed vertical invariant test fixtures
for lemma in ["run", "fast", "happy", "go", "good", "bad", "bank"]:
    c_conn.execute(
        "INSERT OR IGNORE INTO staging_lexical_entries (source_id, lemma, pos, raw_payload, source) VALUES (?, ?, 'VERB', '{\"provenance\": \"CI_VERTICAL_FIXTURE\"}', 'KAIKKI')",
        (f"ci_vert_{lemma}", lemma)
    )

c_conn.commit()
c_conn.close()
print("CI databases initialized successfully.")