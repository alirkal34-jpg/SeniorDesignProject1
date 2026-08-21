"""Unit tests for the demo input-sample builder.

The sample exists so a live demo can run on named products instead of the
first three records, which are all phones. The properties worth locking are
the ones that would let a demo show something the dataset does not say: a
silently dropped product, a reordered sample, or an invented field.
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.make_demo_sample import SampleError, build_sample  # noqa: E402


PRODUCTS = [
    {"product_id": "ELK001", "category_group": "elektronik_cep_telefonu"},
    {"product_id": "PET001", "category_group": "petshop"},
    {"product_id": "SPM001", "category_group": "supermarket"},
]
SUBSET_FIELDS = ["product_id", "product_name", "variant_label"]
SUBSET_ROWS = [
    {"product_id": "ELK001", "product_name": "iPhone", "variant_label": "256 GB"},
    {"product_id": "PET001", "product_name": "Pro Plan", "variant_label": "10 kg"},
    {"product_id": "SPM001", "product_name": "Eti Burcak", "variant_label": "114 gr"},
]


class BuildSampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.directory = Path(self._temporary.name)

        self.products_path = self.directory / "products.json"
        self.products_path.write_text(
            json.dumps(PRODUCTS, ensure_ascii=False), encoding="utf-8"
        )

        self.subset_path = self.directory / "subset.csv"
        with self.subset_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=SUBSET_FIELDS)
            writer.writeheader()
            writer.writerows(SUBSET_ROWS)

        self.output = self.directory / "out"

    def build(self, ids: list[str]) -> tuple[Path, Path]:
        return build_sample(
            ids=ids,
            products_path=self.products_path,
            subset_path=self.subset_path,
            output_directory=self.output,
        )

    def test_sample_keeps_the_requested_order(self) -> None:
        products_out, subset_out = self.build(["SPM001", "ELK001"])

        written = json.loads(products_out.read_text(encoding="utf-8"))
        self.assertEqual(
            [record["product_id"] for record in written], ["SPM001", "ELK001"]
        )

        with subset_out.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([row["product_id"] for row in rows], ["SPM001", "ELK001"])

    def test_records_are_copied_unchanged(self) -> None:
        products_out, _ = self.build(["PET001"])
        written = json.loads(products_out.read_text(encoding="utf-8"))
        self.assertEqual(written, [PRODUCTS[1]])

    def test_subset_keeps_its_original_columns(self) -> None:
        _, subset_out = self.build(["ELK001"])
        with subset_out.open(encoding="utf-8-sig", newline="") as stream:
            self.assertEqual(csv.DictReader(stream).fieldnames, SUBSET_FIELDS)

    def test_an_unknown_id_is_refused(self) -> None:
        with self.assertRaises(SampleError):
            self.build(["ELK001", "NOPE"])

    def test_an_id_missing_from_the_subset_is_refused(self) -> None:
        # A product can exist in the dataset without being one of the twenty
        # labeled products; running the batch on it would produce results no
        # label covers.
        products = PRODUCTS + [{"product_id": "KMH001", "category_group": "kitap"}]
        self.products_path.write_text(
            json.dumps(products, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaises(SampleError):
            self.build(["KMH001"])

    def test_an_empty_id_list_is_refused(self) -> None:
        with self.assertRaises(SampleError):
            self.build([])


if __name__ == "__main__":
    unittest.main()
