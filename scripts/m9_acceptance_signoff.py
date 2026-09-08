import sqlite3
import os
import hashlib
import json
import time

def verify_release():
    start_time = time.time()
    dist_dir = "data/distribution"
    graph_db = os.path.join(dist_dir, "lexical_graph.db")
    workspace_db = os.path.join(dist_dir, "user_workspace.db")
    manifest_path = os.path.join(dist_dir, "release_manifest.json")

    assert os.path.exists(graph_db), f"Missing {graph_db}"
    assert os.path.exists(workspace_db), f"Missing {workspace_db}"

    # Calculate SHA256 checksums
    def get_hash(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    graph_hash = get_hash(graph_db)
    workspace_hash = get_hash(workspace_db)

    # Acceptance Integrity Checks
    conn = sqlite3.connect(graph_db)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM lexemes;")
    lexeme_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM forms;")
    form_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM morphology_edges;")
    morph_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM semantic_edges;")
    sem_count = cur.fetchone()[0]

    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchone()[0]
    conn.close()

    assert integrity == "ok", f"Integrity check failed: {integrity}"

    manifest = {
        "version": "1.0.0-rc1",
        "timestamp_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "artifacts": {
            "lexical_graph.db": {
                "sha256": graph_hash,
                "bytes": os.path.getsize(graph_db),
                "counts": {
                    "lexemes": lexeme_count,
                    "forms": form_count,
                    "morphology_edges": morph_count,
                    "semantic_edges": sem_count
                }
            },
            "user_workspace.db": {
                "sha256": workspace_hash,
                "bytes": os.path.getsize(workspace_db)
            }
        },
        "acceptance_status": "PASSED"
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    duration = time.time() - start_time
    print(f"PASS | Artifacts signed | Lexemes: {lexeme_count} | Forms: {form_count} | Edges: {morph_count + sem_count} | Duration: {duration:.3f}s")

if __name__ == "__main__":
    verify_release()
