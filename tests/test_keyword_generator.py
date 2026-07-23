import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keyword_generator import FakeKeywordClient, load_products, select_products, validate_keyword_output
from relevance_evaluator import SearchResult, make_result_payload


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


if __name__ == "__main__":
    unittest.main()
