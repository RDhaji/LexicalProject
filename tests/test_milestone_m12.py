"""
Milestone M12 Acceptance Suite: Production CI Pipeline, Containerization & Automated Gate Audits
"""
import os, sqlite3, time, pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEX_DB = os.path.join(ROOT_DIR, "data", "distribution", "lexical_graph.db")
USER_DB = os.path.join(ROOT_DIR, "data", "distribution", "user_workspace.db")

def test_containerization_artifacts():
    dockerfile = os.path.join(ROOT_DIR, "Dockerfile")
    dockerignore = os.path.join(ROOT_DIR, ".dockerignore")
    assert os.path.exists(dockerfile), "Dockerfile missing"
    assert os.path.exists(dockerignore), ".dockerignore missing"
    with open(dockerfile) as f:
        df = f.read()
    assert "FROM " in df and "CMD " in df, "Malformed Dockerfile"

def test_ci_workflow_artifacts():
    ci_path = os.path.join(ROOT_DIR, ".github", "workflows", "ci.yml")
    assert os.path.exists(ci_path), "CI workflow file missing"
    with open(ci_path) as f:
        ci = f.read()
    assert "actions/checkout" in ci and "pytest" in ci, "Malformed CI workflow"

def test_automated_gate_a_ontology_conformance():
    conn = sqlite3.connect(LEX_DB)
    cols = [c[1] for c in conn.execute("PRAGMA table_info(edges)").fetchall()]
    assert any("rel" in c or "type" in c for c in cols), "Gate A Failed: Missing relation column"
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "Gate A: Integrity check failed"

def test_automated_gate_b_user_partition_isolation():
    u_conn = sqlite3.connect(USER_DB)
    for (tbl,) in u_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        fks = u_conn.execute(f"PRAGMA foreign_key_list({tbl})").fetchall()
        assert not any("lexic" in str(fk).lower() for fk in fks), f"Gate B: FK leak in {tbl}"

def test_automated_gate_c_zero_dangling_edges():
    conn = sqlite3.connect(LEX_DB)
    valid_ids = {r[0] for t in ["lexemes", "forms"] for r in conn.execute(f"SELECT id FROM {t}").fetchall()}
    cur = conn.cursor()
    edge_cols = [c[1] for c in cur.execute("PRAGMA table_info(edges)").fetchall()]
    src_c = "source_id" if "source_id" in edge_cols else edge_cols[1]
    tgt_c = "target_id" if "target_id" in edge_cols else edge_cols[2]
    dangling = [r for r in cur.execute(f"SELECT id, {src_c}, {tgt_c} FROM edges").fetchall() if r[1] not in valid_ids or r[2] not in valid_ids]
    assert len(dangling) == 0, f"Gate C: {len(dangling)} dangling edges found"

def test_automated_gate_d_and_e_fixture_and_latency_sla():
    conn = sqlite3.connect(LEX_DB)
    cur = conn.cursor()
    fixtures = ["run", "fast", "happy", "go", "good", "bad", "bank"]
    latencies = []
    for f in fixtures:
        t0 = time.perf_counter()
        row = cur.execute("SELECT id FROM lexemes WHERE lemma = ? LIMIT 1", (f,)).fetchone()
        assert row is not None, f"Gate D: Missing fixture {f}"
        cur.execute("SELECT target_id, relation_type FROM edges WHERE source_id = ? LIMIT 10", (row[0],)).fetchall()
        latencies.append((time.perf_counter() - t0) * 1000)
    assert max(latencies) < 250, f"Gate E Failed: Latency {max(latencies):.2f}ms >= 250ms"
