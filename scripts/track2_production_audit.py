import os
import sqlite3
import json
import hashlib
import time

DIST_DB = "data/distribution/lexical_graph.db"
USER_DB = "data/distribution/user_workspace.db"
MANIFEST = "data/distribution/release_manifest.json"

FIXTURES = ["run", "fast", "happy", "go", "good", "bad", "bank"]

def run_audit():
    t0 = time.time()
    assert os.path.exists(DIST_DB), f"Missing {DIST_DB}"
    assert os.path.exists(USER_DB), f"Missing {USER_DB}"
    assert os.path.exists(MANIFEST), f"Missing {MANIFEST}"

    conn = sqlite3.connect(DIST_DB)
    cur = conn.cursor()

    # PRAGMA Integrity
    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchone()[0]
    assert integrity == "ok", f"Integrity check failed: {integrity}"

    # Invariant 7: Workspace Isolation Check
    u_conn = sqlite3.connect(USER_DB)
    u_cur = u_conn.cursor()
    u_cur.execute("SELECT sql FROM sqlite_master WHERE type='table';")
    user_schemas = " ".join([r[0] for r in u_cur.fetchall() if r[0]])
    assert "lexical_graph" not in user_schemas.lower(), "Invariant 7 violation: Cross-database foreign reference"
    u_conn.close()

    # Invariant 6: Form/Lexeme Separation in Pronunciations and Translations
    cur.execute("SELECT COUNT(*) FROM pronunciations WHERE target_type = 'LEXEME' AND target_id IN (SELECT id FROM forms);")
    assert cur.fetchone()[0] == 0, "Invariant 6 violation: Form linked as Lexeme in pronunciations"

    cur.execute("SELECT COUNT(*) FROM pronunciations WHERE target_type = 'FORM' AND target_id IN (SELECT id FROM lexemes);")
    assert cur.fetchone()[0] == 0, "Invariant 6 violation: Lexeme linked as Form in pronunciations"

    cur.execute("""
        SELECT COUNT(*) FROM edges e 
        WHERE e.relation_type = 'TRANSLATION_OF' 
        AND (e.source_id IN (SELECT id FROM forms) OR e.target_id IN (SELECT id FROM forms_es));
    """)
    assert cur.fetchone()[0] == 0, "Invariant 6 violation: Forms linked in cross-lingual TRANSLATION_OF"

    # Invariant 4: No heuristic phonetic edges in graph
    cur.execute("SELECT COUNT(*) FROM edges WHERE relation_type LIKE '%PHONETIC%' OR relation_type LIKE '%SOUNDEX%';")
    assert cur.fetchone()[0] == 0, "Invariant 4 violation: Phonetic similarity edge exists in graph"

    # 7 Vertical Fixtures Verification
    for fix in FIXTURES:
        cur.execute("SELECT COUNT(*) FROM lexemes WHERE lemma = ?", (fix,))
        assert cur.fetchone()[0] > 0, f"Fixture missing in lexemes: {fix}"

        cur.execute("""
            SELECT COUNT(*) FROM pronunciations p 
            JOIN lexemes l ON p.target_id = l.id 
            WHERE l.lemma = ?;
        """, (fix,))
        assert cur.fetchone()[0] > 0, f"Fixture missing pronunciation: {fix}"

        cur.execute("""
            SELECT COUNT(*) FROM search_phonetic_index spi 
            JOIN lexemes l ON spi.target_id = l.id 
            WHERE l.lemma = ?;
        """, (fix,))
        assert cur.fetchone()[0] > 0, f"Fixture missing phonetic index: {fix}"

        cur.execute("""
            SELECT COUNT(*) FROM edges e 
            JOIN lexemes l ON e.source_id = l.id 
            WHERE l.lemma = ? AND e.relation_type = 'TRANSLATION_OF';
        """, (fix,))
        assert cur.fetchone()[0] > 0, f"Fixture missing Spanish translation edge: {fix}"

    # Counts & Metrics
    cur.execute("SELECT COUNT(*) FROM lexemes;")
    lexeme_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM forms;")
    form_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM synsets;")
    synset_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM edges;")
    morph_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM semantic_edges;")
    sem_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pronunciations;")
    pron_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM search_phonetic_index;")
    phon_idx_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM lexemes_es;")
    lex_es_count = cur.fetchone()[0]

    conn.close()

    # Manifest Parity Verification
    with open(MANIFEST, "r") as f:
        manifest = json.load(f)

    def get_hash(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    current_hash = get_hash(DIST_DB)
    assert manifest["artifacts"]["lexical_graph.db"]["sha256"] == current_hash, "Manifest SHA-256 mismatch against lexical_graph.db"

    duration = time.time() - t0
    print(f"AUDIT_PASSED | Duration: {duration:.3f}s | Lexemes: {lexeme_count} | Forms: {form_count} | Pronunciations: {pron_count} | Phonetic Indices: {phon_idx_count} | Spanish Lexemes: {lex_es_count}")

if __name__ == "__main__":
    run_audit()
