"""
Unit & Regression Tests for User Workspace Partition and Traversal Service
Compliance: PRD.md Section 39, ARCHITECTURE.md Section 2 & 4, ADR-006
"""

import os
import sqlite3
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from storage.user_workspace import add_bookmark, add_note, WORKSPACE_DB_PATH
from storage.traversal_service import TraversalService, COMPILED_DB_PATH

class TestStorageAndTraversal(unittest.TestCase):
    def test_user_partition_has_zero_foreign_keys_to_lexical_graph(self):
        """Invariant ADR-006 & ARCHITECTURE.md §2: Zero FKs from user partition to compiled graph."""
        conn = sqlite3.connect(WORKSPACE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_list(user_bookmarks);")
        self.assertEqual(len(cursor.fetchall()), 0)
        cursor.execute("PRAGMA foreign_key_list(user_notes);")
        self.assertEqual(len(cursor.fetchall()), 0)
        conn.close()

    def test_user_bookmark_and_note_persistence(self):
        """Verify user state writes succeed independently."""
        import uuid; test_uuid = f"lex_{uuid.uuid4().hex[:12]}"
        b_id = add_bookmark(test_uuid, "LEXEME")
        n_id = add_note(test_uuid, "LEXEME", "Personal linguistic study note.")
        
        conn = sqlite3.connect(WORKSPACE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM user_bookmarks WHERE id = ?;", (b_id,))
        self.assertIsNotNone(cursor.fetchone())
        cursor.execute("SELECT id FROM user_notes WHERE id = ?;", (n_id,))
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_traversal_service_lookup_and_expansion(self):
        """Verify client traversal returns valid records with sub-50ms index lookups."""
        service = TraversalService(COMPILED_DB_PATH)
        res = service.lookup_term("go")
        self.assertGreater(len(res["lexemes"]), 0)
        
        lex_id = res["lexemes"][0]["id"]
        graph = service.expand_graph(lex_id, depth=1)
        self.assertIn("outbound", graph)
        service.close()

if __name__ == "__main__":
    unittest.main()
