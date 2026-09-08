"""
Stage 0: Manifest Preflight & Source Checksum Verification
Compliance: PRD.md Section 2, DATA_SOURCES.md Section 2, Gate A
"""

import hashlib
import json
import os
import sys

MANIFEST_PATH = "data/sources/manifest.json"

def calculate_sha256(filepath: str, chunk_size: int = 65536) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()

def run_preflight() -> bool:
    print("[PREFLIGHT] Starting Stage 0: Manifest Checksum Verification...")
    if not os.path.exists(MANIFEST_PATH):
        print(f"[ERROR] Manifest file missing: {MANIFEST_PATH}")
        return False

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    all_passed = True
    for source_id, spec in manifest.get("sources", {}).items():
        path = spec["path"]
        expected_sha = spec["sha256"]

        if not os.path.exists(path):
            print(f"[MISSING] Source artifact {source_id} not found at {path}")
            all_passed = False
            continue

        actual_sha = calculate_sha256(path)
        if expected_sha.startswith("EXPECTED_SHA"):
            print(f"[WARN] Placeholder SHA configured for {source_id}. Attested SHA: {actual_sha}")
        elif actual_sha != expected_sha:
            print(f"[FAIL] Checksum mismatch for {source_id}!")
            print(f"       Expected: {expected_sha}")
            print(f"       Actual:   {actual_sha}")
            all_passed = False
        else:
            print(f"[PASS] {source_id.ljust(28)} | Checksum Verified: {actual_sha[:12]}...")

    return all_passed

if __name__ == "__main__":
    if not run_preflight():
        print("\n[HALT] Stage 0 Preflight verification failed. Pipeline stopped.")
        sys.exit(1)
    print("\n[SUCCESS] Stage 0 Preflight passed. Environment ready for Stage 1 streaming parsers.")
