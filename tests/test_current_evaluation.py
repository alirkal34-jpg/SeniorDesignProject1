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

    def test_human_labeled_baseline_is_preserved(
        self,
    ) -> None:
        self.assertEqual(
            self.report["ground_truth_record_count"],
            21,
        )
        self.assertGreaterEqual(
            self.report["result_count"],
            61,
        )
        self.assertGreaterEqual(
            self.report["labeled_result_count"],
            40,
        )
        self.assertEqual(
            self.report[
                "ground_truth_coverage_ratio"
            ],
            round(
                self.report["labeled_result_count"]
                / self.report["result_count"],
                4,
            ),
        )

    def test_current_accuracy_is_reproducible(
        self,
    ) -> None:
        methods = self.report["methods"]

        expected_accuracy = round(
            self.report["correct_prediction_count"]
            / self.report["labeled_result_count"],
            4,
        )
        self.assertEqual(
            self.report["accuracy"],
            expected_accuracy,
        )
        self.assertEqual(
            methods[
                "selenium_rule_based"
            ]["accuracy"],
            1.0,
        )
        nano_metrics = methods[
            "selenium_nano_llm"
        ]
        expected_nano_accuracy = round(
            nano_metrics["correct_prediction_count"]
            / nano_metrics["labeled_result_count"],
            4,
        )
        self.assertEqual(
            nano_metrics["accuracy"],
            expected_nano_accuracy,
        )
        self.assertGreaterEqual(
            self.report["false_negative_count"],
            1,
        )
        self.assertEqual(
            self.report["false_positive_count"],
            2,
        )


if __name__ == "__main__":
    unittest.main()
