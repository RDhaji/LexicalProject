#!/usr/bin/env python3
import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DB = REPO_ROOT / 'data' / 'distribution' / 'lexical_graph.db'
ROOT_DB = REPO_ROOT / 'lexical_graph.db'

EPISTEMIC_CLASSES = {'EXPLICIT', 'GENERATED', 'ATTESTED', 'INFERRED', 'UNCERTAIN'}
CORE_FIXTURES = ['run', 'fast', 'happy', 'go', 'good', 'bad', 'bank']

def audit_database(path: Path):
    print(f"=== Auditing: {path.relative_to(REPO_ROOT)} ===")
    if not path.exists():
        print("  STATUS: MISSING FILE")
        return None

    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"  Size: {size_mb:.2f} MB | Permissions: {oct(path.stat().st_mode & 0o777)}")

    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    cur = conn.cursor()

    # Integrity & FK checks
    integrity = cur.execute("PRAGMA integrity_check;").fetchone()[0]
    fk_errors = len(cur.execute("PRAGMA foreign_key_check;").fetchall())
    print(f"  PRAGMA integrity_check: {integrity}")
    print(f"  PRAGMA foreign_key_check: {fk_errors} violations")

    # Table counts
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';").fetchall()]
    table_counts = {}
    for t in sorted(tables):
        cnt = cur.execute(f"SELECT count(*) FROM {t};").fetchone()[0]
        table_counts[t] = cnt
        print(f"    - {t}: {cnt:,}")

    # Epistemic enum validation
    if 'edges' in tables:
        invalid_epistemic = cur.execute(
            f"SELECT count(*) FROM edges WHERE epistemic_status NOT IN ({','.join('?' for _ in EPISTEMIC_CLASSES)});",
            tuple(EPISTEMIC_CLASSES)
        ).fetchone()[0]
        print(f"  Invalid epistemic_status count on edges: {invalid_epistemic}")

    # Fixture SLA lookup latency
    latencies = []
    if 'lexemes' in tables:
        for lemma in CORE_FIXTURES:
            t0 = time.perf_counter()
            cur.execute("SELECT id, lemma, pos FROM lexemes WHERE lemma = ?;", (lemma,)).fetchall()
            latencies.append((time.perf_counter() - t0) * 1000.0)
        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        print(f"  Fixture SLA Lookup: avg={avg_lat:.3f}ms, max={max_lat:.3f}ms (<250ms SLA: {'PASS' if max_lat < 250 else 'FAIL'})")

    conn.close()
    return table_counts

def main():
    dist_counts = audit_database(DIST_DB)
    print()
    root_counts = audit_database(ROOT_DB)

    print("\n=== PARITY EVALUATION ===")
    if dist_counts and root_counts:
        if dist_counts == root_counts:
            print("STATUS: PARITY_MATCH (Root matches Distribution)")
        else:
            print("STATUS: DIVERGENT (Root does not match Distribution)")
            for k in set(dist_counts) | set(root_counts):
                d_val = dist_counts.get(k, 0)
                r_val = root_counts.get(k, 0)
                if d_val != r_val:
                    print(f"  Mismatch in '{k}': Distribution={d_val:,} vs Root={r_val:,}")

if __name__ == '__main__':
    main()
