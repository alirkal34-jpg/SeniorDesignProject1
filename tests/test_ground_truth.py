"""Unit tests for human ground-truth loading and matching."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.ground_truth import (
    GroundTruthError,
    GroundTruthRecord,
    build_ground_truth_lookup,
    find_human_label,
    load_ground_truth,
    normalize_url,
)


HEADER = (
    "product_id,keyword,method,domain,url,"
    "human_relevant,notes\n"
)


class GroundTruthTests(unittest.TestCase):
    """Test CSV validation and cross-method label reuse."""

    def write_csv(self, content: str) -> Path:
        temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temp_directory.cleanup)
        file_path = Path(temp_directory.name) / "labels.csv"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_header_only_file_returns_empty_records(self) -> None:
        file_path = self.write_csv(HEADER)

        self.assertEqual(
            load_ground_truth(file_path),
            [],
        )

    def test_shared_label_matches_every_method(self) -> None:
        record = GroundTruthRecord(
            product_id="P001",
            keyword="iPhone 16 Pro Max fiyat",
            domain="example.com",
            url="https://example.com/product/",
            human_relevant=True,
        )
        lookup = build_ground_truth_lookup([record])

        label = find_human_label(
            lookup=lookup,
            product_id="P001",
            keyword="iPhone 16 Pro Max fiyat",
            method="selenium_nano_llm",
            domain="EXAMPLE.COM",
            url="https://example.com/product",
        )

        self.assertTrue(label)

    def test_method_specific_label_overrides_shared_label(self) -> None:
        records = [
            GroundTruthRecord(
                product_id="P001",
                keyword="iPhone fiyat",
                domain="example.com",
                url="https://example.com/product",
                human_relevant=False,
            ),
            GroundTruthRecord(
                product_id="P001",
                keyword="iPhone fiyat",
                domain="example.com",
                url="https://example.com/product",
                human_relevant=True,
                method="selenium_rule_based",
            ),
        ]
        lookup = build_ground_truth_lookup(records)

        rule_label = find_human_label(
            lookup,
            "P001",
            "iPhone fiyat",
            "selenium_rule_based",
            "example.com",
            "https://example.com/product",
        )
        nano_label = find_human_label(
            lookup,
            "P001",
            "iPhone fiyat",
            "selenium_nano_llm",
            "example.com",
            "https://example.com/product",
        )

        self.assertTrue(rule_label)
        self.assertFalse(nano_label)

    def test_duplicate_label_is_rejected(self) -> None:
        record = GroundTruthRecord(
            product_id="P001",
            keyword="iPhone fiyat",
            domain="example.com",
            url="https://example.com/product",
            human_relevant=True,
        )

        with self.assertRaises(GroundTruthError):
            build_ground_truth_lookup(
                [record, record]
            )

    def test_invalid_human_label_is_rejected(self) -> None:
        file_path = self.write_csv(
            HEADER
            + (
                "P001,iPhone fiyat,,example.com,"
                "https://example.com/product,maybe,test\n"
            )
        )

        with self.assertRaises(GroundTruthError):
            load_ground_truth(file_path)

    def test_missing_column_is_rejected(self) -> None:
        file_path = self.write_csv(
            "product_id,keyword,url,human_relevant,notes\n"
        )

        with self.assertRaises(GroundTruthError):
            load_ground_truth(file_path)


if __name__ == "__main__":
    unittest.main()


class UrlNormalizationTests(unittest.TestCase):
    """One page must reduce to one key, however a search engine spelled it."""

    def test_percent_encoding_does_not_split_one_page(self) -> None:
        # Two engines returned the same filtered category page, one with the
        # colon escaped. Undecoded they count as two pages, the reviewer is
        # asked twice, and the two answers can disagree unnoticed.
        escaped = (
            "https://www.hepsiburada.com/molfix/bebek-bezi-c-60001048"
            "?filtreler=beden%3A6"
        )
        plain = (
            "https://www.hepsiburada.com/molfix/bebek-bezi-c-60001048"
            "?filtreler=beden:6"
        )

        self.assertEqual(normalize_url(escaped), normalize_url(plain))

    def test_trailing_slash_does_not_split_one_page(self) -> None:
        self.assertEqual(
            normalize_url("https://www.tefal.com.tr/ingenio-2100129672/"),
            normalize_url("https://www.tefal.com.tr/ingenio-2100129672"),
        )

    def test_host_casing_does_not_split_one_page(self) -> None:
        self.assertEqual(
            normalize_url("https://WWW.Trendyol.com/eti-p-1"),
            normalize_url("https://www.trendyol.com/eti-p-1"),
        )

    def test_a_different_query_is_a_different_page(self) -> None:
        # Marketplaces carry the variant filter in the query, so folding it
        # away would merge two genuinely different listings.
        self.assertNotEqual(
            normalize_url("https://www.hepsiburada.com/molfix?beden=6"),
            normalize_url("https://www.hepsiburada.com/molfix?beden=5"),
        )

    def test_a_non_http_url_is_refused(self) -> None:
        with self.assertRaises(GroundTruthError):
            normalize_url("ftp://example.com/a")
