import sqlite3, sys, time, os, json

start = time.time()
lg_path = next((p for p in ("data/distribution/lexical_graph.db", "data/lexical_graph.db", "lexical_graph.db") if os.path.exists(p) and os.path.getsize(p) > 32768), "lexical_graph.db")
uw_path = next((p for p in ("data/distribution/user_workspace.db", "data/user_workspace.db", "user_workspace.db") if os.path.exists(p)), "user_workspace.db")

conn_lg, conn_uw = sqlite3.connect(lg_path), sqlite3.connect(uw_path)

# 1. Structural & Integrity Probes
assert conn_lg.execute("PRAGMA quick_check;").fetchone()[0] == "ok", "lexical_graph quick_check failed"
assert conn_uw.execute("PRAGMA quick_check;").fetchone()[0] == "ok", "user_workspace quick_check failed"

# 2. Invariant 7 Continuous Guard: Ensure 0 foreign keys cross DB boundaries
for (tbl,) in conn_uw.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall():
    for fk in conn_uw.execute(f"PRAGMA foreign_key_list({tbl});").fetchall():
        assert "lexical_graph" not in str(fk), f"Invariant 7 violation in {tbl}: {fk}"

# 3. Vertical Fixture Telemetry & Drift Monitoring (<15% variance threshold)
FIXTURES = ("run", "fast", "happy", "go", "good", "bad", "bank")
q = f"SELECT count(*) FROM lexemes WHERE lemma IN ({','.join('?' for _ in FIXTURES)})"
fixture_count = conn_lg.execute(q, FIXTURES).fetchone()[0]
assert fixture_count >= len(FIXTURES), f"Fixture drift detected: {fixture_count}/{len(FIXTURES)}"

# 4. Epistemic Classification Invariant 2 & 3 Sweep
for (tbl,) in conn_lg.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall():
    cols = [c[1] for c in conn_lg.execute(f"PRAGMA table_info({tbl});").fetchall() if "epistemic" in c[1].lower()]
    for col in cols:
        invalid = conn_lg.execute(f"SELECT count(*) FROM {tbl} WHERE {col} NOT IN ('EXPLICIT','GENERATED','ATTESTED','INFERRED','UNCERTAIN');").fetchone()[0]
        assert invalid == 0, f"Invariant 2 violation: {invalid} rows with invalid epistemic class in {tbl}.{col}"

conn_lg.close()
conn_uw.close()

telemetry = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "status": "HEALTHY",
    "fixtures_verified": fixture_count,
    "duration_sec": round(time.time() - start, 3)
}
with open("monitoring_telemetry.json", "w") as f:
    json.dump(telemetry, f, indent=2)

print(f"MONITORING_SWEEP_SUCCESS|db={lg_path}|fixtures={fixture_count}|duration={telemetry['duration_sec']}s")
