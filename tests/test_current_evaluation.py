"""Integration checks for the committed evaluation fixtures."""

from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.final_report import render_report
from evaluation.final_metrics import build_final_metrics_report
from evaluation.metrics import build_metrics_report


RESULTS_DIRECTORY = PROJECT_ROOT / "results"
GROUND_TRUTH_FILE = (
    PROJECT_ROOT
    / "data"
    / "labels"
    / "domain_ground_truth.csv"
)
FINAL_REPORT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "final_evaluation_metrics.json"
)
FINAL_MARKDOWN_REPORT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "final_evaluation_report.md"
)
FINAL_HUMAN_LABELS_FILE = (
    PROJECT_ROOT
    / "data"
    / "labels"
    / "final_evaluation_human_labels.csv"
)


class CurrentEvaluationTests(unittest.TestCase):
    """Keep sample results and human labels synchronized."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_metrics_report(
            input_path=RESULTS_DIRECTORY,
            ground_truth_path=GROUND_TRUTH_FILE,
        )
        cls.final_report = json.loads(
            FINAL_REPORT_FILE.read_text(
                encoding="utf-8"
            )
        )
        cls.rebuilt_final_report = build_final_metrics_report()

    def test_approved_ground_truth_baseline_is_preserved(
        self,
    ) -> None:
        self.assertEqual(
            self.report["ground_truth_record_count"],
            107,
        )
        self.assertEqual(
            self.report["result_count"],
            260,
        )
        self.assertEqual(
            self.report["labeled_result_count"],
            239,
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
        rule_metrics = methods[
            "selenium_rule_based"
        ]
        expected_rule_accuracy = round(
            rule_metrics["correct_prediction_count"]
            / rule_metrics["labeled_result_count"],
            4,
        )
        self.assertEqual(
            rule_metrics["accuracy"],
            expected_rule_accuracy,
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
        self.assertEqual(self.report["accuracy"], 0.728)

    def test_final_live_evaluation_has_full_coverage(
        self,
    ) -> None:
        self.assertEqual(
            self.final_report["product_count"],
            10,
        )
        self.assertEqual(
            self.final_report["method_count"],
            4,
        )
        self.assertEqual(
            self.final_report["experiment_count"],
            40,
        )
        self.assertEqual(
            self.final_report["result_count"],
            199,
        )
        self.assertEqual(
            self.final_report[
                "labeled_result_count"
            ],
            199,
        )
        self.assertEqual(
            self.final_report[
                "ground_truth_coverage_ratio"
            ],
            1.0,
        )
        self.assertEqual(
            len(
                self.final_report[
                    "selected_result_files"
                ]
            ),
            40,
        )
        for relative_path in self.final_report[
            "selected_result_files"
        ]:
            self.assertTrue(
                (PROJECT_ROOT / relative_path).is_file(),
                relative_path,
            )
        for method_metrics in self.final_report[
            "methods"
        ].values():
            self.assertEqual(
                method_metrics["experiment_count"],
                10,
            )
            self.assertEqual(
                method_metrics["result_count"],
                method_metrics[
                    "labeled_result_count"
                ],
            )

    def test_final_metrics_are_reproducible_from_manifest(
        self,
    ) -> None:
        self.assertEqual(
            self.rebuilt_final_report,
            self.final_report,
        )

    def test_final_human_review_is_complete_and_auditable(
        self,
    ) -> None:
        with FINAL_HUMAN_LABELS_FILE.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 86)
        self.assertEqual(
            sum(row["human_relevant"] == "true" for row in rows),
            57,
        )
        self.assertEqual(
            sum(row["human_relevant"] == "false" for row in rows),
            29,
        )
        self.assertEqual(
            sum(row["adjudication_required"] == "true" for row in rows),
            35,
        )
        self.assertTrue(
            all("Individually reviewed" in row["review_status"] for row in rows)
        )

    def test_final_markdown_report_matches_metrics(
        self,
    ) -> None:
        report_text = render_report(self.final_report)
        self.assertEqual(
            FINAL_MARKDOWN_REPORT_FILE.read_text(
                encoding="utf-8"
            ),
            report_text,
        )
        self.assertIn("Tavily + NanoLLM", report_text)
        self.assertIn("74.00%", report_text)
        self.assertIn("68.84%", report_text)
        self.assertNotIn("AI-assisted", report_text)


if __name__ == "__main__":
    unittest.main()
