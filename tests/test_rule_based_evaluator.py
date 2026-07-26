"""Unit tests for the Rule-Based relevance threshold."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rule_based_evaluator import (
    RELEVANCE_THRESHOLD,
    evaluate_result,
)


class RuleBasedEvaluatorTests(unittest.TestCase):
    """Keep the documented relevance threshold stable."""

    def test_relevance_threshold_is_fixed_at_point_six(self) -> None:
        self.assertEqual(RELEVANCE_THRESHOLD, 0.60)

        domain_rules = {
            "at-threshold.example": {
                "domain_type": "retailer",
                "relevance_score": 0.60,
            },
            "below-threshold.example": {
                "domain_type": "retailer",
                "relevance_score": 0.5999,
            },
        }

        at_threshold = evaluate_result(
            {"domain": "at-threshold.example"},
            domain_rules,
        )
        below_threshold = evaluate_result(
            {"domain": "below-threshold.example"},
            domain_rules,
        )

        self.assertTrue(at_threshold["predicted_relevant"])
        self.assertFalse(below_threshold["predicted_relevant"])


if __name__ == "__main__":
    unittest.main()
