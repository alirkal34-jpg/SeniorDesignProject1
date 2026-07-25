"""Validate the representative 10-product evaluation subset."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUBSET_FILE = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "evaluation_subset.csv"
)
PROCESSED_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "processed_products.json"
)


class EvaluationSubsetTests(unittest.TestCase):
    """Ensure the pilot subset is representative and traceable."""

    @classmethod
    def setUpClass(cls) -> None:
        with SUBSET_FILE.open(
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            cls.subset = list(
                csv.DictReader(stream)
            )

        cls.processed = {
            product["product_id"]: product
            for product in json.loads(
                PROCESSED_FILE.read_text(
                    encoding="utf-8"
                )
            )
        }

    def test_subset_has_ten_unique_products(self) -> None:
        product_ids = [
            row["product_id"]
            for row in self.subset
        ]

        self.assertEqual(
            len(product_ids),
            10,
        )
        self.assertEqual(
            len(set(product_ids)),
            10,
        )

    def test_subset_has_ten_distinct_brands(self) -> None:
        brands = {
            row["brand"]
            for row in self.subset
        }

        self.assertEqual(
            len(brands),
            10,
        )

    def test_subset_matches_processed_dataset(self) -> None:
        for subset_product in self.subset:
            product_id = subset_product["product_id"]

            self.assertIn(
                product_id,
                self.processed,
            )

            processed_product = self.processed[
                product_id
            ]

            for field_name in (
                "product_name",
                "brand",
                "model",
                "storage_gb",
                "ram_gb",
                "color",
            ):
                self.assertEqual(
                    str(subset_product[field_name]),
                    str(processed_product[field_name]),
                    msg=(
                        f"{product_id}: mismatch in "
                        f"{field_name}"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
