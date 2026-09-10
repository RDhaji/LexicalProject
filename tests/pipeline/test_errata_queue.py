import os
import sqlite3
import pytest
from packages.pipeline.src.errata_processor import process_pending_errata

@pytest.fixture
def test_db(tmp_path):
    db_path = str(tmp_path / "test_lexical_graph.db")
    conn = sqlite3.connect(db_path)
    mig_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "migrations", "003_create_errata_queue.sql"))
    with open(mig_path) as f:
        conn.executescript(f.read())
    conn.execute("""
        CREATE TABLE edges (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            epistemic_class TEXT NOT NULL CHECK(epistemic_class IN ('EXPLICIT','GENERATED','ATTESTED','INFERRED','UNCERTAIN')),
            created_at INTEGER NOT NULL
        );
    """)
    fixtures = [
        ('e_run', 'lex_run', 'run', 'UNRESOLVED_CLAIM', '{"source": "wiktionary"}', '{"source": "wordnet"}', 'UNCERTAIN', 'PENDING'),
        ('e_fast', 'lex_fast', 'fast', 'MISSING_ETYMOLOGY', '{"source": "wiktionary"}', None, 'UNCERTAIN', 'PENDING'),
        ('e_happy', 'lex_happy', 'happy', 'UNRESOLVED_CLAIM', '{"source": "wiktionary"}', '{"source": "oed"}', 'UNCERTAIN', 'PENDING'),
        ('e_go', 'lex_go', 'go', 'MISSING_ETYMOLOGY', '{"source": "etymonline"}', None, 'UNCERTAIN', 'PENDING'),
        ('e_good', 'lex_good', 'good', 'UNRESOLVED_CLAIM', '{"source": "wiktionary"}', '{"source": "oed"}', 'UNCERTAIN', 'PENDING'),
        ('e_bad', 'lex_bad', 'bad', 'MISSING_ETYMOLOGY', '{"source": "etymonline"}', None, 'UNCERTAIN', 'PENDING'),
        ('e_bank', 'lex_bank', 'bank', 'UNRESOLVED_CLAIM', '{"source": "etymonline"}', '{"source": "oed"}', 'UNCERTAIN', 'PENDING'),
    ]
    conn.executemany("""
        INSERT INTO errata_queue (id, target_entity_id, target_lemma, conflict_type, source_a_claim, source_b_claim, epistemic_class, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, fixtures)
    conn.commit()
    conn.close()
    return db_path

def test_fixture_lexemes_errata_processing(test_db):
    processed = process_pending_errata(test_db)
    assert processed == 7
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT status, count(*) FROM errata_queue GROUP BY status")
    counts = dict(cursor.fetchall())
    assert counts.get('RESOLVED_CONFLICT_PRESERVED') == 4
    assert counts.get('RESOLVED_UNATTESTED') == 3
    cursor.execute("SELECT DISTINCT epistemic_class FROM errata_queue")
    assert [r[0] for r in cursor.fetchall()] == ['UNCERTAIN']
    conn.close()
