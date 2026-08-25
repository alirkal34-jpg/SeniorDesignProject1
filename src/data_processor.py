"""Standardize and validate raw product data.

The processor is driven by a DatasetProfile so the same cleaning and validation
code serves two datasets:

SMARTPHONE_PROFILE
    The original 100-product smartphone dataset. Its column list, mandatory
    columns and numeric ranges are frozen, because the committed evaluation
    report was produced from it.

MULTICATEGORY_PROFILE
    The ten-category dataset requested by the advisor. It keeps a small
    mandatory core and moves every category-specific field into an
    ``attributes`` JSON column, validated per category group against
    ``data/reference/product_categories.csv``.

Module-level names such as SCHEMA_COLUMNS still describe the smartphone
profile, so existing callers and tests keep working unchanged.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, replace
from pathlib import Path

import pandas as pd

from category_taxonomy import (
    CategoryGroup,
    DEFAULT_TAXONOMY_FILE,
    build_category_lookup,
    load_category_groups,
)


# ==================================================
# File paths
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "candidate_smartphone_products_100.csv"
)

OUTPUT_DIRECTORY = BASE_DIR / "data" / "processed"

OUTPUT_CSV = OUTPUT_DIRECTORY / "processed_products.csv"
OUTPUT_JSON = OUTPUT_DIRECTORY / "processed_products.json"
VALIDATION_REPORT = OUTPUT_DIRECTORY / "validation_issues.csv"


# ==================================================
# Dataset profiles
# ==================================================

@dataclass(frozen=True)
class DatasetProfile:
    """The data contract for one raw dataset."""

    name: str
    input_file: Path
    schema_columns: list[str]
    non_null_columns: list[str]
    nullable_columns: list[str]
    text_columns: list[str]
    numeric_columns: list[str]
    valid_ranges: dict[str, tuple[float, float]]
    output_csv: Path
    output_json: Path
    validation_report: Path
    # Category-aware profiles additionally validate the attributes column
    # against the category taxonomy.
    category_aware: bool = False
    text_value_mappings: dict[str, dict[str, str]] = field(
        default_factory=dict
    )


SMARTPHONE_PROFILE = DatasetProfile(
    name="smartphone",
    input_file=INPUT_FILE,
    schema_columns=[
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
    non_null_columns=[
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
    nullable_columns=[],
    text_columns=[
        "product_id",
        "product_name",
        "brand",
        "model",
        "category",
        "color",
        "operating_system",
        "source_url",
    ],
    numeric_columns=[
        "storage_gb",
        "ram_gb",
        "display_size_inch",
        "battery_mah",
    ],
    valid_ranges={
        "storage_gb": (16, 2048),
        "ram_gb": (1, 64),
        "display_size_inch": (3, 10),
        "battery_mah": (1000, 15000),
    },
    output_csv=OUTPUT_CSV,
    output_json=OUTPUT_JSON,
    validation_report=VALIDATION_REPORT,
    text_value_mappings={
        "category": {
            "smartphone": "Smartphone",
            "smart phone": "Smartphone",
            "mobile phone": "Smartphone",
        },
        "operating_system": {
            "android": "Android",
            "ios": "iOS",
        },
    },
)


MULTICATEGORY_PROFILE = DatasetProfile(
    name="multicategory",
    input_file=(
        BASE_DIR
        / "data"
        / "raw"
        / "candidate_products_multicategory.csv"
    ),
    schema_columns=[
        "product_id",
        "product_name",
        "brand",
        "category",
        "category_group",
        "source_url",
        "attributes",
    ],
    non_null_columns=[
        "product_id",
        "product_name",
        "brand",
        "category",
        "category_group",
        "source_url",
        "attributes",
    ],
    nullable_columns=[],
    text_columns=[
        "product_id",
        "product_name",
        "brand",
        "category",
        "category_group",
        "source_url",
        "attributes",
    ],
    numeric_columns=[],
    valid_ranges={},
    output_csv=OUTPUT_DIRECTORY / "processed_products_multicategory.csv",
    output_json=OUTPUT_DIRECTORY / "processed_products_multicategory.json",
    validation_report=(
        OUTPUT_DIRECTORY / "validation_issues_multicategory.csv"
    ),
    category_aware=True,
)


PROFILES = {
    SMARTPHONE_PROFILE.name: SMARTPHONE_PROFILE,
    MULTICATEGORY_PROFILE.name: MULTICATEGORY_PROFILE,
}


# ==================================================
# Data contract (smartphone profile)
# ==================================================

# These columns must exist in the dataset structure.
# Their order is also used in the processed output.
SCHEMA_COLUMNS = SMARTPHONE_PROFILE.schema_columns

# These columns must contain a value for every product.
NON_NULL_COLUMNS = SMARTPHONE_PROFILE.non_null_columns

# These columns must exist, but their values may be empty.
NULLABLE_COLUMNS = SMARTPHONE_PROFILE.nullable_columns

# Columns that will be processed as text.
TEXT_COLUMNS = SMARTPHONE_PROFILE.text_columns

# Columns that will be converted to numeric values.
NUMERIC_COLUMNS = SMARTPHONE_PROFILE.numeric_columns

# Sanity-check ranges used to detect clearly invalid values.
VALID_RANGES = SMARTPHONE_PROFILE.valid_ranges


# ==================================================
# Data loading
# ==================================================

def load_data(
    profile: DatasetProfile = SMARTPHONE_PROFILE,
) -> pd.DataFrame:
    """
    Load the raw product dataset from the CSV file.

    Returns:
        A Pandas DataFrame containing the raw product data.
    """

    if not profile.input_file.exists():
        raise FileNotFoundError(
            f"Input file could not be found: {profile.input_file}"
        )

    products = pd.read_csv(profile.input_file)

    print(f"Raw dataset loaded: {len(products)} products")

    return products


# ==================================================
# Structural schema validation
# ==================================================

def validate_schema(
    df: pd.DataFrame,
    profile: DatasetProfile = SMARTPHONE_PROFILE,
) -> None:
    """
    Validate the structural schema of the dataset.

    This function checks whether all columns defined in the profile's schema
    exist in the input dataset.

    It does not check whether individual product values
    are missing. Row-level value validation is performed
    later by validate_data().
    """

    missing_columns = [
        column
        for column in profile.schema_columns
        if column not in df.columns
    ]

    unexpected_columns = [
        column
        for column in df.columns
        if column not in profile.schema_columns
    ]

    if missing_columns:
        raise ValueError(
            f"Schema validation failed. "
            f"Missing columns: {missing_columns}"
        )

    if unexpected_columns:
        print(
            "Warning: The following unexpected columns "
            f"will not be included in the processed output: "
            f"{unexpected_columns}"
        )

    print("Schema validation passed.")


# ==================================================
# Data cleaning and standardization
# ==================================================

def clean_text_columns(
    df: pd.DataFrame,
    profile: DatasetProfile = SMARTPHONE_PROFILE,
) -> pd.DataFrame:
    """
    Clean and standardize text-based columns.
    """

    for column in profile.text_columns:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # Columns with a controlled vocabulary are lowercased first, then mapped
    # back to their canonical spelling.
    for column, mapping in profile.text_value_mappings.items():
        if column not in df.columns:
            continue

        df[column] = (
            df[column]
            .str.lower()
            .replace(mapping)
        )

    return df


def clean_numeric_columns(
    df: pd.DataFrame,
    profile: DatasetProfile = SMARTPHONE_PROFILE,
) -> pd.DataFrame:
    """
    Convert columns defined in the profile's numeric list into
    actual numeric values.

    Values that cannot be converted are changed to NaN.
    They will be detected during row-level validation.
    """

    for column in profile.numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    return df


def clean_data(
    df: pd.DataFrame,
    profile: DatasetProfile = SMARTPHONE_PROFILE,
) -> pd.DataFrame:
    """
    Apply all cleaning and standardization operations.
    """

    # Keep the defined schema and enforce its column order.
    df = df[profile.schema_columns].copy()

    df = clean_text_columns(df, profile)
    df = clean_numeric_columns(df, profile)

    print("Data cleaning and standardization completed.")

    return df


# ==================================================
# Row-level data-quality validation
# ==================================================

def add_validation_error(
    df: pd.DataFrame,
    condition: pd.Series,
    error_message: str,
) -> None:
    """
    Add an error message to rows matching the condition.
    """

    df.loc[
        condition,
        "validation_errors",
    ] += f"{error_message};"


def validate_non_null_values(
    df: pd.DataFrame,
    profile: DatasetProfile = SMARTPHONE_PROFILE,
) -> pd.DataFrame:
    """
    Check that every column defined as non-null in the profile
    contains a value for each product.
    """

    for column in profile.non_null_columns:
        if column in profile.numeric_columns:
            missing_condition = df[column].isna()
        else:
            missing_condition = df[column] == ""

        add_validation_error(
            df,
            missing_condition,
            f"missing_{column}",
        )

    return df


def validate_source_urls(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Require non-empty source URLs to use HTTPS.

    Missing URLs are reported by validate_non_null_values().
    """

    invalid_source_url_condition = (
        df["source_url"].ne("")
        & ~df["source_url"].str.match(
            r"^https://",
            na=False,
        )
    )

    add_validation_error(
        df,
        invalid_source_url_condition,
        "invalid_source_url",
    )

    return df


def validate_duplicates(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Detect duplicate product IDs and product names.
    Empty values are excluded because they are already
    handled by non-null validation.
    """

    duplicate_id_condition = (
        df["product_id"].ne("")
        & df["product_id"].duplicated(
            keep=False
        )
    )

    add_validation_error(
        df,
        duplicate_id_condition,
        "duplicate_product_id",
    )

    normalized_product_names = (
        df["product_name"]
        .str.lower()
        .str.strip()
    )

    duplicate_name_condition = (
        normalized_product_names.ne("")
        & normalized_product_names.duplicated(
            keep=False
        )
    )

    add_validation_error(
        df,
        duplicate_name_condition,
        "duplicate_product_name",
    )

    return df


def validate_numeric_ranges(
    df: pd.DataFrame,
    profile: DatasetProfile = SMARTPHONE_PROFILE,
) -> pd.DataFrame:
    """
    Check whether numeric values are inside their
    expected sanity-check ranges.
    """

    for column, limits in profile.valid_ranges.items():
        minimum, maximum = limits

        invalid_range_condition = (
            df[column].notna()
            & ~df[column].between(
                minimum,
                maximum,
            )
        )

        add_validation_error(
            df,
            invalid_range_condition,
            f"invalid_{column}",
        )

    return df


# ==================================================
# Category-aware attribute validation
# ==================================================

def describe_attribute_errors(
    raw_attributes: str,
    category_group_name: str,
    category_lookup: dict[str, CategoryGroup],
) -> list[str]:
    """
    Validate one product's category and attributes JSON.

    Returns the error codes for this row, using the same
    missing_/invalid_ vocabulary as the column-level checks.
    """

    group = category_lookup.get(category_group_name)

    if group is None:
        # Without a known category there is no rule set to apply, so the
        # attributes cannot be checked any further.
        return ["unknown_category_group"]

    try:
        attributes = json.loads(raw_attributes)
    except (TypeError, ValueError):
        return ["invalid_attributes_json"]

    if not isinstance(attributes, dict):
        return ["invalid_attributes_json"]

    errors: list[str] = [
        f"missing_attribute_{name}"
        for name in group.missing_required_attributes(attributes)
    ]

    for attribute_name, limits in group.numeric_attribute_ranges.items():
        if f"missing_attribute_{attribute_name}" in errors:
            continue

        if attribute_name not in attributes:
            continue

        minimum, maximum = limits

        try:
            value = float(attributes[attribute_name])
        except (TypeError, ValueError):
            errors.append(f"invalid_attribute_{attribute_name}")
            continue

        if not minimum <= value <= maximum:
            errors.append(f"invalid_attribute_{attribute_name}")

    return errors


def validate_category_attributes(
    df: pd.DataFrame,
    category_lookup: dict[str, CategoryGroup],
) -> pd.DataFrame:
    """
    Apply the per-category attribute rules to every row.
    """

    for index in df.index:
        errors = describe_attribute_errors(
            raw_attributes=df.at[index, "attributes"],
            category_group_name=df.at[index, "category_group"],
            category_lookup=category_lookup,
        )

        for error_message in errors:
            df.at[index, "validation_errors"] += f"{error_message};"

    return df


def assign_validation_status(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign valid or invalid status based on validation
    error messages.
    """

    df["validation_errors"] = (
        df["validation_errors"]
        .str.rstrip(";")
    )

    df["validation_status"] = (
        df["validation_errors"]
        .apply(
            lambda errors: (
                "valid"
                if errors == ""
                else "invalid"
            )
        )
    )

    return df


def validate_data(
    df: pd.DataFrame,
    profile: DatasetProfile = SMARTPHONE_PROFILE,
    taxonomy_file: Path = DEFAULT_TAXONOMY_FILE,
) -> pd.DataFrame:
    """
    Run all row-level data-quality validation rules.

    This is the "489/489 valid" DataProcessor quality gate: every check
    below (missing values, non-HTTPS URLs, duplicates, out-of-range
    numbers, and, for the multi-category profile, per-category attributes)
    appends to the same validation_errors column, and
    assign_validation_status() turns "no errors accumulated" into
    validation_status="valid" for save_results() to act on.
    """

    df["validation_errors"] = ""

    df = validate_non_null_values(df, profile)
    df = validate_source_urls(df)
    df = validate_duplicates(df)
    df = validate_numeric_ranges(df, profile)

    if profile.category_aware:
        category_lookup = build_category_lookup(
            load_category_groups(taxonomy_file)
        )
        df = validate_category_attributes(df, category_lookup)

    df = assign_validation_status(df)

    print("Row-level data validation completed.")

    return df


# ==================================================
# Output generation
# ==================================================

def save_results(
    df: pd.DataFrame,
    profile: DatasetProfile = SMARTPHONE_PROFILE,
) -> None:
    """
    Separate valid and invalid products and write
    the final outputs.
    """

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    valid_products = df.loc[
        df["validation_status"] == "valid",
        profile.schema_columns,
    ].copy()

    invalid_products = df.loc[
        df["validation_status"] == "invalid"
    ].copy()

    valid_products.to_csv(
        profile.output_csv,
        index=False,
    )

    valid_products.to_json(
        profile.output_json,
        orient="records",
        indent=2,
        force_ascii=False,
    )

    invalid_products.to_csv(
        profile.validation_report,
        index=False,
    )

    print()
    print("Data processing completed.")
    print(f"Dataset profile: {profile.name}")
    print(f"Total products: {len(df)}")
    print(f"Valid products: {len(valid_products)}")
    print(f"Invalid products: {len(invalid_products)}")
    print()
    print(f"Processed CSV: {profile.output_csv}")
    print(f"Processed JSON: {profile.output_json}")
    print(f"Validation report: {profile.validation_report}")


# ==================================================
# Pipeline entry point
# ==================================================

def main() -> None:
    """
    Execute the complete DataProcessor pipeline.
    """

    parser = argparse.ArgumentParser(
        description="Standardize and validate a raw product dataset."
    )
    parser.add_argument(
        "--dataset",
        choices=sorted(PROFILES),
        default=SMARTPHONE_PROFILE.name,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help=(
            "Read this raw CSV instead of the dataset's committed one. The "
            "contract - schema, cleaning and validation - is unchanged; only "
            "the file it is applied to differs."
        ),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=None,
        help=(
            "Write the processed CSV, JSON and validation report here "
            "instead of data/processed/, keeping a demonstration run out of "
            "the committed dataset."
        ),
    )
    args = parser.parse_args()

    profile = PROFILES[args.dataset]

    if args.input is not None:
        profile = replace(profile, input_file=args.input)

    if args.output_directory is not None:
        args.output_directory.mkdir(parents=True, exist_ok=True)
        profile = replace(
            profile,
            output_csv=args.output_directory / profile.output_csv.name,
            output_json=args.output_directory / profile.output_json.name,
            validation_report=(
                args.output_directory / profile.validation_report.name
            ),
        )

    products = load_data(profile)

    validate_schema(products, profile)

    products = clean_data(products, profile)
    products = validate_data(products, profile)

    save_results(products, profile)


if __name__ == "__main__":
    main()
