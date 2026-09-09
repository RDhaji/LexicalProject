import json
import sqlite3
import sys

db_path = "lexical_graph.db"
conn = sqlite3.connect(db_path)
conn.isolation_level = None
cur = conn.cursor()

try:
    cur.execute("BEGIN TRANSACTION;")

    # Schema inspection
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    cur.execute("PRAGMA table_info(edges)")
    edge_cols = {r[1] for r in cur.fetchall()}
    epistemic_col = "epistemic_class" if "epistemic_class" in edge_cols else "epistemic_status"
    meta_col = "metadata" if "metadata" in edge_cols else "features"

    cur.execute("SELECT COUNT(*) FROM lexemes")
    before_lexemes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM forms")
    before_forms = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM edges")
    before_edges = cur.fetchone()[0]

    # Staged row diff tracking
    inserted_lexemes, inserted_forms, inserted_edges = [], [], []
    deleted_edges = []

    # 1. Canonical Lexemes
    canonical_lexemes = [
        ("run:v", "run", "verb", "eng"),
        ("run:n", "run", "noun", "eng"),
        ("fast:adj", "fast", "adjective", "eng"),
        ("fast:adv", "fast", "adverb", "eng"),
        ("fast:v", "fast", "verb", "eng"),
        ("happy:adj", "happy", "adjective", "eng"),
        ("unhappy:adj", "unhappy", "adjective", "eng"),
        ("go:v", "go", "verb", "eng"),
        ("good:adj", "good", "adjective", "eng"),
        ("bad:adj", "bad", "adjective", "eng"),
        ("bank_1:n", "bank", "noun", "eng"),
        ("bank_2:n", "bank", "noun", "eng"),
        ("runner:n", "runner", "noun", "eng"),
        ("rerun:v", "rerun", "verb", "eng"),
        ("outrun:v", "outrun", "verb", "eng"),
        ("fastness:n", "fastness", "noun", "eng"),
        ("fasting:n", "fasting", "noun", "eng"),
        ("happiness:n", "happiness", "noun", "eng"),
        ("unhappily:adv", "unhappily", "adverb", "eng"),
        ("unhappiness:n", "unhappiness", "noun", "eng"),
        ("forgo:v", "forgo", "verb", "eng"),
        ("undergo:v", "undergo", "verb", "eng"),
        ("goodness:n", "goodness", "noun", "eng"),
        ("badness:n", "badness", "noun", "eng"),
        ("badly:adv", "badly", "adverb", "eng"),
        ("banker:n", "banker", "noun", "eng"),
        ("banking:n", "banking", "noun", "eng"),
        ("embankment:n", "embankment", "noun", "eng")
    ]
    for lid, lemma, pos, lang in canonical_lexemes:
        cur.execute("SELECT 1 FROM lexemes WHERE id = ?", (lid,))
        if not cur.fetchone():
            cur.execute("INSERT INTO lexemes (id, lemma, pos, language) VALUES (?, ?, ?, ?)", (lid, lemma, pos, lang))
            inserted_lexemes.append(lid)

    # 2. Canonical Forms
    canonical_forms = [
        ("runs", "runs", "eng"), ("running", "running", "eng"), ("ran", "ran", "eng"),
        ("run", "run", "eng"), ("faster", "faster", "eng"), ("fastest", "fastest", "eng"),
        ("fast", "fast", "eng"), ("fasts", "fasts", "eng"), ("fasting", "fasting", "eng"),
        ("fasted", "fasted", "eng"), ("happier", "happier", "eng"), ("happiest", "happiest", "eng"),
        ("unhappier", "unhappier", "eng"), ("unhappiest", "unhappiest", "eng"),
        ("goes", "goes", "eng"), ("going", "going", "eng"), ("went", "went", "eng"),
        ("gone", "gone", "eng"), ("better", "better", "eng"), ("best", "best", "eng"),
        ("worse", "worse", "eng"), ("worst", "worst", "eng"), ("bank", "bank", "eng"), ("banks", "banks", "eng")
    ]
    for fid, form, lang in canonical_forms:
        cur.execute("SELECT 1 FROM forms WHERE id = ?", (fid,))
        if not cur.fetchone():
            cur.execute("INSERT INTO forms (id, form, language) VALUES (?, ?, ?)", (fid, form, lang))
            inserted_forms.append(fid)

    # 3. Purge Transitive Skipping and Heuristic Leaks
    to_delete = [
        ("unhappily:adv", "happy:adj", "DERIVED_FROM"),
        ("car", "carpet", "DERIVED_FROM"),
        ("art", "article", "DERIVED_FROM")
    ]
    for src, tgt, rel in to_delete:
        cur.execute("SELECT 1 FROM edges WHERE source_id = ? AND target_id = ? AND relation_type = ?", (src, tgt, rel))
        if cur.fetchone():
            cur.execute("DELETE FROM edges WHERE source_id = ? AND target_id = ? AND relation_type = ?", (src, tgt, rel))
            deleted_edges.append(f"{src} -[:{rel}]-> {tgt}")

    # 4. Canonical HAS_FORM Edges (Disjoint POS sets)
    has_form_edges = [
        ("run:v", "runs"), ("run:v", "running"), ("run:v", "ran"),
        ("run:n", "run"), ("run:n", "runs"),
        ("fast:adj", "faster"), ("fast:adj", "fastest"),
        ("fast:adv", "fast"),
        ("fast:v", "fasts"), ("fast:v", "fasting"), ("fast:v", "fasted"),
        ("happy:adj", "happier"), ("happy:adj", "happiest"),
        ("unhappy:adj", "unhappier"), ("unhappy:adj", "unhappiest"),
        ("go:v", "goes"), ("go:v", "going"), ("go:v", "went"), ("go:v", "gone"),
        ("good:adj", "better"), ("good:adj", "best"),
        ("bad:adj", "worse"), ("bad:adj", "worst"),
        ("bank_1:n", "bank"), ("bank_1:n", "banks"),
        ("bank_2:n", "bank"), ("bank_2:n", "banks")
    ]
    for src, tgt in has_form_edges:
        cur.execute("SELECT 1 FROM edges WHERE source_id = ? AND target_id = ? AND relation_type = 'HAS_FORM'", (src, tgt))
        if not cur.fetchone():
            edge_id = f"{src}_HAS_FORM_{tgt}"
            cur.execute(f"""
                INSERT INTO edges (id, source_id, target_id, relation_type, {epistemic_col}, {meta_col}, provenance)
                VALUES (?, ?, ?, 'HAS_FORM', 'EXPLICIT', NULL, 'canonical_fixture')
            """, (edge_id, src, tgt))
            inserted_edges.append(edge_id)

    # 5. Canonical DERIVED_FROM Edges (Immediate Parentage Only)
    derived_edges = [
        ("run:n", "run:v", "EXPLICIT", json.dumps({"process": "conversion"})),
        ("runner:n", "run:v", "EXPLICIT", json.dumps({"process": "suffixation"})),
        ("rerun:v", "run:v", "EXPLICIT", json.dumps({"process": "prefixation"})),
        ("outrun:v", "run:v", "EXPLICIT", json.dumps({"process": "prefixation"})),
        ("fast:adv", "fast:adj", "EXPLICIT", json.dumps({"process": "conversion"})),
        ("fastness:n", "fast:adj", "EXPLICIT", json.dumps({"process": "suffixation"})),
        ("fasting:n", "fast:v", "EXPLICIT", json.dumps({"process": "suffixation"})),
        ("happiness:n", "happy:adj", "EXPLICIT", json.dumps({"process": "suffixation"})),
        ("unhappy:adj", "happy:adj", "INFERRED", json.dumps({"process": "prefixation"})),
        ("unhappily:adv", "unhappy:adj", "INFERRED", json.dumps({"process": "suffixation"})),
        ("unhappiness:n", "unhappy:adj", "INFERRED", json.dumps({"process": "suffixation"})),
        ("forgo:v", "go:v", "ATTESTED", json.dumps({"process": "prefixation"})),
        ("undergo:v", "go:v", "ATTESTED", json.dumps({"process": "prefixation"})),
        ("goodness:n", "good:adj", "ATTESTED", json.dumps({"process": "suffixation"})),
        ("badness:n", "bad:adj", "ATTESTED", json.dumps({"process": "suffixation"})),
        ("badly:adv", "bad:adj", "ATTESTED", json.dumps({"process": "suffixation"})),
        ("banker:n", "bank_1:n", "EXPLICIT", json.dumps({"process": "suffixation"})),
        ("banking:n", "bank_1:n", "EXPLICIT", json.dumps({"process": "suffixation"})),
        ("embankment:n", "bank_2:n", "EXPLICIT", json.dumps({"process": "prefixation_suffixation"}))
    ]
    for src, tgt, epistemic, meta in derived_edges:
        cur.execute("SELECT 1 FROM edges WHERE source_id = ? AND target_id = ? AND relation_type = 'DERIVED_FROM'", (src, tgt))
        if not cur.fetchone():
            edge_id = f"{src}_DERIVED_FROM_{tgt}"
            cur.execute(f"""
                INSERT INTO edges (id, source_id, target_id, relation_type, {epistemic_col}, {meta_col}, provenance)
                VALUES (?, ?, ?, 'DERIVED_FROM', ?, ?, 'canonical_fixture')
            """, (edge_id, src, tgt, epistemic, meta))
            inserted_edges.append(edge_id)

    # =================== PRE-COMMIT INVARIANT CHECKS ===================

    # Check 1: HAS_FORM endpoint invariant (source = Lexeme, target = Form)
    cur.execute("""
        SELECT source_id, target_id FROM edges 
        WHERE relation_type = 'HAS_FORM'
          AND (source_id NOT IN (SELECT id FROM lexemes) OR target_id NOT IN (SELECT id FROM forms))
    """)
    has_form_violations = cur.fetchall()
    if has_form_violations:
        raise ValueError(f"HAS_FORM endpoint invariant violated: {has_form_violations}")

    # Check 2: DERIVED_FROM endpoint invariant (source = Lexeme, target = Lexeme)
    cur.execute("""
        SELECT source_id, target_id FROM edges 
        WHERE relation_type = 'DERIVED_FROM'
          AND (source_id NOT IN (SELECT id FROM lexemes) OR target_id NOT IN (SELECT id FROM lexemes))
    """)
    derived_violations = cur.fetchall()
    if derived_violations:
        raise ValueError(f"DERIVED_FROM endpoint invariant violated: {derived_violations}")

    # Check 3: Immediate parentage invariant (happy -> unhappy -> unhappily; no shortcut)
    cur.execute("SELECT 1 FROM edges WHERE source_id='unhappily:adv' AND target_id='unhappy:adj' AND relation_type='DERIVED_FROM'")
    p1 = cur.fetchone()
    cur.execute("SELECT 1 FROM edges WHERE source_id='unhappy:adj' AND target_id='happy:adj' AND relation_type='DERIVED_FROM'")
    p2 = cur.fetchone()
    cur.execute("SELECT 1 FROM edges WHERE source_id='unhappily:adv' AND target_id='happy:adj' AND relation_type='DERIVED_FROM'")
    shortcut = cur.fetchone()
    if not p1 or not p2 or shortcut:
        raise ValueError(f"Immediate parentage invariant violated: p1={bool(p1)}, p2={bool(p2)}, shortcut={bool(shortcut)}")

    # Check 4: POS partition invariant (fast:adj and fast:v must have disjoint form paradigms)
    cur.execute("""
        SELECT f.id FROM forms f JOIN edges e ON e.target_id = f.id WHERE e.source_id = 'fast:adj' AND e.relation_type = 'HAS_FORM'
        INTERSECT
        SELECT f.id FROM forms f JOIN edges e ON e.target_id = f.id WHERE e.source_id = 'fast:v' AND e.relation_type = 'HAS_FORM'
    """)
    overlap = cur.fetchall()
    if overlap:
        raise ValueError(f"POS partition invariant violated: overlapping forms {overlap}")

    # Check 5: Epistemic enum invariant (Strict 5-enum closure; no CONFLICTING enum)
    cur.execute(f"""
        SELECT COUNT(*) FROM edges 
        WHERE {epistemic_col} NOT IN ('EXPLICIT', 'ATTESTED', 'INFERRED', 'GENERATED', 'UNCERTAIN')
           OR {epistemic_col} IS NULL
    """)
    invalid_epistemics = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM edges WHERE {epistemic_col} = 'CONFLICTING'")
    conflicting_as_enum = cur.fetchone()[0]
    if invalid_epistemics > 0 or conflicting_as_enum > 0:
        raise ValueError(f"Epistemic enum violated: {invalid_epistemics} invalid, {conflicting_as_enum} CONFLICTING as enum")

    # Check 6: DERIVED_FROM process metadata invariant
    cur.execute(f"""
        SELECT COUNT(*) FROM edges 
        WHERE source_id = 'run:n' AND target_id = 'run:v' AND relation_type = 'DERIVED_FROM'
          AND ({meta_col} IS NULL OR {meta_col} NOT LIKE '%"conversion"%')
    """)
    if cur.fetchone()[0] > 0:
        raise ValueError("Conversion process metadata missing on run:n -> run:v")

    # Check 7: Referential integrity (No dangling edge endpoints)
    node_id_query = "SELECT id FROM lexemes UNION SELECT id FROM forms"
    if "constructions" in tables:
        node_id_query += " UNION SELECT id FROM constructions"
    cur.execute(f"""
        SELECT id, source_id, target_id FROM edges
        WHERE source_id NOT IN ({node_id_query})
           OR target_id NOT IN ({node_id_query})
    """)
    dangling = cur.fetchall()
    if dangling:
        raise ValueError(f"Referential integrity violated: {len(dangling)} dangling edges found")

    cur.execute("COMMIT;")
    print("[SUCCESS] All 7 pre-commit invariants passed. Transaction committed.")

    # Reporting
    cur.execute("SELECT COUNT(*) FROM lexemes")
    after_lexemes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM forms")
    after_forms = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM edges")
    after_edges = cur.fetchone()[0]

    print(f"Nodes (Lexemes): {before_lexemes} -> {after_lexemes} ({after_lexemes - before_lexemes:+d})")
    print(f"Nodes (Forms):   {before_forms} -> {after_forms} ({after_forms - before_forms:+d})")
    print(f"Edges:           {before_edges} -> {after_edges} ({after_edges - before_edges:+d})")
    print(f"Inserted Lexemes ({len(inserted_lexemes)}): {inserted_lexemes}")
    print(f"Inserted Forms   ({len(inserted_forms)}): {inserted_forms}")
    print(f"Inserted Edges   ({len(inserted_edges)}): {inserted_edges}")
    print(f"Deleted Edges    ({len(deleted_edges)}): {deleted_edges}")

except Exception as err:
    cur.execute("ROLLBACK;")
    print(f"[FATAL] Migration failed pre-commit check: {err}", file=sys.stderr)
    print("[ROLLBACK] Database state reverted. 0 changes persisted.", file=sys.stderr)
    conn.close()
    sys.exit(1)

conn.close()
