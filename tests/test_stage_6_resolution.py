import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.stage_6_resolution import ClaimResolutionEngine

class TestStage6Resolution(unittest.TestCase):

    def setUp(self):
        self.engine = ClaimResolutionEngine()

    def test_corroborated_claims_attested(self):
        claims = [
            {"claim_id": "c1", "asserted_value": "NOUN", "evidence_type": "EXPLICIT"},
            {"claim_id": "c2", "asserted_value": "NOUN", "evidence_type": "EXPLICIT"}
        ]
        res = self.engine.resolve_claims(claims)
        self.assertEqual(res["resolution_status"], "RESOLVED")
        self.assertEqual(res["evidence_type"], "ATTESTED")
        self.assertEqual(res["confidence"], 1.00)
        self.assertEqual(len(res["claim_ids"]), 2)

    def test_conflicting_claims_uncertain(self):
        claims = [
            {"claim_id": "c1", "asserted_value": "NOUN", "evidence_type": "EXPLICIT"},
            {"claim_id": "c2", "asserted_value": "VERB", "evidence_type": "EXPLICIT"}
        ]
        res = self.engine.resolve_claims(claims)
        self.assertEqual(res["resolution_status"], "CONFLICTING")
        self.assertEqual(res["evidence_type"], "UNCERTAIN")
        self.assertEqual(res["confidence"], 0.50)
        self.assertEqual(len(res["claim_ids"]), 2)

if __name__ == "__main__":
    unittest.main()
