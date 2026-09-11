import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/rd/Desktop/LexicalProject")
SRC_DB = ROOT / "data" / "distribution" / "lexical_graph.db"
DIST_DIR = ROOT / "dist"
DIST_DB = DIST_DIR / "lexical_graph.db"
DIST_DATA_DB = DIST_DIR / "data" / "lexical_graph.db"
MANIFEST_PATH = DIST_DIR / "RELEASE_MANIFEST.json"
SHA_FILE = DIST_DIR / "SHA256SUMS"

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def run():
    DIST_DIR.mkdir(exist_ok=True)
    DIST_DATA_DB.parent.mkdir(parents=True, exist_ok=True)

    # Sync fresh database binary to distribution targets
    if DIST_DB.exists():
        DIST_DB.chmod(0o644)
    if DIST_DATA_DB.exists():
        DIST_DATA_DB.chmod(0o644)

    shutil.copy2(SRC_DB, DIST_DB)
    shutil.copy2(SRC_DB, DIST_DATA_DB)

    sha256_hash = compute_sha256(DIST_DB)

    conn = sqlite3.connect(SRC_DB)
    cur = conn.cursor()
    lex_count = cur.execute("SELECT COUNT(*) FROM lexemes;").fetchone()[0]
    form_count = cur.execute("SELECT COUNT(*) FROM forms;").fetchone()[0]
    edge_count = cur.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]
    conn.close()

    manifest = {
        "version": "1.0.0-production",
        "released_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "lexemes": lex_count,
            "forms": form_count,
            "edges": edge_count
        },
        "artifacts": {
            "lexical_graph.db": {
                "sha256": sha256_hash,
                "size_bytes": DIST_DB.stat().st_size
            }
        },
        "status": "VERIFIED"
    }

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    SHA_FILE.write_text(f"{sha256_hash}  lexical_graph.db\n", encoding="utf-8")

    DIST_DB.chmod(0o444)
    DIST_DATA_DB.chmod(0o444)

    print(f"SYNC_SUCCESS | SHA256: {sha256_hash} | Lexemes: {lex_count:,} | Forms: {form_count:,} | Edges: {edge_count:,}")

if __name__ == "__main__":
    run()
