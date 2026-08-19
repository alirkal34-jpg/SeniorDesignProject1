"""Characterization tests that lock the current data-pipeline behavior.

These tests are a safety net for the multi-category revision. They do not
describe how the pipeline *should* behave in the future; they record exactly
how it behaves today, including the smartphone-only assumptions. Any test that
starts failing during the category expansion marks a deliberate decision that
has to be reviewed and re-approved, not an accident.

Locked here:
- the DataProcessor schema constants and their order,
- the exact text/numeric cleaning transformations,
- the exact validation error vocabulary and the order it is emitted in,
- the dataset-level quality gate, including its hard-coded 100 product and
  P001-P100 identifier assumptions,
- the frozen 10-product evaluation subset.
"""

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

import data_processor
from data_processor import clean_data, validate_data
from quality_check import check_dataset_quality


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
SUBSET_FILE = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "evaluation_subset.csv"
)


def build_row(**overrides: object) -> pd.DataFrame:
    """Build one raw-shaped product row so tests can vary a single field."""

    row = {
        "product_id": "P001",
        "product_name": "Test Phone",
        "brand": "Apple",
        "model": "iPhone 16 Pro Max",
        "category": "Smartphone",
        "storage_gb": "256",
        "ram_gb": "8",
        "display_size_inch": "6.9",
        "battery_mah": "4685",
        "color": "Black Titanium",
        "operating_system": "iOS",
        "source_url": "https://example.com/product",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def process(frame: pd.DataFrame) -> pd.DataFrame:
    """Run clean_data + validate_data without the module's console output."""

    with redirect_stdout(io.StringIO()):
        return validate_data(clean_data(frame))


class SchemaConstantTests(unittest.TestCase):
    """Freeze the column contract the whole pipeline is built on."""

    def test_schema_columns_and_their_order_are_fixed(self) -> None:
        self.assertEqual(
            data_processor.SCHEMA_COLUMNS,
            [
                "product_id",
                "product_name",
                "brand",
                "model",
                "category",
                "storage_gb",
                "ram_gb",
                "display_size_inch",
                "battery_mah",
                "color",
                "operating_system",
                "source_url",
            ],
        )

    def test_every_schema_column_is_currently_mandatory(self) -> None:
        # The smartphone-only dataset has no optional column today. The
        # multi-category revision is expected to change exactly this line.
        self.assertEqual(
            data_processor.NON_NULL_COLUMNS,
            data_processor.SCHEMA_COLUMNS,
        )
        self.assertEqual(data_processor.NULLABLE_COLUMNS, [])

    def test_text_and_numeric_columns_partition_the_schema(self) -> None:
        self.assertEqual(
            data_processor.TEXT_COLUMNS,
            [
                "product_id",
                "product_name",
                "brand",
                "model",
                "category",
                "color",
                "operating_system",
                "source_url",
            ],
        )
        self.assertEqual(
            data_processor.NUMERIC_COLUMNS,
            [
                "storage_gb",
                "ram_gb",
                "display_size_inch",
                "battery_mah",
            ],
        )
        self.assertEqual(
            sorted(
                data_processor.TEXT_COLUMNS
                + data_processor.NUMERIC_COLUMNS
            ),
            sorted(data_processor.SCHEMA_COLUMNS),
        )

    def test_numeric_sanity_ranges_are_smartphone_specific(self) -> None:
        self.assertEqual(
            data_processor.VALID_RANGES,
            {
                "storage_gb": (16, 2048),
                "ram_gb": (1, 64),
                "display_size_inch": (3, 10),
                "battery_mah": (1000, 15000),
            },
        )


class CleaningBehaviorTests(unittest.TestCase):
    """Freeze the exact standardization applied to every product row."""

    def test_clean_data_selects_and_reorders_to_the_schema(self) -> None:
        frame = build_row()
        frame["unexpected_column"] = "dropped"
        frame = frame[["unexpected_column"] + data_processor.SCHEMA_COLUMNS[::-1]]

        with redirect_stdout(io.StringIO()):
            cleaned = clean_data(frame)

        self.assertEqual(
            list(cleaned.columns),
            data_processor.SCHEMA_COLUMNS,
        )

    def test_text_columns_are_stripped_but_case_is_preserved(self) -> None:
        with redirect_stdout(io.StringIO()):
            cleaned = clean_data(
                build_row(
                    product_id="  P001  ",
                    brand="  Apple  ",
                    color="  Black Titanium  ",
                )
            )

        self.assertEqual(cleaned.loc[0, "product_id"], "P001")
        self.assertEqual(cleaned.loc[0, "brand"], "Apple")
        self.assertEqual(cleaned.loc[0, "color"], "Black Titanium")

    def test_category_is_lowercased_then_mapped_to_smartphone(self) -> None:
        for raw_category in ("Smartphone", "SMART PHONE", "Mobile Phone"):
            with self.subTest(raw_category=raw_category):
                with redirect_stdout(io.StringIO()):
                    cleaned = clean_data(build_row(category=raw_category))

                self.assertEqual(cleaned.loc[0, "category"], "Smartphone")

    def test_unmapped_category_stays_lowercased(self) -> None:
        # Any category outside the smartphone mapping keeps its lowercase form.
        # The revision has to decide what replaces this behavior.
        with redirect_stdout(io.StringIO()):
            cleaned = clean_data(build_row(category="Kitap"))

        self.assertEqual(cleaned.loc[0, "category"], "kitap")

    def test_operating_system_is_lowercased_then_mapped(self) -> None:
        for raw_os, expected in (
            ("iOS", "iOS"),
            ("IOS", "iOS"),
            ("Android", "Android"),
            ("ANDROID", "Android"),
        ):
            with self.subTest(raw_os=raw_os):
                with redirect_stdout(io.StringIO()):
                    cleaned = clean_data(build_row(operating_system=raw_os))

                self.assertEqual(
                    cleaned.loc[0, "operating_system"],
                    expected,
                )

    def test_numeric_columns_are_coerced_and_bad_values_become_missing(
        self,
    ) -> None:
        with redirect_stdout(io.StringIO()):
            cleaned = clean_data(
                build_row(storage_gb="256", ram_gb="not-a-number")
            )

        self.assertEqual(cleaned.loc[0, "storage_gb"], 256)
        self.assertTrue(pd.isna(cleaned.loc[0, "ram_gb"]))


class ValidationVocabularyTests(unittest.TestCase):
    """Freeze the error codes and the order validate_data emits them in."""

    def test_a_fully_valid_row_has_no_errors(self) -> None:
        validated = process(build_row())

        self.assertEqual(validated.loc[0, "validation_errors"], "")
        self.assertEqual(validated.loc[0, "validation_status"], "valid")

    def test_missing_value_produces_missing_prefixed_error(self) -> None:
        for column in data_processor.SCHEMA_COLUMNS:
            with self.subTest(column=column):
                validated = process(build_row(**{column: ""}))

                self.assertIn(
                    f"missing_{column}",
                    validated.loc[0, "validation_errors"],
                )
                self.assertEqual(
                    validated.loc[0, "validation_status"],
                    "invalid",
                )

    def test_non_https_source_url_is_rejected(self) -> None:
        validated = process(
            build_row(source_url="http://insecure.example.com/a")
        )

        self.assertEqual(
            validated.loc[0, "validation_errors"],
            "invalid_source_url",
        )

    def test_out_of_range_numeric_values_are_reported_per_column(self) -> None:
        for column, bad_value in (
            ("storage_gb", "999999"),
            ("ram_gb", "999"),
            ("display_size_inch", "99"),
            ("battery_mah", "1"),
        ):
            with self.subTest(column=column):
                validated = process(build_row(**{column: bad_value}))

                self.assertEqual(
                    validated.loc[0, "validation_errors"],
                    f"invalid_{column}",
                )

    def test_duplicate_id_and_name_are_both_reported(self) -> None:
        frame = pd.concat(
            [
                build_row(product_name="Same Name", source_url="https://a.example.com"),
                build_row(product_name="same name", source_url="https://b.example.com"),
            ],
            ignore_index=True,
        )

        validated = process(frame)

        for index in (0, 1):
            self.assertEqual(
                validated.loc[index, "validation_errors"],
                "duplicate_product_id;duplicate_product_name",
            )

    def test_error_codes_keep_a_stable_emission_order(self) -> None:
        # Non-null checks run first in NON_NULL_COLUMNS order, then the source
        # URL check, then duplicates, then numeric ranges.
        validated = process(
            build_row(
                brand="",
                ram_gb="",
                storage_gb="999999",
                source_url="http://insecure.example.com",
            )
        )

        self.assertEqual(
            validated.loc[0, "validation_errors"],
            "missing_brand;missing_ram_gb;invalid_source_url;invalid_storage_gb",
        )

    def test_error_list_is_semicolon_separated_without_trailing_separator(
        self,
    ) -> None:
        validated = process(build_row(brand="", model=""))

        errors = validated.loc[0, "validation_errors"]
        self.assertEqual(errors, "missing_brand;missing_model")
        self.assertFalse(errors.endswith(";"))


class CommittedDatasetTests(unittest.TestCase):
    """Freeze the shape of the datasets that are committed today."""

    def test_raw_dataset_is_exactly_100_smartphone_products(self) -> None:
        with RAW_FILE.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))

        self.assertEqual(len(rows), 100)
        self.assertEqual(
            [row["product_id"] for row in rows],
            [f"P{number:03d}" for number in range(1, 101)],
        )
        self.assertEqual(
            {row["category"] for row in rows},
            {"Smartphone"},
        )

    def test_processing_the_raw_dataset_yields_no_invalid_rows(self) -> None:
        validated = process(pd.read_csv(RAW_FILE))

        self.assertEqual(len(validated), 100)
        self.assertEqual(
            validated["validation_status"].tolist(),
            ["valid"] * 100,
        )

    def test_quality_gate_passes_on_the_committed_processed_dataset(
        self,
    ) -> None:
        with redirect_stdout(io.StringIO()):
            passed = check_dataset_quality(pd.read_csv(PROCESSED_CSV_FILE))

        self.assertTrue(passed)

    def test_quality_gate_hard_codes_a_100_product_p001_to_p100_dataset(
        self,
    ) -> None:
        # Dropping any row breaks the gate purely because of the hard-coded
        # count. The category expansion must replace this rule deliberately.
        shortened = pd.read_csv(PROCESSED_CSV_FILE).head(99)

        with redirect_stdout(io.StringIO()):
            passed = check_dataset_quality(shortened)

        self.assertFalse(passed)

    def test_quality_gate_rejects_identifiers_outside_p001_to_p100(
        self,
    ) -> None:
        renamed = pd.read_csv(PROCESSED_CSV_FILE)
        renamed.loc[0, "product_id"] = "P101"

        with redirect_stdout(io.StringIO()):
            passed = check_dataset_quality(renamed)

        self.assertFalse(passed)

    def test_quality_gate_rejects_repeated_product_variants(self) -> None:
        duplicated = pd.read_csv(PROCESSED_CSV_FILE)
        for column in ("brand", "model", "storage_gb", "ram_gb", "color"):
            duplicated.loc[1, column] = duplicated.loc[0, column]

        with redirect_stdout(io.StringIO()):
            passed = check_dataset_quality(duplicated)

        self.assertFalse(passed)

    def test_evaluation_subset_is_ten_single_category_products(self) -> None:
        with SUBSET_FILE.open(encoding="utf-8-sig", newline="") as stream:
            subset = list(csv.DictReader(stream))

        self.assertEqual(len(subset), 10)
        self.assertEqual(
            len({row["product_id"] for row in subset}),
            10,
        )
        self.assertEqual(
            len({row["brand"] for row in subset}),
            10,
        )
        # The subset carries no category column at all, because every row is a
        # smartphone. Multi-category evaluation needs this to change.
        self.assertNotIn("category", subset[0])


if __name__ == "__main__":
    unittest.main()
