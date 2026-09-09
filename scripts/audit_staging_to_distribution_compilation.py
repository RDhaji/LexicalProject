import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING_DB = ROOT / "data" / "staging" / "staging_claims.db"
RESOLVED_DB = ROOT / "data" / "staging" / "resolved_graph.db"
DIST_DB = ROOT / "data" / "distribution" / "lexical_graph.db"

FIXTURES = ["run", "fast", "happy", "go", "good", "bad", "bank"]

def audit_compilation():
    t_start = time.perf_counter()
    anomalies = []

    # 1. Existence and size verification
    for db_path, name in [(STAGING_DB, "Staging DB"), (RESOLVED_DB, "Resolved DB"), (DIST_DB, "Distribution DB")]:
        if not db_path.exists():
            anomalies.append(f"Missing database: {name} at {db_path}")
        elif db_path.stat().st_size == 0:
            anomalies.append(f"Empty database file: {name} at {db_path}")

    if anomalies:
        for a in anomalies:
            print(f"FAIL: {a}")
        sys.exit(1)

    # 2. Distribution DB PRAGMA and Schema Integrity
    conn_dist = sqlite3.connect(DIST_DB)
    cur_dist = conn_dist.cursor()

    journal_mode = cur_dist.execute("PRAGMA journal_mode;").fetchone()[0]
    # Check table existence
    tables = {r[0] for r in cur_dist.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()}
    required_tables = {"lexemes", "forms", "edges", "synsets", "semantic_edges"}
    missing_tables = required_tables - tables
    if missing_tables:
        anomalies.append(f"Distribution DB missing tables: {missing_tables}")

    # Check indices
    indices = {r[0] for r in cur_dist.execute("SELECT name FROM sqlite_master WHERE type='index';").fetchall()}
    if not indices:
        anomalies.append("Distribution DB lacks secondary indices")

    # 3. Entity & Edge Isolation / Invariant 6 Validation
    collision_cnt = cur_dist.execute(
        "SELECT COUNT(*) FROM lexemes l JOIN forms f ON l.id = f.id;"
    ).fetchone()[0]
    if collision_cnt > 0:
        anomalies.append(f"Invariant 6 Violation: {collision_cnt} ID collisions between lexemes and forms")

    # 4. Referential Integrity on Core Relations (Dangling Edges)
    # Check sample of edges to verify source and target existence
    dangling_source = cur_dist.execute("""
        SELECT COUNT(*) FROM edges e
        WHERE e.relation_type = 'HAS_FORM'
          AND NOT EXISTS (SELECT 1 FROM lexemes l WHERE l.id = e.source_id);
    """).fetchone()[0]
    if dangling_source > 0:
        anomalies.append(f"Dangling edge sources detected: {dangling_source} HAS_FORM edges missing lexeme")

    dangling_target = cur_dist.execute("""
        SELECT COUNT(*) FROM edges e
        WHERE e.relation_type = 'HAS_FORM'
          AND NOT EXISTS (SELECT 1 FROM forms f WHERE f.id = e.target_id);
    """).fetchone()[0]
    if dangling_target > 0:
        anomalies.append(f"Dangling edge targets detected: {dangling_target} HAS_FORM edges missing form")

    # 5. Staging-to-Distribution Propagation Volume Parity
    conn_res = sqlite3.connect(RESOLVED_DB)
    cur_res = conn_res.cursor()
    res_lexemes = cur_res.execute("SELECT COUNT(*) FROM resolved_lexemes;").fetchone()[0]
    res_forms = cur_res.execute("SELECT COUNT(*) FROM resolved_forms;").fetchone()[0]
    conn_res.close()

    dist_lexemes = cur_dist.execute("SELECT COUNT(*) FROM lexemes;").fetchone()[0]
    dist_forms = cur_dist.execute("SELECT COUNT(*) FROM forms;").fetchone()[0]
    dist_edges = cur_dist.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]

    # Distribution DB must contain at least the resolved count
    if dist_lexemes < res_lexemes:
        anomalies.append(f"Lexeme loss in distribution: {dist_lexemes:,} < resolved {res_lexemes:,}")
    if dist_forms < res_forms:
        anomalies.append(f"Form loss in distribution: {dist_forms:,} < resolved {res_forms:,}")

    # 6. Read Query Latency Performance Test on Core Fixtures
    fixture_latencies = []
    for lemma in FIXTURES:
        t0 = time.perf_counter()
        cur_dist.execute("""
            SELECT l.id, l.lemma, l.pos, f.form, e.relation_type
            FROM lexemes l
            JOIN edges e ON l.id = e.source_id
            JOIN forms f ON e.target_id = f.id
            WHERE l.lemma = ?;
        """, (lemma,)).fetchall()
        fixture_latencies.append(time.perf_counter() - t0)

    avg_latency_ms = (sum(fixture_latencies) / len(fixture_latencies)) * 1000
    if avg_latency_ms > 20.0:
        anomalies.append(f"Slow fixture traversal latency: {avg_latency_ms:.2f}ms (threshold 20ms)")

    conn_dist.close()
    duration = time.perf_counter() - t_start

    if anomalies:
        print(f"AUDIT_FAILED | Duration: {duration:.2f}s | Anomalies: {len(anomalies)}")
        for a in anomalies:
            print(f"  - {a}")
        sys.exit(1)

    print(f"AUDIT_PASSED | Duration: {duration:.2f}s | Avg Traversal Latency: {avg_latency_ms:.2f}ms | Journal: {journal_mode}")
    print(f"Verified Counts -> Lexemes: {dist_lexemes:,} | Forms: {dist_forms:,} | Edges: {dist_edges:,}")

if __name__ == "__main__":
    audit_compilation()
