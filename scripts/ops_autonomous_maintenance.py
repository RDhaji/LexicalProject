import json, os, subprocess, sys, time, sqlite3

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
from packages.pipeline.src.errata_processor import process_pending_errata

start = time.time()
db_path = os.path.join(root, "data", "lexical_graph.db")

# 1. Structural, epistemic, and cross-DB isolation monitoring sweep
mon = subprocess.run([sys.executable, os.path.join(root, "scripts", "ops_continuous_monitoring.py")], cwd=root, capture_output=True, text=True)
assert mon.returncode == 0, f"Continuous monitoring sweep failed: {mon.stderr}"

# 2. Backlog drain & non-destructive conflict preservation (Invariant 3 & Invariant 2)
errata_processed = process_pending_errata(db_path)

# 3. Database maintenance
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA optimize;")
conn.close()

# 4. Vertical-slice regression verification
test = subprocess.run([sys.executable, "-m", "pytest", "tests/pipeline/test_errata_queue.py", "-q"], cwd=root, capture_output=True, text=True)
assert test.returncode == 0, f"Pytest regression suite failed: {test.stderr}"

report = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "status": "HEALTHY",
    "monitoring": "PASSED",
    "errata_processed": errata_processed,
    "regression_tests": "PASSED",
    "duration_sec": round(time.time() - start, 3)
}
with open(os.path.join(root, "maintenance_telemetry.json"), "w") as f:
    json.dump(report, f, indent=2)

print(f"AUTONOMOUS_MAINTENANCE_SUCCESS|errata={errata_processed}|duration={report['duration_sec']}s")
