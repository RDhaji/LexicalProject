"""
Stage 2: Canonical Normalization & Alignment
Compliance: PRD.md Section 2, ONTOLOGY.md Section 1, ADR-001, ADR-003, INGESTION_PIPELINE.md Stage 2
"""

import json
import os
import sqlite3
import sys
import unicodedata

STAGING_DIR = "data/staging"
STAGING_DB_PATH = os.path.join(STAGING_DIR, "claims.db")
NORMALIZED_DB_PATH = os.path.join(STAGING_DIR, "normalized_records.db")

POS_MAP = {
    # Open English WordNet POS mappings
    "n": "NOUN",
    "v": "VERB",
    "a": "ADJECTIVE",
    "s": "ADJECTIVE",  # Satellite adjective in WordNet -> ADJECTIVE
    "r": "ADVERB",
    # Kaikki Wiktionary POS mappings
    "noun": "NOUN",
    "verb": "VERB",
    "adj": "ADJECTIVE",
    "adjective": "ADJECTIVE",
    "adv": "ADVERB",
    "adverb": "ADVERB",
    "pron": "PRONOUN",
    "pronoun": "PRONOUN",
    "det": "DETERMINER",
    "determiner": "DETERMINER",
    "prep": "PREPOSITION",
    "preposition": "PREPOSITION",
    "conj": "CONJUNCTION",
    "conjunction": "CONJUNCTION",
    "intj": "INTERJECTION",
    "interjection": "INTERJECTION",
    "num": "NUMERAL",
    "numeral": "NUMERAL",
    "part": "PARTICLE",
    "particle": "PARTICLE"
}

def normalize_text(text: str) -> str:
    """Applies Unicode NFC normalization, trims whitespace, and folds case."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text.strip())
    return normalized.lower()

def map_pos(raw_pos: str) -> str:
    """Maps raw source POS tag to ONTOLOGY.md canonical enumeration."""
    cleaned = raw_pos.strip().lower()
    return POS_MAP.get(cleaned, "OTHER")

def parse_unimorph_features(feature_str: str) -> dict:
    """Parses semicolon-delimited UniMorph bundle into structured feature attributes."""
    tokens = feature_str.strip().split(";")
    features = {"raw_features": feature_str}
    
    pos_token = tokens[0] if tokens else ""
    if pos_token == "V":
        features["pos"] = "VERB"
    elif pos_token == "N":
        features["pos"] = "NOUN"
    elif pos_token == "ADJ":
        features["pos"] = "ADJECTIVE"

    for t in tokens:
        if t == "PST":
            features["tense"] = "PAST"
        elif t == "PRS":
            features["tense"] = "PRESENT"
        elif t == "PL":
            features["number"] = "PLURAL"
        elif t == "SG":
            features["number"] = "SINGULAR"
        elif t == "1":
            features["person"] = "FIRST"
        elif t == "2":
            features["person"] = "SECOND"
        elif t == "3":
            features["person"] = "THIRD"
        elif t == "CMPR":
            features["degree"] = "COMPARATIVE"
        elif t == "SPRL":
            features["degree"] = "SUPERLATIVE"
        elif t == "PTCP":
            features["aspect"] = "PARTICIPLE"

    return features

def init_normalized_db(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS normalized_lexemes (
            claim_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            raw_lemma TEXT NOT NULL,
            normalized_lemma TEXT NOT NULL,
            canonical_pos TEXT NOT NULL,
            raw_payload TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS normalized_forms (
            claim_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            raw_lemma TEXT NOT NULL,
            normalized_lemma TEXT NOT NULL,
            surface TEXT NOT NULL,
            features_json TEXT NOT NULL
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_norm_lexeme_lemma ON normalized_lexemes(normalized_lemma);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_norm_form_lemma ON normalized_forms(normalized_lemma);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_norm_form_surface ON normalized_forms(surface);")
    conn.commit()

def run_stage_2() -> bool:
    print("[STAGE 2] Initiating canonical normalization & alignment...")
    if not os.path.exists(STAGING_DB_PATH):
        print(f"[ERROR] Staging database not found at {STAGING_DB_PATH}", file=sys.stderr)
        return False

    os.makedirs(STAGING_DIR, exist_ok=True)
    claims_conn = sqlite3.connect(STAGING_DB_PATH)
    claims_cursor = claims_conn.cursor()

    norm_conn = sqlite3.connect(NORMALIZED_DB_PATH)
    init_normalized_db(norm_conn)
    norm_cursor = norm_conn.cursor()

    try:
        # 1. Normalize Lexical Claims (WordNet + Wiktionary Kaikki)
        claims_cursor.execute("""
            SELECT id, source, subject, predicate, object_json 
            FROM staging_claims 
            WHERE claim_type IN ('LEXICAL_ENTRY', 'LEXICAL_RECORD')
        """)
        
        lexeme_rows = []
        for claim_id, source, subject, predicate, obj_str in claims_cursor.fetchall():
            norm_lemma = normalize_text(subject)
            obj = json.loads(obj_str)
            raw_pos = obj.get("pos", "")
            canonical_pos = map_pos(raw_pos)

            lexeme_rows.append((
                claim_id, source, subject, norm_lemma, canonical_pos, obj_str
            ))

        norm_cursor.executemany("""
            INSERT OR REPLACE INTO normalized_lexemes 
            (claim_id, source, raw_lemma, normalized_lemma, canonical_pos, raw_payload)
            VALUES (?, ?, ?, ?, ?, ?)
        """, lexeme_rows)
        print(f"  -> Normalized {len(lexeme_rows)} canonical lexeme records.")

        # 2. Normalize Inflection Claims (UniMorph)
        claims_cursor.execute("""
            SELECT id, source, subject, object_json 
            FROM staging_claims 
            WHERE source = 'UNIMORPH_ENG' AND predicate = 'HAS_INFLECTION'
        """)

        form_rows = []
        for claim_id, source, subject, obj_str in claims_cursor.fetchall():
            norm_lemma = normalize_text(subject)
            obj = json.loads(obj_str)
            surface = normalize_text(obj.get("surface", ""))
            raw_features = obj.get("features", "")
            features_dict = parse_unimorph_features(raw_features)

            form_rows.append((
                claim_id, source, subject, norm_lemma, surface, json.dumps(features_dict)
            ))

        norm_cursor.executemany("""
            INSERT OR REPLACE INTO normalized_forms 
            (claim_id, source, raw_lemma, normalized_lemma, surface, features_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, form_rows)
        print(f"  -> Normalized {len(form_rows)} inflectional form records.")

        norm_conn.commit()
        print("[SUCCESS] Stage 2 finished. Canonical tables built at data/staging/normalized_records.db.")
        return True

    except Exception as e:
        print(f"[ERROR] Stage 2 failed: {e}", file=sys.stderr)
        return False
    finally:
        claims_conn.close()
        norm_conn.close()

if __name__ == "__main__":
    if not run_stage_2():
        sys.exit(1)
