from pathlib import Path

import pandas as pd


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
# Data contract
# ==================================================

# These columns must exist in the dataset structure.
# Their order is also used in the processed output.
SCHEMA_COLUMNS = [
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
]


# These columns must contain a value for every product.
NON_NULL_COLUMNS = [
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
]


# These columns must exist, but their values may be empty.
NULLABLE_COLUMNS = [
]


# Columns that will be processed as text.
TEXT_COLUMNS = [
    "product_id",
    "product_name",
    "brand",
    "model",
    "category",
    "color",
    "operating_system",
    "source_url",
]


# Columns that will be converted to numeric values.
NUMERIC_COLUMNS = [
    "storage_gb",
    "ram_gb",
    "display_size_inch",
    "battery_mah",
]


# Sanity-check ranges used to detect clearly invalid values.
VALID_RANGES = {
    "storage_gb": (16, 2048),
    "ram_gb": (1, 64),
    "display_size_inch": (3, 10),
    "battery_mah": (1000, 15000),
}


# ==================================================
# Data loading
# ==================================================

def load_data() -> pd.DataFrame:
    """
    Load the raw product dataset from the CSV file.

    Returns:
        A Pandas DataFrame containing the raw product data.
    """

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file could not be found: {INPUT_FILE}"
        )

    products = pd.read_csv(INPUT_FILE)

    print(f"Raw dataset loaded: {len(products)} products")

    return products


# ==================================================
# Structural schema validation
# ==================================================

def validate_schema(df: pd.DataFrame) -> None:
    """
    Validate the structural schema of the dataset.

    This function checks whether all columns defined in
    SCHEMA_COLUMNS exist in the input dataset.

    It does not check whether individual product values
    are missing. Row-level value validation is performed
    later by validate_data().
    """

    missing_columns = [
        column
        for column in SCHEMA_COLUMNS
        if column not in df.columns
    ]

    unexpected_columns = [
        column
        for column in df.columns
        if column not in SCHEMA_COLUMNS
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

def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize text-based columns.
    """

    for column in TEXT_COLUMNS:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    category_mapping = {
        "smartphone": "Smartphone",
        "smart phone": "Smartphone",
        "mobile phone": "Smartphone",
    }

    operating_system_mapping = {
        "android": "Android",
        "ios": "iOS",
    }

    df["category"] = (
        df["category"]
        .str.lower()
        .replace(category_mapping)
    )

    df["operating_system"] = (
        df["operating_system"]
        .str.lower()
        .replace(operating_system_mapping)
    )

    return df


def clean_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert columns defined in NUMERIC_COLUMNS into
    actual numeric values.

    Values that cannot be converted are changed to NaN.
    They will be detected during row-level validation.
    """

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all cleaning and standardization operations.
    """

    # Keep the defined schema and enforce its column order.
    df = df[SCHEMA_COLUMNS].copy()

    df = clean_text_columns(df)
    df = clean_numeric_columns(df)

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
) -> pd.DataFrame:
    """
    Check that every column defined in NON_NULL_COLUMNS
    contains a value for each product.
    """

    for column in NON_NULL_COLUMNS:
        if column in NUMERIC_COLUMNS:
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
) -> pd.DataFrame:
    """
    Check whether numeric values are inside their
    expected sanity-check ranges.
    """

    for column, limits in VALID_RANGES.items():
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


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run all row-level data-quality validation rules.
    """

    df["validation_errors"] = ""

    df = validate_non_null_values(df)
    df = validate_source_urls(df)
    df = validate_duplicates(df)
    df = validate_numeric_ranges(df)
    df = assign_validation_status(df)

    print("Row-level data validation completed.")

    return df


# ==================================================
# Output generation
# ==================================================

def save_results(df: pd.DataFrame) -> None:
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
        SCHEMA_COLUMNS,
    ].copy()

    invalid_products = df.loc[
        df["validation_status"] == "invalid"
    ].copy()

    valid_products.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    valid_products.to_json(
        OUTPUT_JSON,
        orient="records",
        indent=2,
        force_ascii=False,
    )

    invalid_products.to_csv(
        VALIDATION_REPORT,
        index=False,
    )

    print()
    print("Data processing completed.")
    print(f"Total products: {len(df)}")
    print(f"Valid products: {len(valid_products)}")
    print(f"Invalid products: {len(invalid_products)}")
    print()
    print(f"Processed CSV: {OUTPUT_CSV}")
    print(f"Processed JSON: {OUTPUT_JSON}")
    print(f"Validation report: {VALIDATION_REPORT}")


# ==================================================
# Pipeline entry point
# ==================================================

def main() -> None:
    """
    Execute the complete DataProcessor pipeline.
    """

    products = load_data()

    validate_schema(products)

    products = clean_data(products)
    products = validate_data(products)

    save_results(products)


if __name__ == "__main__":
    main()
