"""Load and match human relevance labels for experiment results."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit


try:
    from .result_validator import ALLOWED_METHODS
except ImportError:
    from result_validator import ALLOWED_METHODS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GROUND_TRUTH_FILE = (
    PROJECT_ROOT
    / "data"
    / "labels"
    / "domain_ground_truth.csv"
)

REQUIRED_COLUMNS = {
    "product_id",
    "keyword",
    "domain",
    "url",
    "human_relevant",
    "notes",
}

TRUE_VALUES = {"1", "true", "yes", "y", "evet"}
FALSE_VALUES = {"0", "false", "no", "n", "hayir", "hayır"}

GroundTruthKey = tuple[str, str, str, str, str]
GroundTruthLookup = dict[GroundTruthKey, bool]


class GroundTruthError(ValueError):
    """Raised when human-label data is missing or invalid."""


@dataclass(frozen=True)
class GroundTruthRecord:
    """One human relevance decision.

    A blank method means that the label is shared by every evaluation method.
    """

    product_id: str
    keyword: str
    domain: str
    url: str
    human_relevant: bool
    notes: str = ""
    method: str = ""


def normalize_text(value: str) -> str:
    """Normalize text used in a ground-truth lookup key."""

    return " ".join(value.strip().lower().split())


def normalize_url(value: str) -> str:
    """Normalize a URL without changing its query parameters."""

    raw_url = value.strip()
    parsed = urlsplit(raw_url)

    if parsed.scheme.lower() not in {"http", "https"}:
        raise GroundTruthError(
            f"Ground-truth URL must start with http:// or https://: {value}"
        )

    normalized_path = parsed.path.rstrip("/") or "/"

    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            parsed.query,
            "",
        )
    )


def parse_human_relevant(value: str, row_number: int) -> bool:
    """Parse a human label from common CSV boolean values."""

    normalized = normalize_text(value)

    if normalized in TRUE_VALUES:
        return True

    if normalized in FALSE_VALUES:
        return False

    raise GroundTruthError(
        f"Row {row_number}: human_relevant must be one of "
        f"{sorted(TRUE_VALUES | FALSE_VALUES)}."
    )


def require_value(
    row: dict[str, str | None],
    field_name: str,
    row_number: int,
) -> str:
    """Read one required non-empty CSV field."""

    value = row.get(field_name)

    if value is None or not value.strip():
        raise GroundTruthError(
            f"Row {row_number}: '{field_name}' cannot be empty."
        )

    return value.strip()


def load_ground_truth(
    file_path: Path = DEFAULT_GROUND_TRUTH_FILE,
) -> list[GroundTruthRecord]:
    """Load human labels from a UTF-8 CSV file."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Ground-truth file was not found: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = REQUIRED_COLUMNS - fieldnames

        if missing_columns:
            raise GroundTruthError(
                "Ground-truth CSV is missing columns: "
                f"{sorted(missing_columns)}"
            )

        records: list[GroundTruthRecord] = []

        for row_number, row in enumerate(reader, start=2):
            if not any(
                (value or "").strip()
                for value in row.values()
            ):
                continue

            method = (row.get("method") or "").strip()

            if method and method not in ALLOWED_METHODS:
                raise GroundTruthError(
                    f"Row {row_number}: unsupported method '{method}'."
                )

            records.append(
                GroundTruthRecord(
                    product_id=require_value(
                        row,
                        "product_id",
                        row_number,
                    ),
                    keyword=require_value(
                        row,
                        "keyword",
                        row_number,
                    ),
                    domain=require_value(
                        row,
                        "domain",
                        row_number,
                    ),
                    url=normalize_url(
                        require_value(
                            row,
                            "url",
                            row_number,
                        )
                    ),
                    human_relevant=parse_human_relevant(
                        require_value(
                            row,
                            "human_relevant",
                            row_number,
                        ),
                        row_number,
                    ),
                    notes=(row.get("notes") or "").strip(),
                    method=method,
                )
            )

    return records


def make_ground_truth_key(
    product_id: str,
    keyword: str,
    domain: str,
    url: str,
    method: str = "",
) -> GroundTruthKey:
    """Build the normalized lookup key used for matching labels."""

    return (
        normalize_text(product_id),
        normalize_text(keyword),
        normalize_text(domain),
        normalize_url(url),
        normalize_text(method),
    )


def build_ground_truth_lookup(
    records: Iterable[GroundTruthRecord],
) -> GroundTruthLookup:
    """Create a fast lookup and reject duplicate label keys."""

    lookup: GroundTruthLookup = {}

    for record in records:
        key = make_ground_truth_key(
            product_id=record.product_id,
            keyword=record.keyword,
            domain=record.domain,
            url=record.url,
            method=record.method,
        )

        if key in lookup:
            raise GroundTruthError(
                "Duplicate ground-truth label for "
                f"{record.product_id}, {record.domain}, {record.url}, "
                f"method={record.method or '<shared>'}."
            )

        lookup[key] = record.human_relevant

    return lookup


def find_human_label(
    lookup: GroundTruthLookup,
    product_id: str,
    keyword: str,
    method: str,
    domain: str,
    url: str,
) -> bool | None:
    """Find a method-specific label, then fall back to a shared label."""

    method_key = make_ground_truth_key(
        product_id=product_id,
        keyword=keyword,
        domain=domain,
        url=url,
        method=method,
    )

    if method_key in lookup:
        return lookup[method_key]

    shared_key = make_ground_truth_key(
        product_id=product_id,
        keyword=keyword,
        domain=domain,
        url=url,
    )

    return lookup.get(shared_key)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and summarize human ground-truth labels."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_GROUND_TRUTH_FILE,
    )
    args = parser.parse_args()

    try:
        records = load_ground_truth(args.input)
        build_ground_truth_lookup(records)
    except (GroundTruthError, OSError) as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error

    shared_count = sum(
        1
        for record in records
        if not record.method
    )

    print("=== GROUND-TRUTH SUMMARY ===")
    print(f"Label count: {len(records)}")
    print(f"Shared labels: {shared_count}")
    print(f"Method-specific labels: {len(records) - shared_count}")


if __name__ == "__main__":
    main()
