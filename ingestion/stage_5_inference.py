"""
Stage 5: Controlled Inference Engine
Compliance: PRD.md Section 2, ONTOLOGY.md Section 2 & 3, ADR-002, ADR-005, INGESTION_PIPELINE.md Stage 5
"""

import json
import os
import shutil
import sqlite3
import sys
import uuid

# Deterministic root injection for standalone script execution
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

STAGING_DIR = os.path.join(PROJECT_ROOT, "data", "staging")
MORPHOLOGY_DB_PATH = os.path.join(STAGING_DIR, "morphology_graph.db")
INFERRED_DB_PATH = os.path.join(STAGING_DIR, "inferred_graph.db")

NAMESPACE_LEXICAL = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")

def generate_uuid(natural_key: str) -> str:
    return str(uuid.uuid5(NAMESPACE_LEXICAL, natural_key))

def run_stage_5() -> bool:
    print("[STAGE 5] Initiating Controlled Inference Engine...")
    if not os.path.exists(MORPHOLOGY_DB_PATH):
        print(f"[ERROR] Stage 4 morphology database missing at {MORPHOLOGY_DB_PATH}", file=sys.stderr)
        return False

    os.makedirs(STAGING_DIR, exist_ok=True)
    shutil.copyfile(MORPHOLOGY_DB_PATH, INFERRED_DB_PATH)

    conn = sqlite3.connect(INFERRED_DB_PATH)
    cursor = conn.cursor()

    try:
        # Controlled Inference: Degree Progressions (INFLECTS_TO: CMPR -> SPRL)
        cursor.execute("""
            SELECT l.id, l.normalized_lemma, f.id, f.surface, f.features_json
            FROM resolved_relations r
            JOIN resolved_lexemes l ON r.subject_id = l.id
            JOIN resolved_forms f ON r.object_id = f.id
            WHERE r.relation_type = 'HAS_FORM' AND l.pos = 'ADJECTIVE';
        """)
        
        adjective_forms = cursor.fetchall()
        paradigms = {}
        for lex_id, lemma, form_id, surface, feat_json in adjective_forms:
            feats = json.loads(feat_json)
            degree = feats.get("degree")
            if degree:
                paradigms.setdefault(lex_id, {})[degree] = (form_id, surface)

        new_relations = []
        for lex_id, degrees in paradigms.items():
            if "COMPARATIVE" in degrees and "SUPERLATIVE" in degrees:
                cmpr_id, cmpr_surface = degrees["COMPARATIVE"]
                sprl_id, sprl_surface = degrees["SUPERLATIVE"]
                
                rel_natural_key = f"{cmpr_id}:INFLECTS_TO:{sprl_id}"
                rel_id = generate_uuid(rel_natural_key)
                new_relations.append((
                    rel_id,
                    "FORM",
                    cmpr_id,
                    "INFLECTS_TO",
                    "FORM",
                    sprl_id,
                    "GENERATED",
                    0.85,
                    "INFERRED"
                ))

        if new_relations:
            cursor.executemany("""
                INSERT OR REPLACE INTO resolved_relations
                (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, new_relations)
            print(f"  -> Generated {len(new_relations)} controlled INFLECTS_TO candidate edges.")

        conn.commit()
        print("[SUCCESS] Stage 5 finished. Inferred relations committed to data/staging/inferred_graph.db.")
        return True

    except Exception as e:
        print(f"[ERROR] Stage 5 failed: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if not run_stage_5():
        sys.exit(1)
