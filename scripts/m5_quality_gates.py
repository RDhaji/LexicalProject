import sqlite3
import time
import json

def run_quality_gates():
    start_time = time.time()
    db_path = "data/staging/staging_claims.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    gates = {}

    # Gate A: Referential Integrity (No dangling child_id / parent_id)
    cur.execute("""
        SELECT COUNT(*) FROM morphology_relations m
        LEFT JOIN resolved_entities r ON m.parent_id = r.resolved_id
        WHERE r.resolved_id IS NULL;
    """)
    dangling_parents = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM morphology_relations m
        LEFT JOIN forms f ON m.child_id = f.form_id
        WHERE m.relation_type = 'HAS_FORM' AND f.form_id IS NULL;
    """)
    dangling_forms = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM morphology_relations m
        LEFT JOIN resolved_entities r ON m.child_id = r.resolved_id
        WHERE m.relation_type = 'DERIVED_FROM' AND r.resolved_id IS NULL;
    """)
    dangling_derived = cur.fetchone()[0]

    gates['Gate A (Referential Integrity)'] = (dangling_parents == 0 and dangling_forms == 0 and dangling_derived == 0)

    # Gate B: Ontology Invariant 6 (Strict Inflection vs Derivation Separation)
    cur.execute("""
        SELECT COUNT(*) FROM morphology_relations
        WHERE relation_type = 'HAS_FORM' AND affix IS NOT NULL;
    """)
    inflections_with_affix = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM morphology_relations
        WHERE relation_type = 'DERIVED_FROM' AND morphosyntax_features IS NOT NULL;
    """)
    derivations_with_morph = cur.fetchone()[0]

    gates['Gate B (Morphology Separation)'] = (inflections_with_affix == 0 and derivations_with_morph == 0)

    # Gate C: Epistemic Classification Validity
    valid_classes = ('EXPLICIT', 'GENERATED', 'ATTESTED', 'INFERRED', 'UNCERTAIN')
    placeholders = ",".join(f"'{c}'" for c in valid_classes)
    cur.execute(f"SELECT COUNT(*) FROM morphology_relations WHERE epistemic_class NOT IN ({placeholders});")
    invalid_morph_epistemic = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) FROM resolved_entities WHERE epistemic_status NOT IN ({placeholders});")
    invalid_entity_epistemic = cur.fetchone()[0]

    gates['Gate C (Epistemic Classes)'] = (invalid_morph_epistemic == 0 and invalid_entity_epistemic == 0)

    # Gate D: Invariant 4 (No Substring/Stemming False Relations - check carpet/car, art/article)
    cur.execute("""
        SELECT COUNT(*) FROM morphology_relations m
        JOIN resolved_entities p ON m.parent_id = p.resolved_id
        JOIN resolved_entities c ON m.child_id = c.resolved_id
        WHERE (p.canonical_form = 'car' AND c.canonical_form = 'carpet')
           OR (p.canonical_form = 'art' AND c.canonical_form = 'article');
    """)
    false_relations = cur.fetchone()[0]
    gates['Gate D (No Pseudo-Stemming Traps)'] = (false_relations == 0)

    # Gate E: Crosswalk Bi-directional Traceability
    cur.execute("""
        SELECT COUNT(*) FROM entity_crosswalk c
        LEFT JOIN resolved_entities r ON c.resolved_id = r.resolved_id
        WHERE r.resolved_id IS NULL;
    """)
    unmapped_crosswalks = cur.fetchone()[0]
    gates['Gate E (Crosswalk Traceability)'] = (unmapped_crosswalks == 0)

    # Gate F: Fixture Coverage Completeness (All 7 fixture lemmas present with resolved lexemes)
    fixtures = ['run', 'fast', 'happy', 'go', 'good', 'bad', 'bank']
    cur.execute("SELECT DISTINCT canonical_form FROM resolved_entities WHERE canonical_form IN ({})".format(
        ",".join(f"'{f}'" for f in fixtures)
    ))
    covered = {row[0] for row in cur.fetchall()}
    gates['Gate F (Fixture Coverage)'] = (len(covered) == len(fixtures))

    # Gate G: Deterministic Identity Invariance (UUIDv5 idempotency check)
    cur.execute("SELECT resolved_id, canonical_form, pos, resolution_key FROM resolved_entities LIMIT 5;")
    sample_entities = cur.fetchall()
    import uuid
    ns = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    id_invariant = True
    for r_id, canon, pos, key in sample_entities:
        expected = str(uuid.uuid5(ns, key))
        if r_id != expected:
            id_invariant = False
            break
    gates['Gate G (Deterministic Identity)'] = id_invariant

    conn.close()

    duration = time.time() - start_time
    passed = sum(1 for v in gates.values() if v)
    failed = len(gates) - passed

    for k, v in gates.items():
        print(f"{'PASS' if v else 'FAIL'} | {k}")

    print(f"\nTOTAL: {passed} passed, {failed} failed | Duration: {duration:.3f}s")

if __name__ == "__main__":
    run_quality_gates()
