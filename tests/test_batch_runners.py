"""API-free orchestration tests for the batch runners."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.result_validator import (
    validate_result_payload,
)
from keyword_loader import KeywordRecord
from nano_llm_evaluator import FakeNanoLLMEvaluator
import run_agentic_search as agentic_runner
import run_selenium_nano_llm as nano_runner
import run_selenium_rule_based as rule_runner
import run_tavily_llm as tavily_runner
from run_evaluation_batch import (
    METHODS,
    load_evaluation_keywords,
    run_evaluation_batch,
)
from run_rule_based_batch import run_rule_based_batch
from run_selenium_nano_llm import run_selenium_nano_llm


class BatchRunnerTests(unittest.TestCase):
    """Exercise orchestration without Google or paid APIs."""

    @patch("run_rule_based_batch.save_result")
    @patch(
        "run_rule_based_batch.run_selenium_rule_based"
    )
    @patch("run_rule_based_batch.load_keywords")
    def test_rule_based_batch_processes_two_keywords(
        self,
        load_keywords_mock: Mock,
        run_mock: Mock,
        save_mock: Mock,
    ) -> None:
        records = [
            KeywordRecord(
                "P001",
                "Apple iPhone fiyat",
            ),
            KeywordRecord(
                "P002",
                "Samsung Galaxy fiyat",
            ),
        ]
        load_keywords_mock.return_value = records
        run_mock.side_effect = [
            {
                "product_id": record.product_id,
                "keyword": record.keyword,
            }
            for record in records
        ]
        save_mock.side_effect = [
            Path("P001.json"),
            Path("P002.json"),
        ]

        summary = run_rule_based_batch(
            limit=2,
            max_results=5,
        )

        self.assertEqual(
            summary["requested_count"],
            2,
        )
        self.assertEqual(
            summary["successful_count"],
            2,
        )
        self.assertEqual(
            summary["failed_count"],
            0,
        )
        self.assertEqual(run_mock.call_count, 2)

    @patch("run_rule_based_batch.save_result")
    @patch("run_rule_based_batch.run_selenium_rule_based")
    @patch("run_rule_based_batch.load_keywords")
    def test_rule_based_batch_continues_after_one_record_fails(
        self,
        load_keywords_mock: Mock,
        run_mock: Mock,
        save_mock: Mock,
    ) -> None:
        load_keywords_mock.return_value = [
            KeywordRecord("P001", "Apple iPhone fiyat"),
            KeywordRecord("P002", "Samsung Galaxy fiyat"),
        ]
        run_mock.side_effect = [
            RuntimeError("temporary failure"),
            RuntimeError("repeated failure"),
            {
                "product_id": "P002",
                "keyword": "Samsung Galaxy fiyat",
            },
        ]
        save_mock.return_value = Path("P002.json")

        summary = run_rule_based_batch(
            limit=2,
            max_results=5,
        )

        self.assertEqual(summary["requested_count"], 2)
        self.assertEqual(summary["successful_count"], 1)
        self.assertEqual(summary["failed_count"], 1)
        self.assertEqual(summary["errors"][0]["product_id"], "P001")
        self.assertEqual(run_mock.call_count, 3)

    @patch(
        "run_selenium_nano_llm."
        "make_nano_llm_evaluator"
    )
    @patch(
        "run_selenium_nano_llm."
        "collect_search_results"
    )
    @patch("run_selenium_nano_llm.create_browser")
    def test_nano_pipeline_matches_shared_schema(
        self,
        create_browser_mock: Mock,
        collect_mock: Mock,
        evaluator_factory_mock: Mock,
    ) -> None:
        browser = Mock()
        create_browser_mock.return_value = browser
        collect_mock.return_value = [
            {
                "domain": "trendyol.com",
                "url": "https://example.com/product",
                "title": "Apple iPhone fiyat",
                "snippet": "Satın alma seçeneği.",
            }
        ]
        evaluator_factory_mock.return_value = (
            FakeNanoLLMEvaluator()
        )

        payload = run_selenium_nano_llm(
            product_id="P001",
            keyword="Apple iPhone fiyat",
            max_results=1,
            provider="fake",
        )

        validated = validate_result_payload(
            payload,
            source="mocked nano pipeline",
        )

        self.assertEqual(
            validated["method"],
            "selenium_nano_llm",
        )
        self.assertEqual(
            validated["execution_mode"],
            "fake",
        )
        self.assertEqual(
            len(validated["results"]),
            1,
        )
        collect_mock.assert_called_once_with(
            browser=browser,
            keyword="Apple iPhone fiyat",
            max_results=1,
            search_engine="bing",
        )
        browser.quit.assert_called_once_with()

    def test_evaluation_batch_reuses_exact_keywords_for_all_methods(
        self,
    ) -> None:
        summary = run_evaluation_batch(
            execution_mode="fake",
            limit=2,
            max_results=5,
            save=False,
        )

        self.assertEqual(summary["failed_count"], 0)
        self.assertEqual(
            summary["successful_count"],
            2 * len(METHODS),
        )
        outputs_by_product: dict[str, list[dict]] = {}
        for output in summary["outputs"]:
            outputs_by_product.setdefault(
                output["product_id"],
                [],
            ).append(output)
            validate_result_payload(
                output["payload"],
                source="evaluation batch",
            )

        for product_outputs in outputs_by_product.values():
            self.assertEqual(
                {item["method"] for item in product_outputs},
                set(METHODS),
            )
            self.assertEqual(
                len({item["keyword"] for item in product_outputs}),
                1,
            )

    def test_live_batch_requires_explicit_opt_in_above_three_products(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "limited to three products",
        ):
            run_evaluation_batch(
                execution_mode="live",
                limit=4,
            )

    def test_repeated_saves_never_overwrite_result_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            cases = [
                (
                    rule_runner,
                    rule_runner.run_selenium_rule_based(
                        "P001",
                        "Apple iPhone fiyat",
                        search_provider="fake",
                    ),
                ),
                (
                    nano_runner,
                    nano_runner.run_selenium_nano_llm(
                        "P001",
                        "Apple iPhone fiyat",
                        provider="fake",
                        search_provider="fake",
                    ),
                ),
                (
                    tavily_runner,
                    tavily_runner.run_tavily_llm(
                        "P001",
                        "Apple iPhone fiyat",
                        search_provider="fake",
                        evaluator_provider="fake",
                    ),
                ),
                (
                    agentic_runner,
                    agentic_runner.run_agentic_search(
                        "P001",
                        "Apple iPhone fiyat",
                        planner_provider="fake",
                        search_provider="fake",
                        evaluator_provider="fake",
                    ),
                ),
            ]

            for module, payload in cases:
                with patch.object(
                    module,
                    "RESULTS_DIRECTORY",
                    root / payload["method"],
                ):
                    first_path = module.save_result(payload)
                    second_path = module.save_result(payload)

                self.assertNotEqual(first_path, second_path)
                self.assertTrue(first_path.exists())
                self.assertTrue(second_path.exists())


if __name__ == "__main__":
    unittest.main()


class EvaluationSubsetSelectionByIdTests(unittest.TestCase):
    """Locking selection by name in the batch runner.

    The labeled URLs only cover the twenty-product subset, so a run on any
    other product would produce results no human label can score. Naming
    products must therefore stay inside the subset, and must not become a
    way around the three-product live cap.
    """

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        directory = Path(self._temporary.name)

        self.subset = directory / "subset.csv"
        self.subset.write_text(
            "product_id\nELK001\nPET001\nSPM001\nKMH001\n",
            encoding="utf-8",
        )

        self.keywords = directory / "keywords.json"
        self.keywords.write_text(
            json.dumps(
                [
                    {"product_id": "ELK001", "keyword": "iPhone 17 256 GB fiyat"},
                    {"product_id": "PET001", "keyword": "Pro Plan 10 kg fiyat"},
                    {"product_id": "SPM001", "keyword": "Eti Burcak 114 gr fiyat"},
                    {"product_id": "KMH001", "keyword": "Puzzle 2000 parca fiyat"},
                ]
            ),
            encoding="utf-8",
        )

    def load(self, **kwargs):
        return load_evaluation_keywords(
            subset_file=self.subset, keywords_file=self.keywords, **kwargs
        )

    def test_named_products_come_back_in_the_requested_order(self) -> None:
        records = self.load(product_ids=["SPM001", "ELK001"])
        self.assertEqual(
            [record["product_id"] for record in records], ["SPM001", "ELK001"]
        )

    def test_names_override_the_limit(self) -> None:
        records = self.load(limit=1, product_ids=["ELK001", "PET001", "SPM001"])
        self.assertEqual(len(records), 3)

    def test_a_product_outside_the_subset_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            self.load(product_ids=["ELK001", "ELK002"])

    def test_without_names_the_limit_still_takes_the_head(self) -> None:
        records = self.load(limit=2)
        self.assertEqual(
            [record["product_id"] for record in records], ["ELK001", "PET001"]
        )

    def test_naming_four_products_does_not_bypass_the_live_cap(self) -> None:
        with self.assertRaises(ValueError):
            run_evaluation_batch(
                subset_file=self.subset,
                keywords_file=self.keywords,
                execution_mode="live",
                product_ids=["ELK001", "PET001", "SPM001", "KMH001"],
            )


class SubsetFileFormatTests(unittest.TestCase):
    """Locking that a run can be pointed at either file that names products.

    The curated evaluation subset is a CSV; the processor writes JSON. Both
    already state which products exist, so requiring one to be converted into
    the other adds a hand-written step between two pipeline stages, and a
    hand-written step is where a demonstration stops matching the pipeline.
    """

    IDS = ["ELK001", "PET001", "SPM001"]

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.directory = Path(self._temporary.name)

        self.csv_subset = self.directory / "subset.csv"
        self.csv_subset.write_text(
            "product_id\n" + "\n".join(self.IDS) + "\n", encoding="utf-8"
        )

        self.json_subset = self.directory / "products.json"
        self.json_subset.write_text(
            json.dumps(
                [
                    {"product_id": product_id, "product_name": f"Urun {product_id}"}
                    for product_id in self.IDS
                ]
            ),
            encoding="utf-8",
        )

        self.keywords = self.directory / "keywords.json"
        self.keywords.write_text(
            json.dumps(
                [
                    {"product_id": product_id, "keyword": f"{product_id} fiyat"}
                    for product_id in self.IDS
                ]
            ),
            encoding="utf-8",
        )

    def test_json_and_csv_name_the_same_products(self) -> None:
        from_csv = load_evaluation_keywords(
            subset_file=self.csv_subset, keywords_file=self.keywords
        )
        from_json = load_evaluation_keywords(
            subset_file=self.json_subset, keywords_file=self.keywords
        )
        self.assertEqual(from_csv, from_json)

    def test_json_keeps_the_file_order(self) -> None:
        records = load_evaluation_keywords(
            subset_file=self.json_subset, keywords_file=self.keywords, limit=2
        )
        self.assertEqual(
            [record["product_id"] for record in records], ["ELK001", "PET001"]
        )

    def test_a_json_file_that_is_not_a_product_list_is_refused(self) -> None:
        broken = self.directory / "broken.json"
        broken.write_text(json.dumps({"product_id": "ELK001"}), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_evaluation_keywords(
                subset_file=broken, keywords_file=self.keywords
            )
