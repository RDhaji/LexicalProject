import os
import sys
import glob

def preflight():
    sources = {
        "UniMorph": ("data/raw/eng.unimorph", 10 * 1024 * 1024),
        "Kaikki JSONL": ("data/raw/kaikki.org-dictionary-English.jsonl", 1024 * 1024 * 1024),
        "OEWN 2025": ("data/raw/oewn_2025/src/yaml", 0)
    }
    
    passed = True
    for name, (path, min_bytes) in sources.items():
        if not os.path.exists(path):
            print(f"FAIL | {name} missing at {path}")
            passed = False
            continue
        
        if os.path.isdir(path):
            yaml_files = glob.glob(os.path.join(path, "*.yaml"))
            if len(yaml_files) < 10:
                print(f"FAIL | {name} directory missing expected yaml content in {path} (found {len(yaml_files)})")
                passed = False
            else:
                print(f"PASS | {name} verified ({len(yaml_files)} YAML files in {path})")
        else:
            sz = os.path.getsize(path)
            if sz < min_bytes:
                print(f"FAIL | {name} size {sz} below minimum {min_bytes}")
                passed = False
            else:
                print(f"PASS | {name} verified ({sz / (1024*1024):.1f} MB)")

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    preflight()
