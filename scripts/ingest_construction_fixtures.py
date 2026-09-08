import sqlite3, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
db_path = ROOT / "data" / "lexical_graph.db"

constructions = [
    ("cxn_intransitive_motion", "Intransitive Motion Construction", "Schematic pairing: [Subj V Path/Dir] encoding directed motion"),
    ("cxn_resultative", "Resultative Construction", "Schematic pairing: [Subj V Obj Obl/Adj] encoding caused state change")
]

# Realization edges linking canonical fixtures to abstract constructions (Invariant 6 & ADR-008)
realizations = [
    ("edge_realizes_run_motion", "lex_run", "LEXEME", "REALIZES", "cxn_intransitive_motion", "CONSTRUCTION", "EXPLICIT"),
    ("edge_realizes_go_motion", "lex_go", "LEXEME", "REALIZES", "cxn_intransitive_motion", "CONSTRUCTION", "EXPLICIT"),
    ("edge_realizes_run_res", "lex_run", "LEXEME", "REALIZES", "cxn_resultative", "CONSTRUCTION", "EXPLICIT")
]

with sqlite3.connect(db_path) as conn:
    c = conn.cursor()
    ts = int(time.time())
    for cid, name, desc in constructions:
        c.execute("INSERT OR REPLACE INTO constructions (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                  (cid, name, desc, ts))
    for eid, src, src_t, rel, tgt, tgt_t, ep in realizations:
        c.execute("""
            INSERT OR REPLACE INTO edges (id, source_id, source_type, relation_type, target_id, target_type, epistemic_class, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (eid, src, src_t, rel, tgt, tgt_t, ep, ts))

print("[INGEST OK] Canonical construction layer fixtures and REALIZES edges ingested.")
