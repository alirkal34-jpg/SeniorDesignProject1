"""Load the product category taxonomy shared by the whole pipeline.

The advisor asked for the pipeline to be validated across ten e-commerce
category groups instead of smartphones alone. Every module that needs to know
which categories exist, how their product identifiers are built, or which
attributes a category must carry reads this single reference file so the
category list never drifts between the scraper, the processor and the reports.

Each product carries a small mandatory core plus a category-specific
``attributes`` mapping. ``variant_label`` is the one attribute every category
must supply: it is the shopping-relevant distinguishing spec that also becomes
part of the generated search keyword ("256 GB", "500 ml", "42 Numara").
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TAXONOMY_FILE = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "product_categories.csv"
)

REQUIRED_COLUMNS = (
    "category_group",
    "display_name_tr",
    "product_id_prefix",
    "expected_product_count",
    "required_attributes",
    "optional_attributes",
    "numeric_attribute_ranges",
)

# Supplied by every category, and used to build the search keyword.
UNIVERSAL_ATTRIBUTE = "variant_label"


class TaxonomyError(ValueError):
    """Raised when the category reference file is missing or inconsistent."""


@dataclass(frozen=True)
class CategoryGroup:
    """One advisor-specified category group."""

    category_group: str
    display_name_tr: str
    product_id_prefix: str
    expected_product_count: int
    # Attributes a product cannot be valid without. Kept deliberately small:
    # real listing pages publish a title and a price, not a spec sheet, so
    # requiring fields the source never states would reject valid products.
    required_attributes: tuple[str, ...] = ()
    # Attributes that enrich a product when the source happens to state them.
    # They are never required, but they are range-checked when present.
    optional_attributes: tuple[str, ...] = ()
    numeric_attribute_ranges: dict[str, tuple[float, float]] = field(
        default_factory=dict
    )

    def product_id(self, sequence_number: int) -> str:
        """Build the identifier for the nth product of this group."""

        if sequence_number < 1:
            raise TaxonomyError(
                f"Product sequence numbers start at 1, got {sequence_number}."
            )

        return f"{self.product_id_prefix}{sequence_number:03d}"

    def all_required_attributes(self) -> tuple[str, ...]:
        """Return the universal attribute plus this group's own requirements."""

        return (UNIVERSAL_ATTRIBUTE, *self.required_attributes)

    def all_known_attributes(self) -> tuple[str, ...]:
        """Every attribute this category recognises, required or not."""

        return (*self.all_required_attributes(), *self.optional_attributes)

    def missing_required_attributes(
        self,
        attributes: dict[str, object],
    ) -> tuple[str, ...]:
        """Return the required attribute names this product does not supply.

        Shared by the scraper, which uses it to skip unusable products while
        collecting, and by the DataProcessor, which reports them as row-level
        validation errors.
        """

        return tuple(
            name
            for name in self.all_required_attributes()
            if not str(attributes.get(name, "") or "").strip()
        )


def _parse_attribute_list(raw_value: str) -> tuple[str, ...]:
    """Parse a semicolon-separated attribute name list."""

    return tuple(
        part.strip()
        for part in raw_value.split(";")
        if part.strip()
    )


def _parse_numeric_ranges(
    raw_value: str,
    category_group: str,
) -> dict[str, tuple[float, float]]:
    """Parse ``name:min:max`` sanity ranges separated by semicolons."""

    ranges: dict[str, tuple[float, float]] = {}

    for part in raw_value.split(";"):
        entry = part.strip()

        if not entry:
            continue

        fields = entry.split(":")

        if len(fields) != 3:
            raise TaxonomyError(
                f"{category_group}: numeric range '{entry}' must be "
                "written as name:min:max."
            )

        name, raw_minimum, raw_maximum = (item.strip() for item in fields)

        try:
            minimum = float(raw_minimum)
            maximum = float(raw_maximum)
        except ValueError as error:
            raise TaxonomyError(
                f"{category_group}: numeric range '{entry}' has "
                "non-numeric bounds."
            ) from error

        if minimum > maximum:
            raise TaxonomyError(
                f"{category_group}: numeric range '{entry}' has a minimum "
                "above its maximum."
            )

        ranges[name] = (minimum, maximum)

    return ranges


def load_category_groups(
    file_path: Path = DEFAULT_TAXONOMY_FILE,
) -> list[CategoryGroup]:
    """Load every category group, preserving the order in the reference file."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Category taxonomy file was not found: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream)
        missing_columns = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])

        if missing_columns:
            raise TaxonomyError(
                "Category taxonomy file is missing columns: "
                f"{sorted(missing_columns)}"
            )

        groups: list[CategoryGroup] = []

        for row_number, row in enumerate(reader, start=2):
            category_group = (row.get("category_group") or "").strip()

            if not category_group:
                continue

            raw_count = (row.get("expected_product_count") or "").strip()

            try:
                expected_product_count = int(raw_count)
            except ValueError as error:
                raise TaxonomyError(
                    f"Row {row_number}: expected_product_count must be an "
                    f"integer, got {raw_count!r}."
                ) from error

            if expected_product_count < 1:
                raise TaxonomyError(
                    f"Row {row_number}: expected_product_count must be "
                    "positive."
                )

            prefix = (row.get("product_id_prefix") or "").strip()

            if not prefix:
                raise TaxonomyError(
                    f"Row {row_number}: product_id_prefix cannot be empty."
                )

            groups.append(
                CategoryGroup(
                    category_group=category_group,
                    display_name_tr=(
                        row.get("display_name_tr") or ""
                    ).strip(),
                    product_id_prefix=prefix,
                    expected_product_count=expected_product_count,
                    required_attributes=_parse_attribute_list(
                        row.get("required_attributes") or ""
                    ),
                    optional_attributes=_parse_attribute_list(
                        row.get("optional_attributes") or ""
                    ),
                    numeric_attribute_ranges=_parse_numeric_ranges(
                        row.get("numeric_attribute_ranges") or "",
                        category_group,
                    ),
                )
            )

    if not groups:
        raise TaxonomyError(
            f"Category taxonomy file contains no categories: {file_path}"
        )

    _reject_duplicates(groups)

    return groups


def _reject_duplicates(groups: list[CategoryGroup]) -> None:
    """Fail loudly when two categories share a name or identifier prefix."""

    seen_names: set[str] = set()
    seen_prefixes: set[str] = set()

    for group in groups:
        if group.category_group in seen_names:
            raise TaxonomyError(
                f"Duplicate category_group: {group.category_group}"
            )

        if group.product_id_prefix in seen_prefixes:
            raise TaxonomyError(
                f"Duplicate product_id_prefix: {group.product_id_prefix}"
            )

        seen_names.add(group.category_group)
        seen_prefixes.add(group.product_id_prefix)


def build_category_lookup(
    groups: list[CategoryGroup],
) -> dict[str, CategoryGroup]:
    """Index category groups by their canonical name."""

    return {group.category_group: group for group in groups}


def expected_dataset_size(groups: list[CategoryGroup]) -> int:
    """Return how many products a complete multi-category dataset holds."""

    return sum(group.expected_product_count for group in groups)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and summarize the product category taxonomy."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_TAXONOMY_FILE,
    )
    args = parser.parse_args()

    try:
        groups = load_category_groups(args.input)
    except (TaxonomyError, OSError) as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error

    print("=== PRODUCT CATEGORY TAXONOMY ===")
    print(f"Category groups: {len(groups)}")
    print(f"Expected dataset size: {expected_dataset_size(groups)}")
    print()

    for group in groups:
        print(f"{group.product_id_prefix}  {group.display_name_tr}")
        print(f"    canonical name:  {group.category_group}")
        print(
            "    product IDs:     "
            f"{group.product_id(1)}-"
            f"{group.product_id(group.expected_product_count)}"
        )
        print(
            "    required attrs:  "
            f"{', '.join(group.all_required_attributes())}"
        )

        if group.optional_attributes:
            print(
                "    optional attrs:  "
                f"{', '.join(group.optional_attributes)}"
            )

        if group.numeric_attribute_ranges:
            ranges = ", ".join(
                f"{name} {minimum:g}-{maximum:g}"
                for name, (minimum, maximum) in (
                    group.numeric_attribute_ranges.items()
                )
            )
            print(f"    numeric ranges:  {ranges}")


if __name__ == "__main__":
    main()
