from pathlib import Path

import pandas as pd


# ==================================================
# File paths
# ==================================================

# quality_check.py:
# first-task/src/quality_check.py
#
# İlk parent -> src
# İkinci parent -> first-task
PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "processed_products.csv"
)


# ==================================================
# Processed data loading
# ==================================================

def load_processed_data(
    file_path: Path,
) -> pd.DataFrame:
    """
    DataProcessor tarafından oluşturulan
    processed_products.csv dosyasını yükler.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Processed dataset bulunamadı: "
            f"{file_path}"
        )

    df = pd.read_csv(file_path)

    print(
        f"Processed dataset loaded: "
        f"{len(df)} products"
    )

    return df


# ==================================================
# Dataset-level quality checks
# ==================================================

def check_dataset_quality(
    df: pd.DataFrame,
) -> bool:
    """
    İşlenmiş veri setinin tamamına uygulanan
    dataset-level kalite kontrollerini gerçekleştirir.

    Eksik değer, numeric range ve validation status
    gibi row-level kontroller daha önce DataProcessor
    tarafından yapıldığı için burada tekrarlanmaz.
    """

    # Processed dataset içinde bulunması gereken sütunlar.
    expected_columns = [
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

    # Beklenen sütunlardan hangileri DataFrame'de yok?
    missing_columns = [
        column
        for column in expected_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Processed dataset eksik sütun "
            f"içeriyor: {missing_columns}"
        )

    # P001, P002, ..., P100 değerlerinden oluşan
    # beklenen product_id kümesi.
    expected_product_ids = {
        f"P{number:03d}"
        for number in range(1, 101)
    }

    # CSV dosyasında gerçekten bulunan product_id'ler.
    actual_product_ids = set(
        df["product_id"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    # Beklenen ancak CSV'de bulunmayan ID'ler.
    missing_product_ids = (
        expected_product_ids
        - actual_product_ids
    )

    # CSV'de bulunan ancak P001-P100 aralığında
    # olmayan ID'ler.
    unexpected_product_ids = (
        actual_product_ids
        - expected_product_ids
    )

    # Aynı product_id birden fazla satırda
    # kullanılmış mı?
    duplicate_id_rows = df[
        df.duplicated(
            subset=["product_id"],
            keep=False,
        )
    ]

    # ID değerleri farklı olsa bile aynı ürün
    # varyantının tekrar edip etmediğini kontrol
    # etmek için kullanılacak sütunlar.
    product_variant_columns = [
        "brand",
        "model",
        "storage_gb",
        "ram_gb",
        "color",
    ]

    duplicate_product_rows = df[
        df.duplicated(
            subset=product_variant_columns,
            keep=False,
        )
    ]

    source_url_values = (
        df["source_url"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    missing_source_url_count = (
        source_url_values
        .eq("")
        .sum()
    )

    invalid_source_url_rows = df[
        source_url_values.ne("")
        & ~source_url_values.str.match(
            r"^https://",
            na=False,
        )
    ]

    total_rows = len(df)

    unique_product_ids = (
        df["product_id"]
        .nunique()
    )

    # Dataset'in bütün kalite koşullarını geçip
    # geçmediğini belirleyen tek bir boolean değer.
    dataset_passed = (
        total_rows == 100
        and unique_product_ids == 100
        and not missing_product_ids
        and not unexpected_product_ids
        and duplicate_id_rows.empty
        and duplicate_product_rows.empty
        and missing_source_url_count == 0
        and invalid_source_url_rows.empty
    )

    # ==================================================
    # Quality report
    # ==================================================

    print()
    print("=== DATASET QUALITY REPORT ===")

    print(f"Total rows: {total_rows}")

    print(
        f"Unique product IDs: "
        f"{unique_product_ids}"
    )

    print(
        f"Missing product IDs: "
        f"{len(missing_product_ids)}"
    )

    print(
        f"Unexpected product IDs: "
        f"{len(unexpected_product_ids)}"
    )

    print(
        f"Duplicate ID rows: "
        f"{len(duplicate_id_rows)}"
    )

    print(
        "Duplicate product variant rows: "
        f"{len(duplicate_product_rows)}"
    )

    print(
        "Rows without source URL: "
        f"{missing_source_url_count}"
    )

    print(
        "Rows with invalid source URL: "
        f"{len(invalid_source_url_rows)}"
    )

    # Sorun varsa yalnızca sayısını değil,
    # ilgili kayıtları da göster.
    if missing_product_ids:
        print(
            "Missing IDs:",
            sorted(missing_product_ids),
        )

    if unexpected_product_ids:
        print(
            "Unexpected IDs:",
            sorted(unexpected_product_ids),
        )

    if not duplicate_id_rows.empty:
        print()
        print("Duplicate product IDs:")

        print(
            duplicate_id_rows[
                [
                    "product_id",
                    "product_name",
                ]
            ].to_string(index=False)
        )

    if not duplicate_product_rows.empty:
        print()
        print("Duplicate product variants:")

        print(
            duplicate_product_rows[
                [
                    "product_id",
                    "product_name",
                    "brand",
                    "model",
                    "storage_gb",
                    "ram_gb",
                    "color",
                ]
            ].to_string(index=False)
        )

    if not invalid_source_url_rows.empty:
        print()
        print("Invalid source URLs:")
        print(
            invalid_source_url_rows[
                [
                    "product_id",
                    "source_url",
                ]
            ].to_string(index=False)
        )

    print()

    if dataset_passed:
        print(
            "Dataset-level quality check: PASSED"
        )
    else:
        print(
            "Dataset-level quality check: FAILED"
        )

    return dataset_passed


# ==================================================
# Program entry point
# ==================================================

def main() -> None:
    """
    Processed dataset'i yükler ve dataset-level
    kalite kontrolünü çalıştırır.
    """

    processed_df = load_processed_data(
        PROCESSED_FILE
    )

    check_dataset_quality(
        processed_df
    )


if __name__ == "__main__":
    main()
