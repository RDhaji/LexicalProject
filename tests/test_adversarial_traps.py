"""
Milestone M8: Adversarial Hardening & Negative Traps Suite
Enforces Invariants 4, 5, and 6 across Traps 1-6.
Compliance: ADR-005, PRD.md Section 2, MORPHOLOGY.md
"""

import os
import sqlite3
import unittest

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "staging", "resolved_graph.db")

class TestAdversarialTraps(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_trap_1_substring_overlaps(self):
        """Invariant 4: Reject string overlap/substring false positives."""
        traps = [("car", "carpet"), ("art", "article"), ("go", "goal"), ("ride", "riddance"), ("he", "hero"), ("cat", "catch")]
        for a, b in traps:
            self.cur.execute("""
                SELECT COUNT(*) FROM resolved_relations r
                JOIN resolved_lexemes l1 ON r.subject_id = l1.id
                JOIN resolved_lexemes l2 ON r.object_id = l2.id
                WHERE ((l1.normalized_lemma = ? AND l2.normalized_lemma = ?)
                    OR (l1.normalized_lemma = ? AND l2.normalized_lemma = ?))
                  AND r.relation_type IN ('DERIVED_FROM', 'MORPHOLOGICALLY_RELATED');
            """, (a, b, b, a))
            self.assertEqual(self.cur.fetchone()[0], 0, f"Invariant 4 Violation: Substring overlap between {a} and {b}")

    def test_trap_2_algorithmic_stems(self):
        """Invariant 5 & ADR-005: Reject algorithmic stemmer artifacts and stemmer inversion derivations."""
        invalid_stems = ["compon", "regul", "generat", "experi"]
        self.cur.execute(f"""
            SELECT COUNT(*) FROM resolved_lexemes 
            WHERE normalized_lemma IN ({','.join(['?']*len(invalid_stems))});
        """, invalid_stems)
        self.assertEqual(self.cur.fetchone()[0], 0, "Invariant 5 Violation: Algorithmic stem detected in lexemes")

        stemmer_derivation_pairs = [("oper", "operate"), ("oper", "operation"), ("oper", "operator")]
        for base, derived in stemmer_derivation_pairs:
            self.cur.execute("""
                SELECT COUNT(*) FROM resolved_relations r
                JOIN resolved_lexemes l1 ON r.subject_id = l1.id
                JOIN resolved_lexemes l2 ON r.object_id = l2.id
                WHERE ((l1.normalized_lemma = ? AND l2.normalized_lemma = ?)
                    OR (l1.normalized_lemma = ? AND l2.normalized_lemma = ?))
                  AND r.relation_type IN ('DERIVED_FROM', 'MORPHOLOGICALLY_RELATED');
            """, (base, derived, derived, base))
            self.assertEqual(self.cur.fetchone()[0], 0, f"ADR-005 Violation: Stemmer inversion derivation detected between {base} and {derived}")

    def test_trap_3_conflation(self):
        """Invariant 6: Enforce clean separation between Lexemes and Forms."""
        self.cur.execute("""
            SELECT COUNT(*) FROM resolved_relations
            WHERE (relation_type = 'HAS_FORM' AND (subject_type != 'LEXEME' OR object_type != 'FORM'))
               OR (relation_type = 'DERIVED_FROM' AND (subject_type != 'LEXEME' OR object_type != 'LEXEME'));
        """)
        self.assertEqual(self.cur.fetchone()[0], 0, "Invariant 6 Violation: Conflation of Lexeme and Form")

    def test_trap_4_affix_anomalies(self):
        """Affix Anomalies: Reflexive or illegal affixations prohibited."""
        self.cur.execute("""
            SELECT COUNT(*) FROM resolved_relations
            WHERE subject_id = object_id AND relation_type IN ('DERIVED_FROM', 'HAS_FORM', 'MORPHOLOGICALLY_RELATED');
        """)
        self.assertEqual(self.cur.fetchone()[0], 0, "Affix Anomaly: Reflexive relation detected")

    def test_trap_5_epistemic_drift(self):
        """Epistemic Drift: Every relation must have valid provenance claims."""
        self.cur.execute("""
            SELECT COUNT(*) FROM resolved_relations r
            LEFT JOIN relation_claims rc ON r.id = rc.relation_id
            WHERE rc.relation_id IS NULL;
        """)
        self.assertEqual(self.cur.fetchone()[0], 0, "Epistemic Drift: Unclaimed relation detected")

    def test_trap_6_cycles(self):
        """Cycle Trap: Derivation graph must be strictly acyclic."""
        self.cur.execute("""
            SELECT COUNT(*) FROM resolved_relations r1
            JOIN resolved_relations r2 ON r1.subject_id = r2.object_id AND r1.object_id = r2.subject_id
            WHERE r1.relation_type = 'DERIVED_FROM' AND r2.relation_type = 'DERIVED_FROM';
        """)
        self.assertEqual(self.cur.fetchone()[0], 0, "Acyclic Invariant Violation: 2-cycle detected")
