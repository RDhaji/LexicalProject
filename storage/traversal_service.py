"""
Client Traversal Service
Compliance: ARCHITECTURE.md Section 4, ADR-006
"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPILED_DB_PATH = os.path.join(PROJECT_ROOT, "data", "compiled", "lexical_graph.db")

class TraversalService:
    def __init__(self, db_path: str = COMPILED_DB_PATH):
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Compiled database missing at {db_path}")
        # Read-only URI mode to prevent client corruption
        self.conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row

    def lookup_term(self, term: str):
        normalized = term.strip().lower()
        cursor = self.conn.cursor()
        
        # 1. Direct Lexeme Lookup
        cursor.execute("""
            SELECT id, lemma, normalized_lemma, pos, source_presence, frequency_summary
            FROM lexemes
            WHERE normalized_lemma = ?;
        """, (normalized,))
        lexemes = [dict(row) for row in cursor.fetchall()]

        # 2. Direct Form Lookup (Surface realization)
        cursor.execute("""
            SELECT f.id, f.surface, f.features_json, r.subject_id as parent_lexeme_id
            FROM forms f
            JOIN relations r ON r.object_id = f.id AND r.relation_type = 'HAS_FORM'
            WHERE f.normalized_surface = ?;
        """, (normalized,))
        forms = [dict(row) for row in cursor.fetchall()]

        return {"term": term, "lexemes": lexemes, "forms": forms}

    def expand_graph(self, entity_id: str, depth: int = 1):
        if depth > 3:
            raise ValueError("Graph traversal bounded to depth <= 3 per ARCHITECTURE.md Section 4.")
            
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.relation_type, r.object_type, r.object_id, r.evidence_type, r.confidence
            FROM relations r
            WHERE r.subject_id = ?;
        """, (entity_id,))
        outbound = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT r.relation_type, r.subject_type, r.subject_id, r.evidence_type, r.confidence
            FROM relations r
            WHERE r.object_id = ?;
        """, (entity_id,))
        inbound = [dict(row) for row in cursor.fetchall()]

        return {"entity_id": entity_id, "outbound": outbound, "inbound": inbound}

    def close(self):
        self.conn.close()
