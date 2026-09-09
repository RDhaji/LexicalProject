import json
import os
import shutil
import sqlite3
import subprocess
import time

DIST_DB = "dist/data/lexical_graph.db"
USER_DB = "data/distribution/user_workspace.db"
MANIFEST = "dist/RELEASE_MANIFEST.json"
ARCHIVE_DIR = "backups/production_freeze"

def run_archive_and_maintenance():
    t0 = time.perf_counter()
    assert os.path.exists(DIST_DB), f"Missing database: {DIST_DB}"
    assert os.path.exists(MANIFEST), f"Missing manifest: {MANIFEST}"

    # 1. Vacuum & Optimize Production Databases
    conn = sqlite3.connect(DIST_DB)
    conn.execute("PRAGMA optimize;")
    conn.commit()
    conn.close()

    if os.path.exists(USER_DB):
        u_conn = sqlite3.connect(USER_DB)
        u_conn.execute("PRAGMA optimize;")
        u_conn.commit()
        u_conn.close()

    # 2. Production Cold-Storage Snapshot
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    shutil.copy2(DIST_DB, os.path.join(ARCHIVE_DIR, "lexical_graph.db"))
    shutil.copy2(MANIFEST, os.path.join(ARCHIVE_DIR, "RELEASE_MANIFEST.json"))

    # 3. Clean Ephemeral Caches & Artifacts
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d in ("__pycache__", ".pytest_cache"):
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)

    # 4. Final Invariant Regression Confirmation
    res = subprocess.run(["pytest", "tests/", "-q"], capture_output=True, text=True)
    assert res.returncode == 0, f"Maintenance regression failure:\n{res.stderr}\n{res.stdout}"

    duration = time.perf_counter() - t0
    print(f"ARCHIVE_AND_MAINTENANCE_PASSED | Duration: {duration:.2f}s | Archive: {ARCHIVE_DIR} | Snapshot: OK")

if __name__ == "__main__":
    run_archive_and_maintenance()
