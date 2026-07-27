"""API-free orchestration tests for the batch runners."""

from __future__ import annotations

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
from run_evaluation_batch import METHODS, run_evaluation_batch
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
