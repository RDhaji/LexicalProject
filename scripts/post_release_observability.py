import http.client
import json
import os
import sqlite3
import subprocess
import time

DIST_DB = "dist/data/lexical_graph.db"
MANIFEST = "dist/RELEASE_MANIFEST.json"
FIXTURES = ["run", "fast", "happy", "go", "good", "bad", "bank"]

def run_observability():
    t_start = time.perf_counter()
    assert os.path.exists(DIST_DB), f"Missing database: {DIST_DB}"
    assert os.path.exists(MANIFEST), f"Missing manifest: {MANIFEST}"

    # 1. Byte-Range Streaming Health Check & Headers
    srv = subprocess.Popen(["python3", "serve_client.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    try:
        conn_http = http.client.HTTPConnection("localhost", 8080, timeout=5)
        conn_http.request("GET", "/dist/data/lexical_graph.db", headers={"Range": "bytes=0-15"})
        res = conn_http.getresponse()
        assert res.status == 206, f"HTTP-206 failure: {res.status}"
        raw_header = res.read()
        assert raw_header.startswith(b"SQLite format 3\x00"), "Corrupted SQLite header received"
        accept_ranges = res.getheader("Accept-Ranges")
        assert accept_ranges == "bytes", f"Missing Accept-Ranges header: {accept_ranges}"
    finally:
        srv.terminate()
        srv.wait()

    # 2. Production Latency & Query Plan SLA (<250ms)
    conn = sqlite3.connect(DIST_DB)
    cur = conn.cursor()
    latencies = []
    for f in FIXTURES:
        t0 = time.perf_counter()
        cur.execute("SELECT id, lemma, pos FROM lexemes WHERE lemma = ?", (f,))
        rows = cur.fetchall()
        assert len(rows) > 0, f"Missing fixture: {f}"
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        cur.execute("EXPLAIN QUERY PLAN SELECT id FROM lexemes WHERE lemma = ?", (f,))
        plan = " ".join([r[3] for r in cur.fetchall()])
        assert "INDEX" in plan or "COVERING" in plan, f"Unindexed query scan detected for {f}: {plan}"

    # 3. Phonetic and Cross-Lingual Query Plan SLAs
    for f in FIXTURES:
        cur.execute("""
            EXPLAIN QUERY PLAN
            SELECT p.transcription FROM pronunciations p
            JOIN lexemes l ON p.target_id = l.id
            WHERE l.lemma = ?;
        """, (f,))
        plan = " ".join([r[3] for r in cur.fetchall()])
        assert "INDEX" in plan, f"Pronunciation query plan unindexed: {plan}"

        cur.execute("""
            EXPLAIN QUERY PLAN
            SELECT le.lemma FROM lexemes_es le
            JOIN edges e ON e.target_id = le.id
            JOIN lexemes l ON e.source_id = l.id
            WHERE l.lemma = ? AND e.relation_type = 'TRANSLATION_OF';
        """, (f,))
        plan_trans = " ".join([r[3] for r in cur.fetchall()])
        assert "INDEX" in plan_trans, f"Translation query plan unindexed: {plan_trans}"

    conn.close()

    max_lat = max(latencies)
    avg_lat = sum(latencies) / len(latencies)
    assert max_lat < 250, f"Max latency breached SLA: {max_lat:.2f}ms >= 250ms"

    print(f"OBSERVABILITY_AUDIT_PASSED | Duration: {time.perf_counter() - t_start:.2f}s | Max Latency: {max_lat:.2f}ms | Avg Latency: {avg_lat:.2f}ms | HTTP-206: OK")

if __name__ == "__main__":
    run_observability()
