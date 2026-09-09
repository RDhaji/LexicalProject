import sqlite3
import sys
import time

FIXTURES = ["run", "fast", "happy", "go", "good", "bad", "bank"]
STAGING_DB = "data/staging/staging_claims.db"
RESOLVED_DB = "data/staging/resolved_graph.db"
DIST_DB = "data/distribution/lexical_graph.db"

def validate_pipeline():
    t0 = time.perf_counter()
    errors = []

    # 1. Staging claims validation
    conn_stage = sqlite3.connect(STAGING_DB)
    cur_stage = conn_stage.cursor()
    for f in FIXTURES:
        raw_cnt = cur_stage.execute(
            "SELECT COUNT(*) FROM raw_claims WHERE subject_raw = ? OR payload_json LIKE ?",
            (f, f'%"{f}"%')
        ).fetchone()[0]
        if raw_cnt == 0:
            errors.append(f"[STAGING] Missing raw_claims for fixture: {f}")
    conn_stage.close()

    # 2. Resolved graph validation
    conn_res = sqlite3.connect(RESOLVED_DB)
    cur_res = conn_res.cursor()
    for f in FIXTURES:
        lex_cnt = cur_res.execute(
            "SELECT COUNT(*) FROM resolved_lexemes WHERE lemma = ?", (f,)
        ).fetchone()[0]
        if lex_cnt == 0:
            errors.append(f"[RESOLVED] Missing resolved_lexemes for fixture: {f}")
    conn_res.close()

    # 3. Distribution graph compilation validation
    conn_dist = sqlite3.connect(DIST_DB)
    cur_dist = conn_dist.cursor()
    for f in FIXTURES:
        lex_ids = [r[0] for r in cur_dist.execute(
            "SELECT id FROM lexemes WHERE lemma = ?", (f,)
        ).fetchall()]
        if not lex_ids:
            errors.append(f"[DIST] Missing compiled lexeme for fixture: {f}")
            continue

        placeholders = ",".join(["?"] * len(lex_ids))
        form_edges = cur_dist.execute(
            f"SELECT COUNT(*) FROM edges WHERE source_id IN ({placeholders}) AND relation_type = 'HAS_FORM'",
            lex_ids
        ).fetchone()[0]
        if form_edges == 0:
            errors.append(f"[DIST] Missing HAS_FORM edge for fixture: {f}")

        # Invariant 6: Lexeme vs Form ID space partition
        overlap = cur_dist.execute(
            "SELECT COUNT(*) FROM lexemes l JOIN forms f ON l.id = f.id WHERE l.lemma = ?", (f,)
        ).fetchone()[0]
        if overlap > 0:
            errors.append(f"[INVARIANT_6] Lexeme and Form ID collision detected for fixture: {f}")

    # Epistemic enum integrity across compiled edges
    invalid_epistemic = cur_dist.execute(
        "SELECT COUNT(*) FROM edges WHERE epistemic_status NOT IN ('EXPLICIT', 'GENERATED', 'ATTESTED', 'INFERRED', 'UNCERTAIN')"
    ).fetchone()[0]
    if invalid_epistemic > 0:
        errors.append(f"[EPISTEMIC] Found {invalid_epistemic} edges with invalid epistemic_status")

    conn_dist.close()

    duration = time.perf_counter() - t0
    if errors:
        print(f"PIPELINE_VALIDATION_FAILED | Duration: {duration:.2f}s | Errors: {len(errors)}")
        for err in errors[:10]:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print(f"PIPELINE_VALIDATION_PASSED | Duration: {duration:.2f}s | Fixtures: {len(FIXTURES)} validated across staging -> resolved -> dist")

if __name__ == "__main__":
    validate_pipeline()
