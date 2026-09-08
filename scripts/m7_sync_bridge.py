import sqlite3
import os
import json
import time

def setup_workspace_and_sync_bridge():
    start_time = time.time()
    dist_dir = "data/distribution"
    workspace_db = os.path.join(dist_dir, "user_workspace.db")
    graph_db = os.path.join(dist_dir, "lexical_graph.db")

    if not os.path.exists(graph_db):
        raise FileNotFoundError(f"Missing distribution graph: {graph_db}")

    conn_ws = sqlite3.connect(workspace_db)
    cur_ws = conn_ws.cursor()

    # Invariant 7: Strictly NO Foreign Keys referencing lexical_graph.db
    cur_ws.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS user_annotations (
            annotation_id TEXT PRIMARY KEY,
            target_entity_id TEXT NOT NULL,
            target_entity_type TEXT NOT NULL,
            user_notes TEXT,
            tags TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sync_tombstones (
            entity_id TEXT PRIMARY KEY,
            deleted_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sync_state (
            client_id TEXT PRIMARY KEY,
            last_synced_version TEXT NOT NULL,
            last_sync_timestamp TEXT NOT NULL
        );
    """)

    # Seed test user annotation referencing fixture entity 'run'
    conn_graph = sqlite3.connect(graph_db)
    cur_graph = conn_graph.cursor()
    cur_graph.execute("SELECT id FROM lexemes WHERE canonical_form = 'run' LIMIT 1;")
    run_row = cur_graph.fetchone()
    conn_graph.close()

    if run_row:
        run_id = run_row[0]
        cur_ws.execute("""
            INSERT OR REPLACE INTO user_annotations 
            (annotation_id, target_entity_id, target_entity_type, user_notes, tags, updated_at)
            VALUES ('ann_run_test', ?, 'LEXEME', 'High-frequency polysemous verb', '[\"fixture\",\"core\"]', datetime('now'));
        """, (run_id,))

    conn_ws.commit()

    # Verify no foreign keys reference lexical_graph
    cur_ws.execute("PRAGMA foreign_key_list(user_annotations);")
    fk_list = cur_ws.fetchall()
    has_graph_fk = any(fk[2] == 'lexemes' or 'lexical_graph' in str(fk) for fk in fk_list)

    conn_ws.close()
    duration = time.time() - start_time

    if has_graph_fk:
        print("FAIL | Invariant 7 violated: user_workspace.db contains foreign key to lexical_graph.db")
    else:
        print(f"PASS | Workspace DB initialized: {workspace_db} | Invariant 7 verified (FK decoupled) | Duration: {duration:.3f}s")

if __name__ == "__main__":
    setup_workspace_and_sync_bridge()
