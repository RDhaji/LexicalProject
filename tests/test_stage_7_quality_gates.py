"""
Unit Tests for Stage 7 Quality Gates
Compliance: INGESTION_PIPELINE.md Section 2
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.stage_7_quality_gates import run_stage_7

class TestStage7QualityGates(unittest.TestCase):
    def test_run_all_quality_gates(self):
        """Execute Gates B through E against the staging graph."""
        self.assertTrue(run_stage_7(), "Stage 7 Quality Gates failed verification.")

if __name__ == "__main__":
    unittest.main()
