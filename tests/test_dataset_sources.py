"""Validate dataset source URL completeness and consistency."""

from __future__ import annotations

import csv
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from quality_check import check_dataset_quality
from data_processor import clean_data, validate_data


RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "candidate_smartphone_products_100.csv"
)
PROCESSED_CSV_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "processed_products.csv"
)
PROCESSED_JSON_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "processed_products.json"
)
SOURCE_URL_PREFIX = (
    "https://www.gsmarena.com/results.php3"
    "?sQuickSearch=yes&sName="
)


class DatasetSourceTests(unittest.TestCase):
    """Ensure every product has a traceable HTTPS reference URL."""

    @classmethod
    def setUpClass(cls) -> None:
        with RAW_FILE.open(
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            cls.raw_rows = list(csv.DictReader(stream))

        with PROCESSED_CSV_FILE.open(
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            cls.processed_csv_rows = list(
                csv.DictReader(stream)
            )

        cls.processed_json_rows = json.loads(
            PROCESSED_JSON_FILE.read_text(
                encoding="utf-8"
            )
        )

    def test_all_products_have_unique_https_source_urls(
        self,
    ) -> None:
        source_urls = [
            row["source_url"]
            for row in self.raw_rows
        ]

        self.assertEqual(len(source_urls), 100)
        self.assertEqual(len(set(source_urls)), 100)
        self.assertTrue(
            all(
                source_url.startswith(
                    SOURCE_URL_PREFIX
                )
                for source_url in source_urls
            )
        )

    def test_processed_outputs_preserve_source_urls(
        self,
    ) -> None:
        raw_sources = {
            row["product_id"]: row["source_url"]
            for row in self.raw_rows
        }
        processed_csv_sources = {
            row["product_id"]: row["source_url"]
            for row in self.processed_csv_rows
        }
        processed_json_sources = {
            row["product_id"]: row["source_url"]
            for row in self.processed_json_rows
        }

        self.assertEqual(
            processed_csv_sources,
            raw_sources,
        )
        self.assertEqual(
            processed_json_sources,
            raw_sources,
        )

    def test_quality_check_rejects_missing_source_url(
        self,
    ) -> None:
        products = pd.read_csv(PROCESSED_CSV_FILE)
        products.loc[0, "source_url"] = ""

        with redirect_stdout(io.StringIO()):
            passed = check_dataset_quality(products)

        self.assertFalse(passed)

    def test_quality_check_rejects_non_https_source_url(
        self,
    ) -> None:
        products = pd.read_csv(PROCESSED_CSV_FILE)
        products.loc[
            0,
            "source_url",
        ] = "http://example.com/product"

        with redirect_stdout(io.StringIO()):
            passed = check_dataset_quality(products)

        self.assertFalse(passed)

    def test_data_processor_reports_missing_source_url(
        self,
    ) -> None:
        products = pd.read_csv(RAW_FILE).head(1)
        products.loc[0, "source_url"] = ""

        with redirect_stdout(io.StringIO()):
            validated = validate_data(
                clean_data(products)
            )

        self.assertEqual(
            validated.loc[0, "validation_status"],
            "invalid",
        )
        self.assertIn(
            "missing_source_url",
            validated.loc[0, "validation_errors"],
        )

    def test_data_processor_reports_invalid_source_url(
        self,
    ) -> None:
        products = pd.read_csv(RAW_FILE).head(1)
        products.loc[
            0,
            "source_url",
        ] = "http://example.com/product"

        with redirect_stdout(io.StringIO()):
            validated = validate_data(
                clean_data(products)
            )

        self.assertEqual(
            validated.loc[0, "validation_status"],
            "invalid",
        )
        self.assertIn(
            "invalid_source_url",
            validated.loc[0, "validation_errors"],
        )


if __name__ == "__main__":
    unittest.main()
