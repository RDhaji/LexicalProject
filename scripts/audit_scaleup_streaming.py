import os
import sqlite3
import sys
import time

STAGING_DB = "data/staging/staging_claims.db"
RESOLVED_DB = "data/staging/resolved_graph.db"
KAIKKI_PATH = "data/raw/kaikki.org-dictionary-English.jsonl"
UNIMORPH_PATH = "data/raw/eng.unimorph"
OEWN_YAML_DIR = "data/raw/oewn_2025/src/yaml"

def audit_streaming_pipeline():
    t0 = time.perf_counter()
    anomalies = []

    # 1. Raw source file presence and accessibility
    for path, name in [(KAIKKI_PATH, "Kaikki JSONL"), (UNIMORPH_PATH, "UniMorph English"), (OEWN_YAML_DIR, "OEWN 2025 YAML Source")]:
        if not os.path.exists(path):
            anomalies.append(f"Missing upstream source: {name} at {path}")
        else:
            if os.path.isfile(path):
                size_mb = os.path.getsize(path) / (1024 * 1024)
            else:
                size_mb = sum(
                    os.path.getsize(os.path.join(root, f))
                    for root, _, files in os.walk(path)
                    for f in files
                ) / (1024 * 1024)
            if size_mb < 1.0:
                anomalies.append(f"Upstream source {name} at {path} is suspiciously small ({size_mb:.2f} MB)")

    # 2. Ingestion staging verification
    conn_stage = sqlite3.connect(STAGING_DB)
    cur_stage = conn_stage.cursor()

    checkpoints = cur_stage.execute("SELECT source_id, records_processed FROM parsing_checkpoints").fetchall()
    if not checkpoints:
        anomalies.append("No parsing checkpoints recorded in staging_claims.db")

    raw_claims_cnt = cur_stage.execute("SELECT COUNT(*) FROM raw_claims").fetchone()[0]
    synsets_cnt = cur_stage.execute("SELECT COUNT(*) FROM synsets").fetchone()[0]
    sem_rel_cnt = cur_stage.execute("SELECT COUNT(*) FROM semantic_relations").fetchone()[0]
    conn_stage.close()

    if raw_claims_cnt < 500000:
        anomalies.append(f"Low raw_claims count in staging: {raw_claims_cnt:,}")
    if synsets_cnt < 100000:
        anomalies.append(f"Low synsets count in staging: {synsets_cnt:,}")
    if sem_rel_cnt < 100000:
        anomalies.append(f"Low semantic_relations count in staging: {sem_rel_cnt:,}")

    # 3. Staging-to-Resolution Parity Audit
    conn_res = sqlite3.connect(RESOLVED_DB)
    cur_res = conn_res.cursor()

    resolved_lexemes_cnt = cur_res.execute("SELECT COUNT(*) FROM resolved_lexemes").fetchone()[0]
    resolved_forms_cnt = cur_res.execute("SELECT COUNT(*) FROM resolved_forms").fetchone()[0]
    resolved_relations_cnt = cur_res.execute("SELECT COUNT(*) FROM resolved_relations").fetchone()[0]
    relation_claims_cnt = cur_res.execute("SELECT COUNT(*) FROM relation_claims").fetchone()[0]
    conn_res.close()

    if resolved_lexemes_cnt < 400000:
        anomalies.append(f"Low resolved_lexemes count: {resolved_lexemes_cnt:,}")
    if resolved_forms_cnt < 600000:
        anomalies.append(f"Low resolved_forms count: {resolved_forms_cnt:,}")
    if resolved_relations_cnt < 600000:
        anomalies.append(f"Low resolved_relations count: {resolved_relations_cnt:,}")

    # Invariant 1 & Strict Provenance: relations must link to ingested claims
    unlinked_relations = resolved_relations_cnt - relation_claims_cnt
    if abs(unlinked_relations) > (0.01 * resolved_relations_cnt):
        anomalies.append(f"Provenance drift detected: {unlinked_relations} resolved relations lack 1:1 relation_claims link")

    duration = time.perf_counter() - t0
    if anomalies:
        print(f"SCALEUP_AUDIT_FAILED | Duration: {duration:.2f}s | Anomalies: {len(anomalies)}")
        for a in anomalies:
            print(f"  - {a}")
        sys.exit(1)

    print(f"SCALEUP_AUDIT_PASSED | Duration: {duration:.2f}s | Staging Claims: {raw_claims_cnt:,} | Synsets: {synsets_cnt:,} | Resolved Lexemes: {resolved_lexemes_cnt:,} | Resolved Forms: {resolved_forms_cnt:,} | Resolved Relations: {resolved_relations_cnt:,}")

if __name__ == "__main__":
    audit_streaming_pipeline()
