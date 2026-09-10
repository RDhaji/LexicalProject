import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DB = ROOT / "data" / "distribution" / "lexical_graph.db"
FIXTURES = ["run", "fast", "happy", "go", "good", "bad", "bank"]

def audit_topology():
    t0 = time.perf_counter()
    anomalies = []

    if not DIST_DB.exists() or DIST_DB.stat().st_size == 0:
        print(f"FAIL: Target production database missing or empty: {DIST_DB}")
        sys.exit(1)

    conn = sqlite3.connect(DIST_DB)
    cur = conn.cursor()

    # 1. Component inventory counts
    total_lexemes = cur.execute("SELECT COUNT(*) FROM lexemes;").fetchone()[0]
    total_forms = cur.execute("SELECT COUNT(*) FROM forms;").fetchone()[0]
    total_edges = cur.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]
    total_synsets = cur.execute("SELECT COUNT(*) FROM synsets;").fetchone()[0]
    
    # 2. Relation type breakdown
    rel_counts = dict(cur.execute("SELECT relation_type, COUNT(*) FROM edges GROUP BY relation_type;").fetchall())
    if "HAS_FORM" not in rel_counts:
        anomalies.append("No HAS_FORM relations found in edge table")

    # 3. Isolation & Dangling Node Audit
    # Degree-0 lexemes check (lexemes with no inbound or outbound edges)
    isolated_lexemes = cur.execute("""
        SELECT COUNT(*) FROM lexemes l
        WHERE NOT EXISTS (SELECT 1 FROM edges e WHERE e.source_id = l.id OR e.target_id = l.id);
    """).fetchone()[0]

    # Degree-0 forms check (forms with no inbound or outbound edges)
    isolated_forms = cur.execute("""
        SELECT COUNT(*) FROM forms f
        WHERE NOT EXISTS (SELECT 1 FROM edges e WHERE e.source_id = f.id OR e.target_id = f.id);
    """).fetchone()[0]

    isolated_pct_lex = (isolated_lexemes / total_lexemes) * 100 if total_lexemes else 0
    isolated_pct_forms = (isolated_forms / total_forms) * 100 if total_forms else 0

    if isolated_pct_lex > 15.0:
        anomalies.append(f"High isolated lexeme ratio: {isolated_pct_lex:.2f}% ({isolated_lexemes:,} / {total_lexemes:,})")
    if isolated_pct_forms > 5.0:
        anomalies.append(f"High isolated form ratio: {isolated_pct_forms:.2f}% ({isolated_forms:,} / {total_forms:,})")

    # 4. Vertical Slice Connectivity & Polysemy / Inflection Reachability
    fixture_degree_stats = {}
    for fix in FIXTURES:
        deg = cur.execute("""
            SELECT COUNT(e.id)
            FROM lexemes l
            JOIN edges e ON (l.id = e.source_id OR l.id = e.target_id)
            WHERE l.lemma = ?;
        """, (fix,)).fetchone()[0]
        fixture_degree_stats[fix] = deg
        if deg == 0:
            anomalies.append(f"Fixture node '{fix}' is completely disconnected (degree = 0)")

    # 5. Semantic Edge / Synset Topology Verification
    sem_edge_count = cur.execute("SELECT COUNT(*) FROM semantic_edges;").fetchone()[0]
    if sem_edge_count < 100000:
        anomalies.append(f"Low semantic edge count: {sem_edge_count:,} (threshold 100,000)")

    dangling_sem_edges = cur.execute("""
        SELECT COUNT(*) FROM semantic_edges se
        WHERE NOT EXISTS (SELECT 1 FROM synsets s WHERE s.id = se.subject_id)
           OR NOT EXISTS (SELECT 1 FROM synsets s WHERE s.id = se.object_id);
    """).fetchone()[0]
    if dangling_sem_edges > 0:
        anomalies.append(f"Dangling semantic edge endpoints detected: {dangling_sem_edges}")

    duration = time.perf_counter() - t0
    conn.close()

    if anomalies:
        print(f"TOPOLOGY_AUDIT_FAILED | Duration: {duration:.2f}s | Anomalies: {len(anomalies)}")
        for a in anomalies:
            print(f"  - {a}")
        sys.exit(1)

    print(f"TOPOLOGY_AUDIT_PASSED | Duration: {duration:.2f}s | Lexemes: {total_lexemes:,} | Forms: {total_forms:,} | Edges: {total_edges:,} | Synsets: {total_synsets:,} | Semantic Edges: {sem_edge_count:,}")
    print(f"Isolated: Lexemes={isolated_lexemes:,} ({isolated_pct_lex:.2f}%), Forms={isolated_forms:,} ({isolated_pct_forms:.2f}%) | Dangling Sem Edges={dangling_sem_edges}")
    print(f"Fixture Degrees: {fixture_degree_stats}")

if __name__ == "__main__":
    audit_topology()
