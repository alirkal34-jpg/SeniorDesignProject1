"""Integration checks for the committed evaluation fixtures."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.metrics import build_metrics_report


RESULTS_DIRECTORY = PROJECT_ROOT / "results"
GROUND_TRUTH_FILE = (
    PROJECT_ROOT
    / "data"
    / "labels"
    / "domain_ground_truth.csv"
)


class CurrentEvaluationTests(unittest.TestCase):
    """Keep sample results and human labels synchronized."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_metrics_report(
            input_path=RESULTS_DIRECTORY,
            ground_truth_path=GROUND_TRUTH_FILE,
        )

    def test_all_current_results_have_human_labels(
        self,
    ) -> None:
        self.assertEqual(
            self.report["ground_truth_record_count"],
            15,
        )
        self.assertEqual(
            self.report["result_count"],
            20,
        )
        self.assertEqual(
            self.report["labeled_result_count"],
            20,
        )
        self.assertEqual(
            self.report[
                "ground_truth_coverage_ratio"
            ],
            1.0,
        )

    def test_current_accuracy_is_reproducible(
        self,
    ) -> None:
        methods = self.report["methods"]

        self.assertEqual(
            self.report["accuracy"],
            0.95,
        )
        self.assertEqual(
            methods[
                "selenium_rule_based"
            ]["accuracy"],
            1.0,
        )
        self.assertEqual(
            methods[
                "selenium_nano_llm"
            ]["accuracy"],
            0.8,
        )
        self.assertEqual(
            self.report["false_negative_count"],
            1,
        )
        self.assertEqual(
            self.report["false_positive_count"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
