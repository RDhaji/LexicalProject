import sqlite3
import os
import time

def run_adversarial_suite():
    start_time = time.time()
    db_path = "data/distribution/lexical_graph.db"
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Missing distribution DB: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    traps = {}

    # Trap 1: Substring/Orthographic Overlap False Friends (Invariant 4)
    false_pairs = [
        ("car", "carpet"),
        ("art", "article"),
        ("pan", "panic"),
        ("ear", "early"),
        ("rat", "ratio")
    ]
    cur.execute("""
        SELECT p.canonical_form, c.canonical_form
        FROM morphology_edges m
        JOIN lexemes p ON m.parent_id = p.id
        JOIN lexemes c ON m.child_id = c.id
        WHERE m.relation_type = 'DERIVED_FROM';
    """)
    derived_pairs = set(cur.fetchall())
    detected_overlaps = [pair for pair in false_pairs if pair in derived_pairs or (pair[1], pair[0]) in derived_pairs]
    traps["Trap 1 (Substring Overlaps)"] = (len(detected_overlaps) == 0)

    # Trap 2: Inverted Stemmer Heuristics / Over-Stemming (Invariant 5)
    invalid_roots = ["happi", "busi", "easi", "veri"]
    placeholders = ",".join(f"'{r}'" for r in invalid_roots)
    cur.execute(f"SELECT COUNT(*) FROM lexemes WHERE canonical_form IN ({placeholders});")
    traps["Trap 2 (Algorithmic Stems as Lexemes)"] = (cur.fetchone()[0] == 0)

    # Trap 3: Category Conflation (Invariant 6 - Inflection instantiating Lexeme or vice versa)
    cur.execute("""
        SELECT COUNT(*) FROM morphology_edges m
        JOIN forms f ON m.child_id = f.id
        WHERE m.relation_type = 'DERIVED_FROM';
    """)
    forms_in_derivation = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM morphology_edges m
        JOIN lexemes l ON m.child_id = l.id
        WHERE m.relation_type = 'HAS_FORM';
    """)
    lexemes_in_inflection = cur.fetchone()[0]
    traps["Trap 3 (Lexeme/Form & Inflection/Derivation Conflation)"] = (forms_in_derivation == 0 and lexemes_in_inflection == 0)

    # Trap 4: Phantom Nonce Affix Boundaries
    cur.execute("""
        SELECT COUNT(*) FROM morphology_edges
        WHERE relation_type = 'DERIVED_FROM'
          AND (affix IS NULL OR affix = '' OR LENGTH(affix) > 8);
    """)
    anomalous_affixes = cur.fetchone()[0]
    traps["Trap 4 (Affix Boundary Anomalies)"] = (anomalous_affixes == 0)

    # Trap 5: Epistemic Null or Out-of-Spec Values
    valid_classes = "('EXPLICIT', 'GENERATED', 'ATTESTED', 'INFERRED', 'UNCERTAIN')"
    cur.execute(f"SELECT COUNT(*) FROM morphology_edges WHERE epistemic_class NOT IN {valid_classes};")
    bad_morph_classes = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM lexemes WHERE epistemic_status NOT IN {valid_classes};")
    bad_lexeme_classes = cur.fetchone()[0]
    traps["Trap 5 (Epistemic Drift)"] = (bad_morph_classes == 0 and bad_lexeme_classes == 0)

    # Trap 6: Cyclic Derivational Parentage (Self-parenting or direct A->B and B->A)
    cur.execute("""
        SELECT COUNT(*) FROM morphology_edges WHERE parent_id = child_id;
    """)
    self_cycles = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM morphology_edges m1
        JOIN morphology_edges m2 ON m1.parent_id = m2.child_id AND m1.child_id = m2.parent_id
        WHERE m1.relation_type = 'DERIVED_FROM' AND m2.relation_type = 'DERIVED_FROM';
    """)
    mutual_cycles = cur.fetchone()[0]
    traps["Trap 6 (Cyclic Derivations)"] = (self_cycles == 0 and mutual_cycles == 0)

    conn.close()

    duration = time.time() - start_time
    passed = sum(1 for v in traps.values() if v)
    failed = len(traps) - passed

    for name, res in traps.items():
        print(f"{'PASS' if res else 'FAIL'} | {name}")

    print(f"\nTOTAL: {passed} passed, {failed} failed | Duration: {duration:.3f}s")

if __name__ == "__main__":
    run_adversarial_suite()
