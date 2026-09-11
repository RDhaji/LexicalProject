import subprocess, time, json, os, yaml, sqlite3

def run_step(name, cmd, parse_status_fn=None):
    t0 = time.perf_counter()
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    status = "PASS" if p.returncode == 0 else "FAIL"
    if parse_status_fn:
        status = parse_status_fn(p.returncode, p.stdout, p.stderr)
    return {
        "gate": name,
        "command": cmd,
        "exit_code": p.returncode,
        "runtime_sec": round(dt, 3),
        "status": status,
        "stdout_tail": p.stdout.strip().splitlines()[-5:] if p.stdout.strip() else [],
        "stderr_tail": p.stderr.strip().splitlines()[-5:] if p.stderr.strip() else []
    }

# 1. CI Workflow Validation (YAML structure, Node setup, WASM step, container job)
def parse_ci_status(code, out, err):
    if code != 0:
        return "FAIL"
    with open(".github/workflows/ci.yml") as f:
        doc = yaml.safe_load(f)
    steps = [s.get("name", "") + " " + s.get("run", "") for s in doc.get("jobs", {}).get("verify", {}).get("steps", [])]
    has_wasm = any("test_wasm_node_runner.js" in s for s in steps)
    has_node = any("actions/setup-node" in s for s in [st.get("uses", "") for st in doc.get("jobs", {}).get("verify", {}).get("steps", [])])
    has_docker = "container-build" in doc.get("jobs", {})
    return "PASS" if (has_wasm and has_node and has_docker) else "FAIL"

r_ci = run_step("CI_WORKFLOW_HARDENING", "python3 -c \"import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))\"", parse_ci_status)

# 2. Local Container Build Execution
def parse_docker_status(code, out, err):
    if code == 127 or "command not found" in err:
        return "UNKNOWN"
    return "PASS" if code == 0 else "FAIL"

r_docker = run_step("CONTAINER_BUILD_EXECUTION", "docker build -t lexical-explorer:m12-test -f Dockerfile .", parse_docker_status)

# 3. M12 Specific Pytest Suite
r_m12_pytest = run_step("M12_ACCEPTANCE_TESTS", "python3 -m pytest -v tests/test_milestone_m12.py")

# 4. Full Pytest Suite
r_full_pytest = run_step("FULL_REGRESSION_TEST_SUITE", "python3 -m pytest -q tests/")

# 5. SQLite WASM Node Execution Harness
r_wasm_runner = run_step("M11_WASM_CLIENT_HARNESS", "node scripts/test_wasm_node_runner.js")

# 6. Quality Gates A-G via m13_package_audit.py against data/distribution/lexical_graph.db
r_gate_audit = run_step("QUALITY_GATES_A_TO_G", "python3 scripts/m13_package_audit.py")

# 7. Drift and Maintenance checks
r_drift = run_step("DAY2_DRIFT_MONITOR", "python3 scripts/day2_drift_monitor.py")
r_maint = run_step("AUTONOMOUS_MAINTENANCE", "python3 scripts/ops_autonomous_maintenance.py")

# 8. Git Status and Diff Check
r_git = run_step("GIT_STATUS_AND_DIFF", "git status --short && git diff --stat .github/workflows/ci.yml")

gates = [r_ci, r_docker, r_m12_pytest, r_full_pytest, r_wasm_runner, r_gate_audit, r_drift, r_maint, r_git]
print(json.dumps(gates, indent=2))
