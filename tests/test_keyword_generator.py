import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keyword_generator import FakeKeywordClient, load_products, select_products, validate_keyword_output
from keyword_loader import load_keywords
from nano_llm_evaluator import FakeNanoLLMEvaluator, validate_evaluation_output
from relevance_evaluator import SearchResult, make_result_payload
from agentic_search import AgenticSearch
from run_agentic_search import run_agentic_search
from run_tavily_llm import run_tavily_llm


class KeywordGeneratorTests(unittest.TestCase):
    def test_fake_keyword_client_keeps_product_ids(self):
        products = select_products(load_products(ROOT / "data" / "processed" / "processed_products.json"), limit=3)

        keywords = FakeKeywordClient().generate_keywords(products)

        self.assertEqual([item.product_id for item in keywords], ["P001", "P002", "P003"])
        self.assertTrue(all("fiyat" in item.keyword.lower() for item in keywords))

    def test_keyword_schema_validation_accepts_expected_shape(self):
        raw = [{"product_id": "P001", "keyword": "Apple iPhone 16 Pro Max 256 GB fiyat"}]

        result = validate_keyword_output(raw, {"P001"})

        self.assertEqual(result[0].to_dict(), raw[0])

    def test_relevance_payload_matches_common_result_shape(self):
        payload = make_result_payload(
            product_id="P001",
            keyword="Apple iPhone 16 Pro Max 256 GB fiyat",
            results=[
                SearchResult(
                    domain="trendyol.com",
                    url="https://www.trendyol.com/apple-iphone-16-pro-max",
                    title="Apple iPhone 16 Pro Max 256 GB",
                    snippet="Telefon fiyatları ve satın alma seçenekleri.",
                )
            ],
        )

        self.assertEqual(payload["method"], "selenium_nano_llm")
        self.assertTrue(payload["results"][0]["predicted_relevant"])
        self.assertGreaterEqual(payload["results"][0]["relevance_score"], 0)
        self.assertLessEqual(payload["results"][0]["relevance_score"], 1)
        json.dumps(payload)

    def test_keyword_loader_reads_generated_keywords(self):
        records = load_keywords(ROOT / "data" / "processed" / "generated_keywords.json", limit=2)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].product_id, "P001")
        self.assertIn("fiyat", records[0].keyword.lower())

    def test_nano_llm_evaluator_validates_three_rows(self):
        raw = [
            {"predicted_relevant": True, "relevance_score": 0.9},
            {"predicted_relevant": False, "relevance_score": 0.2},
            {"predicted_relevant": True, "relevance_score": 0.75},
        ]

        evaluations = validate_evaluation_output(raw, expected_count=3)

        self.assertEqual(len(evaluations), 3)
        self.assertTrue(evaluations[0].predicted_relevant)

    def test_fake_nano_llm_evaluator_adds_required_fields(self):
        evaluator = FakeNanoLLMEvaluator()

        results = evaluator.evaluate_results(
            keyword="Apple iPhone 16 Pro Max 256 GB fiyat",
            results=[
                {
                    "domain": "trendyol.com",
                    "url": "https://www.trendyol.com/",
                    "title": "iPhone 16 Pro Max fiyat",
                    "snippet": "Satın alma seçenekleri.",
                }
            ],
        )

        self.assertIn("predicted_relevant", results[0])
        self.assertIn("relevance_score", results[0])
        self.assertTrue(results[0]["predicted_relevant"])

    def test_fake_tavily_runner_uses_common_result_shape(self):
        payload = run_tavily_llm(
            product_id="P001",
            keyword="Apple iPhone 16 Pro Max 256 GB fiyat",
            search_provider="fake",
            evaluator_provider="fake",
        )

        self.assertEqual(payload["method"], "tavily_llm")
        self.assertLessEqual(len(payload["results"]), 5)
        self.assertIn("predicted_relevant", payload["results"][0])

    def test_agentic_search_deduplicates_and_limits_results(self):
        results = AgenticSearch(provider="fake").search("Apple iPhone 16 Pro Max fiyat")

        self.assertLessEqual(len(results), 5)
        self.assertEqual(len({result["url"] for result in results}), len(results))

    def test_fake_agentic_runner_keeps_method_and_product_id(self):
        payload = run_agentic_search(
            product_id="P001",
            keyword="Apple iPhone 16 Pro Max 256 GB fiyat",
            search_provider="fake",
            evaluator_provider="fake",
        )

        self.assertEqual(payload["product_id"], "P001")
        self.assertEqual(payload["method"], "agentic_search")
        self.assertLessEqual(len(payload["results"]), 5)


if __name__ == "__main__":
    unittest.main()
