"""
Milestone M10: Full-Corpus Ingestion & Streaming Scale-Up Acceptance Suite
Verifies full-corpus staging metrics, source isolation, and vertical fixture coverage.
"""

import os
import sqlite3
import pytest

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "staging", "staging_claims.db")

@pytest.fixture(scope="module")
def db_conn():
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()

def test_m10_lexical_entries_scale(db_conn):
    cur = db_conn.cursor()
    counts = dict(cur.execute("SELECT source, COUNT(*) FROM staging_lexical_entries GROUP BY source;").fetchall())
    assert counts.get("KAIKKI", 0) >= 1_400_000, f"Kaikki scale shortfall: {counts.get('KAIKKI')}"
    assert counts.get("OEWN_2025", 0) >= 100_000, f"OEWN scale shortfall: {counts.get('OEWN_2025')}"
    assert sum(counts.values()) >= 1_500_000

def test_m10_inflections_scale(db_conn):
    cur = db_conn.cursor()
    counts = dict(cur.execute("SELECT source, COUNT(*) FROM staging_inflections GROUP BY source;").fetchall())
    assert counts.get("UNIMORPH", 0) >= 1_000_000, f"UniMorph scale shortfall: {counts.get('UNIMORPH')}"

def test_m10_semantics_scale(db_conn):
    cur = db_conn.cursor()
    counts = dict(cur.execute("SELECT source, COUNT(*) FROM staging_semantic_relations GROUP BY source;").fetchall())
    assert counts.get("OEWN_2025", 0) >= 400_000, f"OEWN semantic relations scale shortfall: {counts.get('OEWN_2025')}"

def test_m10_vertical_slice_coverage(db_conn):
    cur = db_conn.cursor()
    cols = [c[1] for c in cur.execute("PRAGMA table_info(staging_lexical_entries);").fetchall()]
    lemma_col = "lemma" if "lemma" in cols else cols[1]
    fixtures = ["run", "fast", "happy", "go", "good", "bad", "bank"]
    for f in fixtures:
        row = cur.execute(f"SELECT 1 FROM staging_lexical_entries WHERE {lemma_col} = ? LIMIT 1;", (f,)).fetchone()
        assert row is not None, f"Vertical fixture '{f}' missing from staging entries"

def test_m10_source_epistemic_integrity(db_conn):
    cur = db_conn.cursor()
    for tbl in ["staging_lexical_entries", "staging_inflections", "staging_semantic_relations"]:
        null_count = cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE source IS NULL OR source = '';").fetchone()[0]
        assert null_count == 0, f"Source missing or empty in {tbl}"
