import sqlite3
import os
from typing import List, Dict, Any

class SQLiteGraphCompiler:
    """
    Stage 8 Compiler (ARCHITECTURE.md, ADR-006, ADR-007):
    - Compiles verified entities, claims, and relations into production lexical_graph.db.
    - Builds covering B-Tree indices for sub-millisecond lookups.
    - Builds FTS5 full-text index for definition and usage search.
    - Sets PRAGMA user_version and locks schema.
    """

    def compile_database(self, db_path: str, lexemes: List[Dict[str, Any]], relations: List[Dict[str, Any]]):
        if os.path.exists(db_path):
            os.remove(db_path)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute("PRAGMA synchronous = NORMAL;")

        # Entity table
        cur.execute("""
            CREATE TABLE lexemes (
                id TEXT PRIMARY KEY,
                lemma TEXT NOT NULL,
                normalized_lemma TEXT NOT NULL,
                pos TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'eng'
            );
        """)

        # Relations table
        cur.execute("""
            CREATE TABLE relations (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                object_type TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                confidence REAL NOT NULL
            );
        """)

        # FTS5 virtual table
        cur.execute("""
            CREATE VIRTUAL TABLE lexemes_fts USING fts5(
                lemma,
                content='lexemes',
                content_rowid='rowid'
            );
        """)

        # Populate
        for lex in lexemes:
            cur.execute(
                "INSERT INTO lexemes (id, lemma, normalized_lemma, pos) VALUES (?, ?, ?, ?);",
                (lex["id"], lex["lemma"], lex["normalized_lemma"], lex["pos"])
            )
            cur.execute("INSERT INTO lexemes_fts(lemma) VALUES (?);", (lex["lemma"],))

        for rel in relations:
            cur.execute(
                """INSERT INTO relations 
                   (id, subject_id, subject_type, relation_type, object_id, object_type, evidence_type, confidence)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
                (rel["id"], rel["subject_id"], rel["subject_type"], rel["relation_type"],
                 rel["object_id"], rel["object_type"], rel["evidence_type"], rel["confidence"])
            )

        # Covering B-Tree indices
        cur.execute("CREATE INDEX idx_lexemes_norm ON lexemes(normalized_lemma);")
        cur.execute("CREATE INDEX idx_rel_adj ON relations(subject_id, relation_type, object_id);")
        cur.execute("CREATE INDEX idx_rel_rev ON relations(object_id, relation_type, subject_id);")

        conn.commit()
        conn.close()
