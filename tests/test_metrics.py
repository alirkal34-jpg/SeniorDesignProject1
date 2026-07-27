"""Unit tests for experiment metric calculations."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.ground_truth import (
    GroundTruthRecord,
    build_ground_truth_lookup,
)
from evaluation.metrics import (
    build_metrics_report,
    calculate_method_metrics,
)


def make_result(
    url: str,
    predicted_relevant: bool,
    score: float,
) -> dict:
    return {
        "domain": "example.com",
        "url": url,
        "title": "Example product",
        "snippet": "Example product price.",
        "predicted_relevant": predicted_relevant,
        "relevance_score": score,
    }


def make_payload(
    method: str,
    runtime: float,
    cost: float,
    results: list[dict],
) -> dict:
    return {
        "product_id": "P001",
        "keyword": "Example product fiyat",
        "method": method,
        "execution_mode": (
            "live"
            if method == "selenium_rule_based"
            else "fake"
        ),
        "provider": (
            "selenium+rule_based"
            if method == "selenium_rule_based"
            else "fake+fake"
        ),
        "model": (
            "rule-based-v1"
            if method == "selenium_rule_based"
            else "fake"
        ),
        "prompt_version": (
            "not_applicable"
            if method == "selenium_rule_based"
            else "relevance-v1"
        ),
        "runtime_seconds": runtime,
        "estimated_cost_usd": cost,
        "results": results,
    }


class MetricsTests(unittest.TestCase):
    """Test aggregation, relevance ratio and accuracy."""

    def test_metrics_are_grouped_by_method(self) -> None:
        payloads = [
            make_payload(
                "selenium_rule_based",
                10.0,
                0.0,
                [
                    make_result(
                        "https://example.com/a",
                        True,
                        0.9,
                    ),
                    make_result(
                        "https://example.com/b",
                        False,
                        0.2,
                    ),
                ],
            ),
            make_payload(
                "selenium_rule_based",
                20.0,
                0.0,
                [
                    make_result(
                        "https://example.com/c",
                        True,
                        0.8,
                    )
                ],
            ),
            make_payload(
                "selenium_nano_llm",
                5.0,
                0.02,
                [
                    make_result(
                        "https://example.com/d",
                        False,
                        0.3,
                    )
                ],
            ),
        ]

        metrics = calculate_method_metrics(payloads)
        rule_metrics = metrics["selenium_rule_based"]
        nano_metrics = metrics["selenium_nano_llm"]

        self.assertEqual(
            rule_metrics["experiment_count"],
            2,
        )
        self.assertEqual(
            rule_metrics["result_count"],
            3,
        )
        self.assertEqual(
            rule_metrics["relevant_result_count"],
            2,
        )
        self.assertEqual(
            rule_metrics["relevant_result_ratio"],
            0.6667,
        )
        self.assertEqual(
            rule_metrics["average_runtime_seconds"],
            15.0,
        )
        self.assertEqual(
            nano_metrics["total_estimated_cost_usd"],
            0.02,
        )
        self.assertEqual(
            rule_metrics["ground_truth_coverage_ratio"],
            0.0,
        )

    def test_accuracy_uses_available_human_labels(self) -> None:
        payload = make_payload(
            "selenium_rule_based",
            10.0,
            0.0,
            [
                make_result(
                    "https://example.com/correct",
                    True,
                    0.9,
                ),
                make_result(
                    "https://example.com/wrong",
                    True,
                    0.8,
                ),
            ],
        )
        records = [
            GroundTruthRecord(
                product_id="P001",
                keyword="Example product fiyat",
                domain="example.com",
                url="https://example.com/correct",
                human_relevant=True,
            ),
            GroundTruthRecord(
                product_id="P001",
                keyword="Example product fiyat",
                domain="example.com",
                url="https://example.com/wrong",
                human_relevant=False,
            ),
        ]

        metrics = calculate_method_metrics(
            [payload],
            build_ground_truth_lookup(records),
        )["selenium_rule_based"]

        self.assertEqual(
            metrics["labeled_result_count"],
            2,
        )
        self.assertEqual(
            metrics["correct_prediction_count"],
            1,
        )
        self.assertEqual(
            metrics["accuracy"],
            0.5,
        )
        self.assertEqual(
            metrics["ground_truth_coverage_ratio"],
            1.0,
        )
        self.assertEqual(
            metrics["true_positive_count"],
            1,
        )
        self.assertEqual(
            metrics["false_positive_count"],
            1,
        )

    def test_partial_ground_truth_coverage_is_reported(self) -> None:
        payload = make_payload(
            "selenium_rule_based",
            10.0,
            0.0,
            [
                make_result(
                    "https://example.com/labeled",
                    True,
                    0.9,
                ),
                make_result(
                    "https://example.com/unlabeled",
                    False,
                    0.2,
                ),
            ],
        )

        records = [
            GroundTruthRecord(
                product_id="P001",
                keyword="Example product fiyat",
                domain="example.com",
                url="https://example.com/labeled",
                human_relevant=True,
            )
        ]

        metrics = calculate_method_metrics(
            [payload],
            build_ground_truth_lookup(records),
        )["selenium_rule_based"]

        self.assertEqual(metrics["result_count"], 2)
        self.assertEqual(metrics["labeled_result_count"], 1)
        self.assertEqual(
            metrics["ground_truth_coverage_ratio"],
            0.5,
        )
        self.assertEqual(metrics["accuracy"], 1.0)

    def test_accuracy_is_none_without_labels(self) -> None:
        payload = make_payload(
            "selenium_rule_based",
            1.0,
            0.0,
            [
                make_result(
                    "https://example.com/product",
                    True,
                    0.9,
                )
            ],
        )

        metrics = calculate_method_metrics(
            [payload]
        )["selenium_rule_based"]

        self.assertEqual(
            metrics["labeled_result_count"],
            0,
        )
        self.assertIsNone(
            metrics["accuracy"]
        )
        self.assertEqual(
            metrics["ground_truth_coverage_ratio"],
            0.0,
        )

    def test_report_loads_result_and_ground_truth_files(self) -> None:
        payload = make_payload(
            "selenium_rule_based",
            2.0,
            0.0,
            [
                make_result(
                    "https://example.com/product",
                    True,
                    0.9,
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            results_directory = root / "results"
            results_directory.mkdir()
            result_file = results_directory / "result.json"
            result_file.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            ground_truth_file = root / "labels.csv"
            ground_truth_file.write_text(
                (
                    "product_id,keyword,method,domain,url,"
                    "human_relevant,notes\n"
                    "P001,Example product fiyat,,example.com,"
                    "https://example.com/product,true,test\n"
                ),
                encoding="utf-8",
            )

            report = build_metrics_report(
                input_path=results_directory,
                ground_truth_path=ground_truth_file,
            )

        self.assertEqual(
            report["experiment_count"],
            1,
        )
        self.assertEqual(
            report["accuracy"],
            1.0,
        )
        self.assertEqual(
            report["ground_truth_coverage_ratio"],
            1.0,
        )
        self.assertEqual(
            report["true_positive_count"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
