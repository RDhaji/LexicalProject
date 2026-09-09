import os
import resource
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING_DB = ROOT / "data" / "staging" / "staging_claims.db"
RESOLVED_DB = ROOT / "data" / "staging" / "resolved_graph.db"
DIST_DB = ROOT / "data" / "distribution" / "lexical_graph.db"

def get_peak_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    if sys.platform == "darwin":
        return usage.ru_maxrss / (1024 * 1024)
    return usage.ru_maxrss / 1024

def benchmark_pipeline():
    t_start = time.perf_counter()
    metrics = {}

    # Stage 1: Streaming Ingestion Counts & Throughput
    t0 = time.perf_counter()
    s_conn = sqlite3.connect(STAGING_DB)
    s_cur = s_conn.cursor()
    raw_claims = s_cur.execute("SELECT COUNT(*) FROM raw_claims").fetchone()[0]
    synsets = s_cur.execute("SELECT COUNT(*) FROM synsets").fetchone()[0]
    sem_rel = s_cur.execute("SELECT COUNT(*) FROM semantic_relations").fetchone()[0]
    inflections = s_cur.execute("SELECT COUNT(*) FROM staging_inflections").fetchone()[0]
    s_conn.close()
    t_stage1 = time.perf_counter() - t0
    metrics["stage1_staging"] = {
        "raw_claims": raw_claims,
        "synsets": synsets,
        "semantic_relations": sem_rel,
        "inflections": inflections,
        "query_time_s": t_stage1,
    }

    # Stage 2: Resolution Parity & Throughput
    t0 = time.perf_counter()
    r_conn = sqlite3.connect(RESOLVED_DB)
    r_cur = r_conn.cursor()
    res_lexemes = r_cur.execute("SELECT COUNT(*) FROM resolved_lexemes").fetchone()[0]
    res_forms = r_cur.execute("SELECT COUNT(*) FROM resolved_forms").fetchone()[0]
    res_relations = r_cur.execute("SELECT COUNT(*) FROM resolved_relations").fetchone()[0]
    rel_claims = r_cur.execute("SELECT COUNT(*) FROM relation_claims").fetchone()[0]
    r_conn.close()
    t_stage2 = time.perf_counter() - t0
    metrics["stage2_resolved"] = {
        "resolved_lexemes": res_lexemes,
        "resolved_forms": res_forms,
        "resolved_relations": res_relations,
        "relation_claims": rel_claims,
        "query_time_s": t_stage2,
    }

    # Stage 3: Distribution Graph Verification & Counts
    t0 = time.perf_counter()
    d_conn = sqlite3.connect(DIST_DB)
    d_cur = d_conn.cursor()
    dist_lexemes = d_cur.execute("SELECT COUNT(*) FROM lexemes").fetchone()[0]
    dist_forms = d_cur.execute("SELECT COUNT(*) FROM forms").fetchone()[0]
    dist_edges = d_cur.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    dist_synsets = d_cur.execute("SELECT COUNT(*) FROM synsets").fetchone()[0]
    d_conn.close()
    t_stage3 = time.perf_counter() - t0
    metrics["stage3_distribution"] = {
        "lexemes": dist_lexemes,
        "forms": dist_forms,
        "edges": dist_edges,
        "synsets": dist_synsets,
        "query_time_s": t_stage3,
    }

    total_time = time.perf_counter() - t_start
    peak_rss = get_peak_rss_mb()
    
    dist_size_mb = os.path.getsize(DIST_DB) / (1024 * 1024)
    staging_size_mb = os.path.getsize(STAGING_DB) / (1024 * 1024)
    resolved_size_mb = os.path.getsize(RESOLVED_DB) / (1024 * 1024)

    print("=== CORPUS SCALEUP INGESTION BENCHMARK RESULTS ===")
    print(f"Total Benchmark Duration: {total_time:.3f}s | Peak RSS: {peak_rss:.2f} MB")
    print(f"Staging DB Size: {staging_size_mb:.2f} MB | Raw Claims: {raw_claims:,} | Synsets: {synsets:,}")
    print(f"Resolved DB Size: {resolved_size_mb:.2f} MB | Lexemes: {res_lexemes:,} | Forms: {res_forms:,} | Relations: {res_relations:,}")
    print(f"Production DB Size: {dist_size_mb:.2f} MB | Lexemes: {dist_lexemes:,} | Forms: {dist_forms:,} | Edges: {dist_edges:,}")
    
    # Invariant and scale assertion gates
    assert raw_claims >= 500000, f"Raw claims below threshold: {raw_claims}"
    assert res_lexemes >= 400000, f"Resolved lexemes below threshold: {res_lexemes}"
    assert dist_lexemes >= 400000, f"Production lexemes below threshold: {dist_lexemes}"
    assert dist_edges >= 600000, f"Production edges below threshold: {dist_edges}"
    print("ALL SCALEUP BENCHMARK THRESHOLDS PASSED")

if __name__ == "__main__":
    benchmark_pipeline()
