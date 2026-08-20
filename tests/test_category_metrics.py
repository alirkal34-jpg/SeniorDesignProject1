"""Unit tests for the per-category comparison of the four methods.

These numbers are what the written report claims about generalization beyond
phones, so the arithmetic, the category split, and the trivial-classifier
baseline are all pinned down here.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation import category_metrics  # noqa: E402
from evaluation.category_metrics import (  # noqa: E402
    CategoryMetricsError,
    build_category_report,
    load_category_by_product,
    relative_to_project,
    render_markdown,
    score_predictions,
)


SUBSET_HEADER = "product_id,product_name,category_group\n"
GROUND_TRUTH_HEADER = (
    "product_id,keyword,method,domain,url,human_relevant,notes\n"
)


class ScorePredictionTests(unittest.TestCase):
    """Lock the confusion-matrix arithmetic the report is built on."""

    def test_counts_every_quadrant(self) -> None:
        scores = score_predictions(
            [
                (True, True),
                (True, True),
                (True, False),
                (False, False),
                (False, True),
            ]
        )

        self.assertEqual(scores["true_positive_count"], 2)
        self.assertEqual(scores["false_positive_count"], 1)
        self.assertEqual(scores["true_negative_count"], 1)
        self.assertEqual(scores["false_negative_count"], 1)
        self.assertEqual(scores["labeled_result_count"], 5)
        self.assertEqual(scores["accuracy"], 0.6)

    def test_precision_recall_and_f1(self) -> None:
        scores = score_predictions(
            [
                (True, True),
                (True, True),
                (True, True),
                (True, False),
                (False, True),
            ]
        )

        self.assertEqual(scores["precision"], 0.75)
        self.assertEqual(scores["recall"], 0.75)
        self.assertEqual(scores["f1_score"], 0.75)
        self.assertEqual(scores["specificity"], 0.0)
        self.assertEqual(scores["balanced_accuracy"], 0.375)

    def test_always_relevant_method_matches_its_own_baseline(self) -> None:
        # A method that never says no scores the share of relevant labels and
        # nothing more. Accuracy alone would still read as 0.8, which is why
        # the baseline is reported beside it.
        predictions: list[tuple[bool, bool]] = [(True, True)] * 8
        predictions += [(True, False)] * 2

        scores = score_predictions(predictions)

        self.assertEqual(scores["accuracy"], 0.8)
        self.assertEqual(scores["always_relevant_accuracy"], 0.8)
        self.assertEqual(scores["predicted_relevant_ratio"], 1.0)
        self.assertEqual(scores["specificity"], 0.0)
        self.assertEqual(scores["recall"], 1.0)
        # Balanced accuracy is the number that exposes it: pure chance.
        self.assertEqual(scores["balanced_accuracy"], 0.5)

    def test_undefined_ratios_are_reported_as_missing(self) -> None:
        # Nothing was labeled irrelevant, so specificity has no denominator
        # and must not be silently reported as zero.
        scores = score_predictions([(True, True), (False, True)])

        self.assertIsNone(scores["specificity"])
        self.assertIsNone(scores["balanced_accuracy"])
        self.assertEqual(scores["recall"], 0.5)

    def test_empty_prediction_set_is_refused(self) -> None:
        with self.assertRaises(CategoryMetricsError):
            score_predictions([])


class LoadCategoryTests(unittest.TestCase):
    """The category split comes from the evaluation subset, not from ids."""

    def write_subset(self, content: str) -> Path:
        temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temp_directory.cleanup)
        file_path = Path(temp_directory.name) / "subset.csv"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_maps_products_to_category_groups(self) -> None:
        subset_path = self.write_subset(
            SUBSET_HEADER
            + "ELK001,iPhone 17,elektronik_cep_telefonu\n"
            + "PET001,Pro Plan,petshop\n"
        )

        self.assertEqual(
            load_category_by_product(subset_path),
            {
                "ELK001": "elektronik_cep_telefonu",
                "PET001": "petshop",
            },
        )

    def test_missing_category_column_is_reported(self) -> None:
        subset_path = self.write_subset("product_id\nELK001\n")

        with self.assertRaises(CategoryMetricsError) as error:
            load_category_by_product(subset_path)

        self.assertIn("category_group", str(error.exception))

    def test_missing_file_is_reported_by_path(self) -> None:
        with self.assertRaises(CategoryMetricsError) as error:
            load_category_by_product(Path("data") / "nope.csv")

        self.assertIn("nope.csv", str(error.exception))


class CategoryReportTests(unittest.TestCase):
    """End-to-end: manifest and result files in, per-category report out."""

    def setUp(self) -> None:
        temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temp_directory.cleanup)
        self.root = Path(temp_directory.name)

        original_root = category_metrics.PROJECT_ROOT
        category_metrics.PROJECT_ROOT = self.root
        self.addCleanup(
            setattr,
            category_metrics,
            "PROJECT_ROOT",
            original_root,
        )

    def write_result(
        self,
        product_id: str,
        method: str,
        predictions: list[tuple[str, bool]],
    ) -> str:
        payload: dict[str, Any] = {
            "product_id": product_id,
            "keyword": f"{product_id} fiyat",
            "method": method,
            "execution_mode": "live",
            "provider": "test",
            "model": "test-model",
            "prompt_version": "v1",
            "runtime_seconds": 1.0,
            "estimated_cost_usd": 0.0,
            "results": [
                {
                    "domain": "shop.example",
                    "url": url,
                    "title": "listing",
                    "snippet": "",
                    "predicted_relevant": predicted,
                    "relevance_score": 1.0 if predicted else 0.0,
                }
                for url, predicted in predictions
            ],
        }
        relative_path = f"results/{method}/{product_id}.json"
        file_path = self.root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return relative_path

    def build_fixture(self) -> Path:
        (self.root / "data").mkdir(parents=True, exist_ok=True)

        subset_path = self.root / "data" / "subset.csv"
        subset_path.write_text(
            SUBSET_HEADER
            + "ELK001,iPhone,elektronik_cep_telefonu\n"
            + "PET001,Mama,petshop\n",
            encoding="utf-8",
        )

        ground_truth_path = self.root / "data" / "labels.csv"
        ground_truth_path.write_text(
            GROUND_TRUTH_HEADER
            + "ELK001,ELK001 fiyat,,shop.example,"
            "https://shop.example/a,true,\n"
            + "ELK001,ELK001 fiyat,,shop.example,"
            "https://shop.example/b,false,\n"
            + "PET001,PET001 fiyat,,shop.example,"
            "https://shop.example/c,true,\n"
            + "PET001,PET001 fiyat,,shop.example,"
            "https://shop.example/d,false,\n",
            encoding="utf-8",
        )

        selected = [
            # Perfect on phones, wrong on both petshop URLs.
            self.write_result(
                "ELK001",
                "tavily_llm",
                [
                    ("https://shop.example/a", True),
                    ("https://shop.example/b", False),
                ],
            ),
            self.write_result(
                "PET001",
                "tavily_llm",
                [
                    ("https://shop.example/c", False),
                    ("https://shop.example/d", True),
                ],
            ),
            # Says relevant to everything, everywhere.
            self.write_result(
                "ELK001",
                "selenium_nano_llm",
                [
                    ("https://shop.example/a", True),
                    ("https://shop.example/b", True),
                ],
            ),
            self.write_result(
                "PET001",
                "selenium_nano_llm",
                [
                    ("https://shop.example/c", True),
                    ("https://shop.example/d", True),
                ],
            ),
        ]

        manifest_path = self.root / "data" / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "report_scope": "test",
                    "evaluation_subset_file": "data/subset.csv",
                    "ground_truth_file": "data/labels.csv",
                    "selected_result_files": selected,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return manifest_path

    def test_report_splits_accuracy_by_category(self) -> None:
        report = build_category_report(self.build_fixture())

        tavily = report["methods"]["tavily_llm"]["categories"]

        self.assertEqual(
            tavily["elektronik_cep_telefonu"]["accuracy"],
            1.0,
        )
        self.assertEqual(tavily["petshop"]["accuracy"], 0.0)
        # An overall 0.5 would hide both halves of that story.
        self.assertEqual(
            report["methods"]["tavily_llm"]["overall"]["accuracy"],
            0.5,
        )

    def test_report_exposes_a_method_that_never_says_no(self) -> None:
        report = build_category_report(self.build_fixture())

        nano = report["methods"]["selenium_nano_llm"]["overall"]

        self.assertEqual(nano["accuracy"], nano["always_relevant_accuracy"])
        self.assertEqual(nano["predicted_relevant_ratio"], 1.0)
        self.assertEqual(nano["balanced_accuracy"], 0.5)

    def test_categories_are_scored_across_methods_too(self) -> None:
        report = build_category_report(self.build_fixture())

        petshop = report["category_groups"]["petshop"]

        self.assertEqual(
            sorted(petshop["methods"]),
            ["selenium_nano_llm", "tavily_llm"],
        )
        self.assertEqual(petshop["overall"]["labeled_result_count"], 4)

    def test_unlabeled_results_are_counted_not_scored(self) -> None:
        manifest_path = self.build_fixture()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["selected_result_files"].append(
            self.write_result(
                "ELK001",
                "agentic_search",
                [("https://shop.example/never-labeled", True)],
            )
        )
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False),
            encoding="utf-8",
        )

        report = build_category_report(manifest_path)

        self.assertEqual(
            report["methods"]["agentic_search"]["unlabeled_result_count"],
            1,
        )
        self.assertNotIn(
            "agentic_search",
            report["category_groups"]["petshop"]["methods"],
        )

    def test_a_relative_manifest_path_is_accepted(self) -> None:
        # Running the script from a shell gives a relative path, which used
        # to crash the report before the path was resolved.
        import os

        manifest_path = self.build_fixture()
        previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)

        report = build_category_report(Path("data") / manifest_path.name)

        self.assertIn("manifest.json", report["manifest_file"])

    def test_manifest_without_result_files_is_refused(self) -> None:
        manifest_path = self.build_fixture()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["selected_result_files"] = []
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False),
            encoding="utf-8",
        )

        with self.assertRaises(CategoryMetricsError):
            build_category_report(manifest_path)


class RenderMarkdownTests(unittest.TestCase):
    """The tables are what lands in the report, so their shape is locked."""

    def sample_report(self) -> dict[str, Any]:
        strong = score_predictions([(True, True), (False, False)])
        weak = score_predictions([(True, True), (True, False)])
        return {
            "manifest_file": "data/evaluation/manifest.json",
            "evaluation_subset_file": "data/evaluation/subset.csv",
            "ground_truth_file": "data/labels/labels.csv",
            "product_count": 20,
            "category_group_count": 2,
            "method_count": 2,
            "methods": {
                "tavily_llm": {
                    "overall": strong,
                    "unlabeled_result_count": 0,
                    "categories": {"petshop": strong},
                },
                "selenium_nano_llm": {
                    "overall": weak,
                    "unlabeled_result_count": 0,
                    "categories": {"supermarket": weak},
                },
            },
            "category_groups": {
                "petshop": {
                    "overall": strong,
                    "methods": {"tavily_llm": strong},
                },
                "supermarket": {
                    "overall": weak,
                    "methods": {"selenium_nano_llm": weak},
                },
            },
        }

    def test_methods_are_ranked_by_accuracy(self) -> None:
        markdown = render_markdown(self.sample_report())

        self.assertLess(
            markdown.index("| tavily_llm |"),
            markdown.index("| selenium_nano_llm |"),
        )

    def test_missing_combination_renders_as_a_dash(self) -> None:
        markdown = render_markdown(self.sample_report())

        petshop_line = next(
            line
            for line in markdown.splitlines()
            if line.startswith("| petshop |")
        )
        self.assertIn("–", petshop_line)

    def test_unscorable_method_is_listed_last_not_hidden(self) -> None:
        report = self.sample_report()
        report["methods"]["agentic_search"] = {
            "overall": None,
            "unlabeled_result_count": 5,
            "categories": {},
        }

        markdown = render_markdown(report)

        self.assertIn("| agentic_search |", markdown)
        self.assertGreater(
            markdown.index("| agentic_search |"),
            markdown.index("| selenium_nano_llm |"),
        )

    def test_baseline_column_is_present(self) -> None:
        markdown = render_markdown(self.sample_report())

        self.assertIn("always-relevant", markdown)
        self.assertIn("balanced acc.", markdown)


if __name__ == "__main__":
    unittest.main()
