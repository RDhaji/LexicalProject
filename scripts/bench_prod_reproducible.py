import sqlite3
import time
import json
import os

db_path = "data/distribution/lexical_graph.db"
if not os.path.exists(db_path):
    print("FAIL: Distribution DB not found.")
    exit(1)

size = os.path.getsize(db_path)
print(f"Target DB: {db_path} ({size} bytes, {size / 1e9:.2f} GB)")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

fixtures = ["run", "fast", "happy", "go", "good", "bad", "bank"]
metrics = {"exact": {}, "prefix": {}, "expand": {}, "paradigm": {}, "provenance": {}}

# 1. EXACT_LOOKUP (<50ms)
for f in fixtures:
    t0 = time.perf_counter()
    cur.execute("""
        SELECT l.id, l.lemma, l.pos, l.language,
               p.id, p.notation, p.transcription, p.variety, p.epistemic_class, p.provenance_id
        FROM lexemes l
        LEFT JOIN pronunciations p ON p.target_id = l.id AND p.target_type = 'LEXEME'
        WHERE l.lemma = ?;
    """, (f,))
    rows = cur.fetchall()
    dt = (time.perf_counter() - t0) * 1000.0
    metrics["exact"][f] = {"lat_ms": round(dt, 2), "rows": len(rows), "pass": dt < 50.0 and len(rows) > 0}
    print(f"EXACT '{f}': {dt:.2f}ms | count={len(rows)} | pass={metrics['exact'][f]['pass']}")

# 2. PREFIX_LOOKUP (<50ms)
prefixes = ["ru", "fa", "hap", "go", "goo", "ba", "ban"]
for p in prefixes:
    t0 = time.perf_counter()
    cur.execute("SELECT id, lemma, pos, language FROM lexemes WHERE lemma >= ? AND lemma < ? LIMIT 10;", (p, p[:-1] + chr(ord(p[-1]) + 1)))
    rows = cur.fetchall()
    dt = (time.perf_counter() - t0) * 1000.0
    metrics["prefix"][p] = {"lat_ms": round(dt, 2), "count": len(rows), "pass": dt < 50.0 and len(rows) > 0}
    print(f"PREFIX '{p}': {dt:.2f}ms | count={len(rows)} | pass={metrics['prefix'][p]['pass']}")

# 3. EXPAND_GRAPH D<=3 (<250ms)
for f in ["run", "go", "bank"]:
    cur.execute("SELECT id FROM lexemes WHERE lemma = ? LIMIT 1;", (f,))
    root_id = cur.fetchone()[0]
    for d in [1, 2, 3]:
        t0 = time.perf_counter()
        cur.execute("""
            WITH RECURSIVE bfs(id, depth) AS (
                SELECT ?, 0
                UNION
                SELECT CASE WHEN e.source_id = b.id THEN e.target_id ELSE e.source_id END, b.depth + 1
                FROM edges e
                JOIN bfs b ON (e.source_id = b.id OR e.target_id = b.id)
                WHERE b.depth < ?
            )
            SELECT DISTINCT id FROM bfs LIMIT 50;
        """, (root_id, d))
        nodes = cur.fetchall()
        dt = (time.perf_counter() - t0) * 1000.0
        key = f"{f}_d{d}"
        metrics["expand"][key] = {"lat_ms": round(dt, 2), "nodes": len(nodes), "pass": dt < 250.0}
        print(f"EXPAND '{f}' D={d}: {dt:.2f}ms | nodes={len(nodes)} | pass={metrics['expand'][key]['pass']}")

# 4. GET_PARADIGM
t0 = time.perf_counter()
cur.execute("SELECT id FROM lexemes WHERE lemma = 'run' LIMIT 1;")
run_id = cur.fetchone()[0]
cur.execute("""
    SELECT f.id, f.form, e.relation_type, e.features, e.epistemic_status, e.provenance
    FROM edges e
    JOIN forms f ON e.target_id = f.id
    WHERE e.source_id = ? AND e.relation_type = 'HAS_FORM';
""", (run_id,))
para = cur.fetchall()
dt = (time.perf_counter() - t0) * 1000.0
metrics["paradigm"]["run"] = {"lat_ms": round(dt, 2), "forms": len(para), "pass": len(para) > 0}
print(f"PARADIGM 'run': {dt:.2f}ms | forms={len(para)} | pass={metrics['paradigm']['run']['pass']}")

# 5. GET_PROVENANCE
t0 = time.perf_counter()
cur.execute("SELECT id, provenance FROM edges WHERE source_id = ? LIMIT 5;", (run_id,))
prov = cur.fetchall()
dt = (time.perf_counter() - t0) * 1000.0
metrics["provenance"]["run"] = {"lat_ms": round(dt, 2), "records": len(prov), "pass": len(prov) > 0}
print(f"PROVENANCE 'run': {dt:.2f}ms | records={len(prov)} | pass={metrics['provenance']['run']['pass']}")

conn.close()

with open("data/distribution/m11_production_benchmark.json", "w") as f:
    json.dump(metrics, f, indent=2)

print("BENCHMARK_COMPLETE")
