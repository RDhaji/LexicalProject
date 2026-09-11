import os, sys, json, sqlite3

results = {
    "1_get_provenance_implemented": False,
    "2_ran_against_1_56gb_db": False,
    "3_zero_mocks_in_worker": False,
    "4_opfs_actual_runtime_path": False,
    "5_sw_offline_tested": False,
    "6_seven_fixtures_used": False,
    "7_benchmarks_reproducible": False
}

worker_path = "client/worker.js"
if os.path.exists(worker_path):
    with open(worker_path) as f:
        w_text = f.read()
    results["1_get_provenance_implemented"] = "GET_PROVENANCE" in w_text
    results["3_zero_mocks_in_worker"] = ("mock" not in w_text.lower()) and ("fallback" not in w_text.lower())
    results["4_opfs_actual_runtime_path"] = "opfs" in w_text.lower()

# Check runner script to see what DB was tested
runner_path = "scripts/test_wasm_node_runner.js"
if os.path.exists(runner_path):
    with open(runner_path) as f:
        r_text = f.read()
    results["2_ran_against_1_56gb_db"] = "lexical_graph.db" in r_text and "fixture_slice.db" not in r_text
    results["6_seven_fixtures_used"] = all(x in r_text for x in ["run", "fast", "happy", "go", "good", "bad", "bank"])

# Check SW test artifacts
results["5_sw_offline_tested"] = os.path.exists("tests/test_sw_offline.py") or os.path.exists("tests/test_sw.js")

print(json.dumps(results, indent=2))
