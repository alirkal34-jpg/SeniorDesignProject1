"""API-free orchestration tests for the batch runners."""

from __future__ import annotations

import sys
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
            len(validated["results"]),
            1,
        )
        browser.quit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
