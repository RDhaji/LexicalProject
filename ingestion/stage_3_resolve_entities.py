"""
Stage 3: Entity Resolution & Deterministic UUIDv5 Key Generation
Compliance: ONTOLOGY.md Section 1 & 2, ADR-001, ADR-002, ADR-003, INGESTION_PIPELINE.md Stage 3
"""

import json
import os
import sqlite3
import sys
import uuid

STAGING_DIR = "data/staging"
NORMALIZED_DB_PATH = os.path.join(STAGING_DIR, "normalized_records.db")
RESOLVED_DB_PATH = os.path.join(STAGING_DIR, "resolved_entities.db")

# Authoritative Namespace UUID from ONTOLOGY.md Section 1
NAMESPACE_LEXICAL = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")

def init_resolved_db(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resolved_lexemes (
            id TEXT PRIMARY KEY,
            lemma TEXT NOT NULL,
            normalized_lemma TEXT NOT NULL,
            language TEXT NOT NULL,
            pos TEXT NOT NULL,
            lexeme_key TEXT UNIQUE NOT NULL,
            source_presence TEXT NOT NULL,
            frequency_summary TEXT,
            status TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resolved_forms (
            id TEXT PRIMARY KEY,
            surface TEXT NOT NULL,
            normalized_surface TEXT NOT NULL,
            script TEXT NOT NULL,
            language TEXT NOT NULL,
            features_json TEXT NOT NULL,
            form_type TEXT NOT NULL,
            form_key TEXT UNIQUE NOT NULL,
            evidence TEXT NOT NULL,
            confidence REAL NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resolved_relations (
            id TEXT PRIMARY KEY,
            subject_type TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            resolution_status TEXT NOT NULL
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_res_lex_norm ON resolved_lexemes(normalized_lemma);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_res_form_surf ON resolved_forms(normalized_surface);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_res_rel_adj ON resolved_relations(subject_id, relation_type, object_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_res_rel_rev ON resolved_relations(object_id, relation_type, subject_id);")
    conn.commit()

def generate_uuid(natural_key: str) -> str:
    return str(uuid.uuid5(NAMESPACE_LEXICAL, natural_key))

def run_stage_3() -> bool:
    print("[STAGE 3] Initiating Entity Resolution & UUIDv5 Generation...")
    if not os.path.exists(NORMALIZED_DB_PATH):
        print(f"[ERROR] Normalized records database missing at {NORMALIZED_DB_PATH}", file=sys.stderr)
        return False

    os.makedirs(STAGING_DIR, exist_ok=True)
    norm_conn = sqlite3.connect(NORMALIZED_DB_PATH)
    norm_cursor = norm_conn.cursor()

    res_conn = sqlite3.connect(RESOLVED_DB_PATH)
    init_resolved_db(res_conn)
    res_cursor = res_conn.cursor()

    try:
        # 1. Resolve Lexemes (Unifying across OEWN, Kaikki, SUBTLEX)
        norm_cursor.execute("""
            SELECT raw_lemma, normalized_lemma, canonical_pos, source, raw_payload
            FROM normalized_lexemes
        """)
        
        lexemes_map = {}
        for raw_lemma, norm_lemma, pos, source, payload_str in norm_cursor.fetchall():
            lexeme_key = f"eng:{norm_lemma}:{pos}"
            if lexeme_key not in lexemes_map:
                lex_id = generate_uuid(lexeme_key)
                lexemes_map[lexeme_key] = {
                    "id": lex_id,
                    "lemma": raw_lemma,
                    "normalized_lemma": norm_lemma,
                    "language": "eng",
                    "pos": pos,
                    "lexeme_key": lexeme_key,
                    "sources": set(),
                    "status": "CANONICAL"
                }
            lexemes_map[lexeme_key]["sources"].add(source)

        lexeme_rows = [
            (
                data["id"],
                data["lemma"],
                data["normalized_lemma"],
                data["language"],
                data["pos"],
                data["lexeme_key"],
                json.dumps(sorted(list(data["sources"]))),
                json.dumps({}),
                data["status"]
            )
            for data in lexemes_map.values()
        ]

        res_cursor.executemany("""
            INSERT OR REPLACE INTO resolved_lexemes
            (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, frequency_summary, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, lexeme_rows)
        print(f"  -> Resolved and unified {len(lexeme_rows)} canonical Lexemes.")

        # 2. Resolve Forms & Generate HAS_FORM Relations
        norm_cursor.execute("""
            SELECT raw_lemma, normalized_lemma, surface, features_json
            FROM normalized_forms
        """)
        
        form_rows = []
        relation_rows = []
        forms_map = {}

        for raw_lemma, norm_lemma, surface, feat_json in norm_cursor.fetchall():
            features = json.loads(feat_json)
            raw_feats = features.get("raw_features", "")
            form_key = f"eng:{surface}:{raw_feats}"
            
            if form_key not in forms_map:
                form_id = generate_uuid(form_key)
                forms_map[form_key] = form_id
                form_type = "INFLECTED" if raw_feats else "BASE"
                form_rows.append((
                    form_id,
                    surface,
                    surface.lower(),
                    "Latn",
                    "eng",
                    feat_json,
                    form_type,
                    form_key,
                    "ATTESTED",
                    1.0
                ))

            form_id = forms_map[form_key]
            
            # Map Form back to its parent Lexeme
            lex_pos = features.get("pos", "")
            if not lex_pos:
                # Fallback to verb/noun detection based on inflection
                lex_pos = "VERB" if "V" in raw_feats else ("NOUN" if "N" in raw_feats else "ADJECTIVE")
            
            lexeme_key = f"eng:{norm_lemma}:{lex_pos}"
            if lexeme_key in lexemes_map:
                parent_lex_id = lexemes_map[lexeme_key]["id"]
                rel_natural_key = f"{parent_lex_id}:HAS_FORM:{form_id}"
                rel_id = generate_uuid(rel_natural_key)
                
                relation_rows.append((
                    rel_id,
                    "LEXEME",
                    parent_lex_id,
                    "HAS_FORM",
                    "FORM",
                    form_id,
                    "EXPLICIT",
                    1.0,
                    "RESOLVED"
                ))

        res_cursor.executemany("""
            INSERT OR REPLACE INTO resolved_forms
            (id, surface, normalized_surface, script, language, features_json, form_type, form_key, evidence, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, form_rows)
        print(f"  -> Materialized {len(form_rows)} canonical Form entities.")

        res_cursor.executemany("""
            INSERT OR REPLACE INTO resolved_relations
            (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, relation_rows)
        print(f"  -> Generated {len(relation_rows)} HAS_FORM ontological relations.")

        res_conn.commit()
        print("[SUCCESS] Stage 3 finished. Canonical entities committed to data/staging/resolved_entities.db.")
        return True

    except Exception as e:
        print(f"[ERROR] Stage 3 failed: {e}", file=sys.stderr)
        return False
    finally:
        norm_conn.close()
        res_conn.close()

if __name__ == "__main__":
    if not run_stage_3():
        sys.exit(1)
