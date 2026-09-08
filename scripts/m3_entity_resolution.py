import sqlite3
import uuid
import json
import time

NAMESPACE_LEXICAL = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

def generate_uuid5(namespace: uuid.UUID, key: str) -> str:
    return str(uuid.uuid5(namespace, key))

def run_resolution():
    start_time = time.time()
    db_path = "data/staging/staging_claims.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("DELETE FROM resolved_entities;")
    cur.execute("DELETE FROM entity_crosswalk;")

    entity_cache = {}
    resolved_count = 0
    crosswalk_count = 0

    # 1. Resolve from synsets table (M1 Semantic Backbone: members JSON array)
    cur.execute("SELECT id, pos, members FROM synsets;")
    synset_rows = cur.fetchall()
    for s_id, pos, members_raw in synset_rows:
        try:
            members = json.loads(members_raw) if members_raw else []
        except Exception:
            members = [m.strip() for m in members_raw.split(",") if m.strip()]
        
        pos_norm = pos.lower().strip()
        for member in members:
            canon = member.lower().strip()
            key = f"lexeme:{canon}:{pos_norm}"
            if key not in entity_cache:
                res_id = generate_uuid5(NAMESPACE_LEXICAL, key)
                entity_cache[key] = res_id
                cur.execute("""
                    INSERT INTO resolved_entities (resolved_id, canonical_form, pos, entity_type, epistemic_status, resolution_key)
                    VALUES (?, ?, ?, 'LEXEME', 'EXPLICIT', ?)
                """, (res_id, canon, pos_norm, key))
                resolved_count += 1
            else:
                res_id = entity_cache[key]

            cur.execute("""
                INSERT OR IGNORE INTO entity_crosswalk (source_table, source_id, resolved_id, epistemic_status)
                VALUES ('synsets', ?, ?, 'EXPLICIT')
            """, (str(s_id), res_id))
            crosswalk_count += 1

    # 2. Resolve from raw_lexical_entries (M2 Kaikki)
    cur.execute("SELECT id, lemma, pos FROM raw_lexical_entries;")
    kaikki_rows = cur.fetchall()
    for k_id, lemma, pos in kaikki_rows:
        canon = lemma.lower().strip()
        pos_norm = pos.lower().strip()
        key = f"lexeme:{canon}:{pos_norm}"
        if key not in entity_cache:
            res_id = generate_uuid5(NAMESPACE_LEXICAL, key)
            entity_cache[key] = res_id
            cur.execute("""
                INSERT INTO resolved_entities (resolved_id, canonical_form, pos, entity_type, epistemic_status, resolution_key)
                VALUES (?, ?, ?, 'LEXEME', 'EXPLICIT', ?)
            """, (res_id, canon, pos_norm, key))
            resolved_count += 1
        else:
            res_id = entity_cache[key]

        cur.execute("""
            INSERT OR IGNORE INTO entity_crosswalk (source_table, source_id, resolved_id, epistemic_status)
            VALUES ('raw_lexical_entries', ?, ?, 'ATTESTED')
        """, (str(k_id), res_id))
        crosswalk_count += 1

    # 3. Crosswalk raw_inflections (M2 UniMorph) to parent lexemes
    cur.execute("SELECT id, lemma, pos FROM raw_inflections;")
    unimorph_rows = cur.fetchall()
    for u_id, lemma, pos in unimorph_rows:
        canon = lemma.lower().strip()
        pos_norm = pos.lower().strip()
        key = f"lexeme:{canon}:{pos_norm}"
        if key not in entity_cache:
            res_id = generate_uuid5(NAMESPACE_LEXICAL, key)
            entity_cache[key] = res_id
            cur.execute("""
                INSERT INTO resolved_entities (resolved_id, canonical_form, pos, entity_type, epistemic_status, resolution_key)
                VALUES (?, ?, ?, 'LEXEME', 'EXPLICIT', ?)
            """, (res_id, canon, pos_norm, key))
            resolved_count += 1
        else:
            res_id = entity_cache[key]

        cur.execute("""
            INSERT OR IGNORE INTO entity_crosswalk (source_table, source_id, resolved_id, epistemic_status)
            VALUES ('raw_inflections', ?, ?, 'ATTESTED')
        """, (str(u_id), res_id))
        crosswalk_count += 1

    conn.commit()
    conn.close()
    duration = time.time() - start_time
    print(f"PASS | Entities resolved: {resolved_count} | Crosswalk edges: {crosswalk_count} | Duration: {duration:.3f}s")

if __name__ == "__main__":
    run_resolution()
