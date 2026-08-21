"""Dataset-level quality checks for the processed product data.

Row-level rules (missing values, numeric ranges, per-category attributes) are
already applied by the DataProcessor. This module checks properties that only
make sense for the dataset as a whole: identifier coverage, duplicate product
variants, source-URL completeness and - for the ten-category dataset - whether
every category group reached its expected product count.

Two quality profiles are supported:

SMARTPHONE_QUALITY
    The frozen 100-product smartphone dataset with identifiers P001-P100.

MULTICATEGORY_QUALITY
    The ten-category dataset. Expected identifiers and per-category counts are
    read from ``data/reference/product_categories.csv`` instead of being
    hard-coded, so adding or resizing a category needs no code change.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field, replace
from pathlib import Path

import pandas as pd

from category_taxonomy import (
    CategoryGroup,
    DEFAULT_TAXONOMY_FILE,
    load_category_groups,
)


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

PROCESSED_MULTICATEGORY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "processed_products_multicategory.csv"
)


# ==================================================
# Quality profiles
# ==================================================

@dataclass(frozen=True)
class QualityProfile:
    """Dataset-level expectations for one processed dataset."""

    name: str
    processed_file: Path
    expected_columns: list[str]
    # Columns that together identify one product variant. Two rows sharing all
    # of them are the same product under different IDs.
    variant_columns: list[str]
    # Every identifier the dataset is allowed to contain, built from the
    # taxonomy target. Anything outside this set is an unexpected identifier.
    expected_product_ids: set[str]
    # Minimum row count per category group; empty for single-category data.
    expected_category_counts: dict[str, int]
    # The taxonomy target, shown next to the minimum when they differ.
    category_targets: dict[str, int] = field(default_factory=dict)
    # Identifiers that must be present. Equals expected_product_ids unless a
    # lower per-category floor was requested.
    required_product_ids: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.required_product_ids:
            object.__setattr__(
                self,
                "required_product_ids",
                set(self.expected_product_ids),
            )

    @property
    def expected_row_count(self) -> int:
        return len(self.required_product_ids)


def build_smartphone_quality_profile() -> QualityProfile:
    """The frozen P001-P100 smartphone dataset contract."""

    return QualityProfile(
        name="smartphone",
        processed_file=PROCESSED_FILE,
        expected_columns=[
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
        variant_columns=[
            "brand",
            "model",
            "storage_gb",
            "ram_gb",
            "color",
        ],
        expected_product_ids={
            f"P{number:03d}"
            for number in range(1, 101)
        },
        expected_category_counts={},
    )


def build_multicategory_quality_profile(
    groups: list[CategoryGroup] | None = None,
    taxonomy_file: Path = DEFAULT_TAXONOMY_FILE,
    minimum_per_category: int | None = None,
) -> QualityProfile:
    """Derive the ten-category contract from the taxonomy reference file.

    ``minimum_per_category`` lowers the per-category floor below the taxonomy
    target. A listing site does not always publish fifty products that carry a
    usable specification - fashion is the clear case - so the gate can be run
    against the number actually reachable while the report still shows the
    target next to it.
    """

    if groups is None:
        groups = load_category_groups(taxonomy_file)

    def floor_for(group: CategoryGroup) -> int:
        if minimum_per_category is None:
            return group.expected_product_count

        return min(minimum_per_category, group.expected_product_count)

    # Allowed identifiers always run up to the taxonomy target, so a complete
    # category is never reported as holding unexpected identifiers.
    expected_product_ids = {
        group.product_id(number)
        for group in groups
        for number in range(1, group.expected_product_count + 1)
    }
    # Required identifiers stop at the floor, so a category that the site
    # cannot fill is not reported as missing the rest.
    required_product_ids = {
        group.product_id(number)
        for group in groups
        for number in range(1, floor_for(group) + 1)
    }

    return QualityProfile(
        name="multicategory",
        processed_file=PROCESSED_MULTICATEGORY_FILE,
        expected_columns=[
            "product_id",
            "product_name",
            "brand",
            "category",
            "category_group",
            "source_url",
            "attributes",
        ],
        # Product names already encode brand, model and variant, and the
        # remaining specs live in the attributes JSON.
        variant_columns=["brand", "product_name", "attributes"],
        expected_product_ids=expected_product_ids,
        required_product_ids=required_product_ids,
        expected_category_counts={
            group.category_group: floor_for(group)
            for group in groups
        },
        category_targets={
            group.category_group: group.expected_product_count
            for group in groups
        },
    )


SMARTPHONE_QUALITY = build_smartphone_quality_profile()


# ==================================================
# Processed data loading
# ==================================================

def load_processed_data(
    file_path: Path,
) -> pd.DataFrame:
    """
    DataProcessor tarafından oluşturulan
    processed CSV dosyasını yükler.
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
    profile: QualityProfile = SMARTPHONE_QUALITY,
) -> bool:
    """
    İşlenmiş veri setinin tamamına uygulanan
    dataset-level kalite kontrollerini gerçekleştirir.

    Eksik değer, numeric range ve validation status
    gibi row-level kontroller daha önce DataProcessor
    tarafından yapıldığı için burada tekrarlanmaz.
    """

    # Beklenen sütunlardan hangileri DataFrame'de yok?
    missing_columns = [
        column
        for column in profile.expected_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Processed dataset eksik sütun "
            f"içeriyor: {missing_columns}"
        )

    # CSV dosyasında gerçekten bulunan product_id'ler.
    actual_product_ids = set(
        df["product_id"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    # Zorunlu olup CSV'de bulunmayan ID'ler.
    missing_product_ids = (
        profile.required_product_ids
        - actual_product_ids
    )

    # CSV'de bulunan ancak beklenen aralıkta olmayan ID'ler.
    unexpected_product_ids = (
        actual_product_ids
        - profile.expected_product_ids
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
    # varyantının tekrar edip etmediğini kontrol eder.
    duplicate_product_rows = df[
        df.duplicated(
            subset=profile.variant_columns,
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

    # Kategori bazlı ürün sayıları yalnızca çok kategorili
    # veri setinde kontrol edilir.
    category_count_problems = find_category_count_problems(
        df=df,
        profile=profile,
    )

    # Dataset'in bütün kalite koşullarını geçip
    # geçmediğini belirleyen tek bir boolean değer.
    dataset_passed = (
        total_rows >= profile.expected_row_count
        and unique_product_ids == total_rows
        and not missing_product_ids
        and not unexpected_product_ids
        and duplicate_id_rows.empty
        and duplicate_product_rows.empty
        and missing_source_url_count == 0
        and invalid_source_url_rows.empty
        and not category_count_problems
    )

    # ==================================================
    # Quality report
    # ==================================================

    print()
    print("=== DATASET QUALITY REPORT ===")

    print(f"Dataset profile: {profile.name}")

    print(f"Total rows: {total_rows}")

    print(
        f"Expected rows: "
        f"{profile.expected_row_count}"
    )

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

    if profile.expected_category_counts:
        print(
            "Category groups with wrong counts: "
            f"{len(category_count_problems)}"
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
                ["product_id", "product_name", *profile.variant_columns]
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

    if profile.expected_category_counts:
        print()
        print("Products per category group:")

        actual_per_group = (
            df["category_group"]
            .fillna("")
            .astype(str)
            .str.strip()
            .value_counts()
            .to_dict()
        )

        for category_group in sorted(profile.expected_category_counts):
            actual = int(actual_per_group.get(category_group, 0))
            target = profile.category_targets.get(
                category_group,
                profile.expected_category_counts[category_group],
            )
            marker = "  " if actual >= target else " <- below target"
            print(f"  {category_group:28s} {actual:3d}/{target}{marker}")

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


def find_category_count_problems(
    df: pd.DataFrame,
    profile: QualityProfile,
) -> list[tuple[str, int, int]]:
    """
    Beklenen ürün sayısını tutturamayan kategori
    gruplarını (grup, beklenen, bulunan) olarak döndürür.
    """

    if not profile.expected_category_counts:
        return []

    if "category_group" not in df.columns:
        raise ValueError(
            "Processed dataset eksik sütun içeriyor: ['category_group']"
        )

    actual_counts = (
        df["category_group"]
        .fillna("")
        .astype(str)
        .str.strip()
        .value_counts()
        .to_dict()
    )

    problems: list[tuple[str, int, int]] = []

    for category_group, expected in sorted(
        profile.expected_category_counts.items()
    ):
        actual = int(actual_counts.get(category_group, 0))

        # A category may exceed its target; only a shortfall is a problem.
        if actual < expected:
            problems.append((category_group, expected, actual))

    # Taksonomide tanımlı olmayan bir kategori grubu da bir sorundur.
    for category_group in sorted(actual_counts):
        if category_group not in profile.expected_category_counts:
            problems.append(
                (
                    category_group,
                    0,
                    int(actual_counts[category_group]),
                )
            )

    return problems


# ==================================================
# Program entry point
# ==================================================

def main() -> None:
    """
    Processed dataset'i yükler ve dataset-level
    kalite kontrolünü çalıştırır.
    """

    parser = argparse.ArgumentParser(
        description="Run dataset-level quality checks on processed products."
    )
    parser.add_argument(
        "--dataset",
        choices=["smartphone", "multicategory"],
        default="smartphone",
    )
    parser.add_argument(
        "--taxonomy",
        type=Path,
        default=DEFAULT_TAXONOMY_FILE,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help=(
            "Check this processed file instead of the dataset's committed "
            "one."
        ),
    )
    parser.add_argument(
        "--categories",
        default="",
        help=(
            "Comma-separated category groups the run was meant to cover, "
            "instead of all ten."
        ),
    )
    parser.add_argument(
        "--min-per-category",
        type=int,
        default=None,
        help=(
            "Per-category floor for the gate. Defaults to the taxonomy "
            "target. The report always shows actual counts against the "
            "target regardless."
        ),
    )
    args = parser.parse_args()

    if args.dataset == "multicategory":
        groups = load_category_groups(args.taxonomy)
        wanted = [
            value.strip() for value in args.categories.split(",") if value.strip()
        ]

        if wanted:
            # A short collection run covers a few groups on purpose. Checking
            # it against all ten would report ten failures for a decision that
            # was made deliberately, so the gate is told which groups the run
            # was supposed to cover.
            known = {group.category_group for group in groups}
            unknown = [name for name in wanted if name not in known]

            if unknown:
                print(f"[ERROR] Unknown category group(s): {', '.join(unknown)}")
                raise SystemExit(1)

            selected = set(wanted)
            groups = [
                group for group in groups if group.category_group in selected
            ]

        profile = build_multicategory_quality_profile(
            groups=groups,
            minimum_per_category=args.min_per_category,
        )
    else:
        profile = SMARTPHONE_QUALITY

    if args.input is not None:
        profile = replace(profile, processed_file=args.input)

    processed_df = load_processed_data(
        profile.processed_file
    )

    passed = check_dataset_quality(
        processed_df,
        profile,
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
