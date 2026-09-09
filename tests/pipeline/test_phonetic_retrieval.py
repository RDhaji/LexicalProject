import sqlite3
import pytest

DIST_DB = "data/distribution/lexical_graph.db"

def test_phonetic_schema_conformance():
    conn = sqlite3.connect(DIST_DB)
    cur = conn.cursor()
    
    cur.execute("PRAGMA table_info(pronunciations);")
    pron_cols = {row[1]: row[2] for row in cur.fetchall()}
    assert "id" in pron_cols
    assert "target_id" in pron_cols
    assert "target_type" in pron_cols
    assert "notation" in pron_cols
    assert "transcription" in pron_cols
    assert "epistemic_class" in pron_cols

    cur.execute("PRAGMA table_info(search_phonetic_index);")
    idx_cols = {row[1]: row[2] for row in cur.fetchall()}
    assert "phonetic_key" in idx_cols
    assert "target_id" in idx_cols
    assert "algorithm" in idx_cols
    assert "epistemic_class" in idx_cols
    conn.close()

def test_phonetic_vertical_fixtures():
    conn = sqlite3.connect(DIST_DB)
    cur = conn.cursor()

    fixtures = {
        "run": ("/ɹʌn/", "R AH1 N", "R500"),
        "fast": ("/fæst/", "F AE1 S T", "F230"),
        "happy": ("/ˈhæpi/", "HH AE1 P IY0", "H100"),
        "go": ("/ɡoʊ/", "G OW1", "G000"),
        "good": ("/ɡʊd/", "G UH1 D", "G300"),
        "bad": ("/bæd/", "B AE1 D", "B300"),
        "bank": ("/bæŋk/", "B AE1 NG K", "B520"),
    }

    for lemma, (ipa, arpabet, soundex) in fixtures.items():
        cur.execute("""
            SELECT p.notation, p.transcription, p.epistemic_class
            FROM pronunciations p
            JOIN lexemes l ON p.target_id = l.id
            WHERE l.lemma = ?
        """, (lemma,))
        records = cur.fetchall()
        assert len(records) > 0, f"Missing pronunciations for {lemma}"
        
        notations = {r[0]: r[1] for r in records}
        assert notations.get("IPA") == ipa
        assert notations.get("ARPABET") == arpabet

        cur.execute("""
            SELECT spi.phonetic_key, spi.algorithm, spi.epistemic_class
            FROM search_phonetic_index spi
            JOIN lexemes l ON spi.target_id = l.id
            WHERE l.lemma = ?
        """, (lemma,))
        idx_records = cur.fetchall()
        assert any(r[0] == soundex and r[1] == "SOUNDEX" and r[2] == "GENERATED" for r in idx_records)

    conn.close()

def test_phonetic_invariants():
    conn = sqlite3.connect(DIST_DB)
    cur = conn.cursor()
    # Invariant 4: search_phonetic_index must never exist in graph edges
    cur.execute("SELECT COUNT(*) FROM edges WHERE relation_type LIKE '%PHONETIC%' OR relation_type LIKE '%SOUNDEX%';")
    assert cur.fetchone()[0] == 0

    # Invariant 6: target_type separation
    cur.execute("""
        SELECT COUNT(*) FROM pronunciations p
        JOIN lexemes l ON p.target_id = l.id
        WHERE p.target_type != 'LEXEME';
    """)
    assert cur.fetchone()[0] == 0
    conn.close()
