"""Unit tests for the written multi-category comparison report.

The report is what the thesis quotes, so the tests check that its claims are
derived from the metrics files rather than asserted: the ranking, the
trivial-classifier comparison, and the refusal to report on partial labels.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.multicategory_report import (  # noqa: E402
    ReportError,
    percent,
    rank_methods,
    render_report,
)


def method_scores(
    accuracy: float,
    always_relevant: float,
    specificity: float | None = 0.0,
    predicted_relevant_ratio: float = 1.0,
    true_negative: int = 0,
    false_positive: int = 0,
) -> dict[str, Any]:
    return {
        "labeled_result_count": 100,
        "correct_prediction_count": int(accuracy * 100),
        "accuracy": accuracy,
        "true_positive_count": 70,
        "true_negative_count": true_negative,
        "false_positive_count": false_positive,
        "false_negative_count": 0,
        "precision": 0.8,
        "recall": 1.0,
        "specificity": specificity,
        "f1_score": 0.88,
        "balanced_accuracy": 0.5,
        "predicted_relevant_ratio": predicted_relevant_ratio,
        "always_relevant_accuracy": always_relevant,
    }


def sample_metrics(coverage: float = 1.0) -> dict[str, Any]:
    return {
        "product_count": 20,
        "experiment_count": 80,
        "result_count": 399,
        "ground_truth_record_count": 194,
        "labeled_result_count": 399,
        "ground_truth_coverage_ratio": coverage,
        "correct_prediction_count": 304,
        "accuracy": 0.7619,
        "methods": {
            "tavily_llm": {"average_runtime_seconds": 12.08},
            "selenium_nano_llm": {"average_runtime_seconds": 14.2},
        },
    }


def sample_category_metrics() -> dict[str, Any]:
    discriminating = method_scores(
        accuracy=0.82,
        always_relevant=0.72,
        specificity=0.3929,
        predicted_relevant_ratio=0.88,
        true_negative=11,
        false_positive=17,
    )
    degenerate = method_scores(
        accuracy=0.74,
        always_relevant=0.74,
        specificity=0.0,
        predicted_relevant_ratio=1.0,
        true_negative=0,
        false_positive=26,
    )
    return {
        "category_group_count": 2,
        "methods": {
            "tavily_llm": {
                "overall": discriminating,
                "unlabeled_result_count": 0,
                "categories": {},
            },
            "selenium_nano_llm": {
                "overall": degenerate,
                "unlabeled_result_count": 0,
                "categories": {},
            },
        },
        "category_groups": {
            "elektronik_cep_telefonu": {
                "overall": method_scores(1.0, 0.95),
                "methods": {
                    "tavily_llm": method_scores(1.0, 0.95),
                    "selenium_nano_llm": method_scores(1.0, 0.95),
                },
            },
            "petshop": {
                "overall": method_scores(0.7, 0.65),
                "methods": {
                    "tavily_llm": method_scores(0.8, 0.65),
                    "selenium_nano_llm": method_scores(0.6, 0.65),
                },
            },
        },
    }


class PercentTests(unittest.TestCase):
    """Undefined metrics must not be printed as zero."""

    def test_ratio_becomes_a_percentage(self) -> None:
        self.assertEqual(percent(0.8205), "82.05%")

    def test_missing_value_becomes_a_dash(self) -> None:
        self.assertEqual(percent(None), "–")


class RankTests(unittest.TestCase):
    """Ranking drives every ordered list in the report."""

    def test_methods_are_ranked_by_accuracy(self) -> None:
        self.assertEqual(
            rank_methods(sample_category_metrics()),
            ["tavily_llm", "selenium_nano_llm"],
        )

    def test_unscorable_methods_are_skipped(self) -> None:
        category_metrics = sample_category_metrics()
        category_metrics["methods"]["agentic_search"] = {
            "overall": None,
            "unlabeled_result_count": 4,
            "categories": {},
        }

        self.assertNotIn(
            "agentic_search",
            rank_methods(category_metrics),
        )

    def test_report_without_any_scorable_method_is_refused(self) -> None:
        category_metrics = sample_category_metrics()
        for payload in category_metrics["methods"].values():
            payload["overall"] = None

        with self.assertRaises(ReportError):
            rank_methods(category_metrics)


class RenderReportTests(unittest.TestCase):
    """The narrative has to match the numbers it is rendered from."""

    def test_partial_label_coverage_is_refused(self) -> None:
        # Scoring methods on different subsets of URLs would make the
        # comparison meaningless, so the report refuses to be written.
        with self.assertRaises(ReportError) as error:
            render_report(
                sample_metrics(coverage=0.68),
                sample_category_metrics(),
            )

        self.assertIn("coverage", str(error.exception))

    def test_best_method_is_listed_first(self) -> None:
        report = render_report(sample_metrics(), sample_category_metrics())

        self.assertLess(
            report.index("| Tavily + NanoLLM |"),
            report.index("| Selenium + NanoLLM |"),
        )

    def test_a_method_matching_its_baseline_is_named_as_not_beating_it(
        self,
    ) -> None:
        report = render_report(sample_metrics(), sample_category_metrics())

        # Tavily is the only method above its own baseline here.
        self.assertIn("Only **Tavily + NanoLLM** beat that baseline", report)
        self.assertIn("rejected 0.00% of the irrelevant ones", report)

    def test_margin_is_shown_when_several_methods_beat_the_baseline(
        self,
    ) -> None:
        category_metrics = sample_category_metrics()
        category_metrics["methods"]["selenium_nano_llm"]["overall"][
            "always_relevant_accuracy"
        ] = 0.73

        report = render_report(sample_metrics(), category_metrics)

        # A one-point margin must not read the same as a ten-point one.
        self.assertIn("+10.0 pp", report)
        self.assertIn("+1.0 pp", report)

    def test_phone_category_comparison_uses_measured_averages(self) -> None:
        report = render_report(sample_metrics(), sample_category_metrics())

        self.assertIn("Was the phone category representative?", report)
        self.assertIn("the phone category scored 100.00%", report)
        self.assertIn("other categories averaged 70.00%", report)

    def test_frozen_phone_experiment_is_marked_as_not_comparable(
        self,
    ) -> None:
        report = render_report(
            sample_metrics(),
            sample_category_metrics(),
            {
                "product_count": 10,
                "labeled_result_count": 199,
                "accuracy": 0.6884,
            },
        )

        self.assertIn("68.84%", report)
        self.assertIn("not directly comparable", report)

    def test_adjudication_file_is_disclosed(self) -> None:
        report = render_report(sample_metrics(), sample_category_metrics())

        self.assertIn("multicategory_label_adjudications.csv", report)
        self.assertIn("cannot overturn an answer", report)


if __name__ == "__main__":
    unittest.main()
