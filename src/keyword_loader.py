"""Load and validate generated product keywords."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEYWORDS_FILE = PROJECT_ROOT / "data" / "processed" / "generated_keywords.json"


class KeywordLoaderError(ValueError):
    """Raised when generated keyword data is missing or invalid."""


@dataclass(frozen=True)
class KeywordRecord:
    product_id: str
    keyword: str

    def to_dict(self) -> dict[str, str]:
        return {
            "product_id": self.product_id,
            "keyword": self.keyword,
        }


def _validate_raw_record(raw_record: Any, index: int) -> KeywordRecord:
    if not isinstance(raw_record, dict):
        raise KeywordLoaderError(f"Keyword record at index {index} must be an object.")

    product_id = raw_record.get("product_id")
    keyword = raw_record.get("keyword")

    if not isinstance(product_id, str) or not product_id.strip():
        raise KeywordLoaderError(f"Keyword record at index {index} has an invalid product_id.")
    if not isinstance(keyword, str) or not keyword.strip():
        raise KeywordLoaderError(f"Keyword record at index {index} has an invalid keyword.")

    keyword = " ".join(keyword.strip().split())
    if len(keyword) < 5:
        raise KeywordLoaderError(f"Keyword for {product_id} is too short.")

    return KeywordRecord(
        product_id=product_id.strip(),
        keyword=keyword,
    )


def load_keywords(file_path: Path = DEFAULT_KEYWORDS_FILE, limit: int | None = None) -> list[KeywordRecord]:
    if not file_path.exists():
        raise FileNotFoundError(f"Generated keyword file was not found: {file_path}")

    raw_data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, list):
        raise KeywordLoaderError("Generated keywords file must contain a JSON list.")

    records: list[KeywordRecord] = []
    seen_pairs: set[tuple[str, str]] = set()

    for index, raw_record in enumerate(raw_data):
        record = _validate_raw_record(raw_record, index)
        pair = (record.product_id, record.keyword.lower())
        if pair in seen_pairs:
            raise KeywordLoaderError(
                f"Duplicate product_id/keyword pair found: {record.product_id} - {record.keyword}"
            )
        seen_pairs.add(pair)
        records.append(record)

        if limit is not None and len(records) >= limit:
            break

    if not records:
        raise KeywordLoaderError("Generated keyword file does not contain any valid records.")

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and preview generated keyword records.")
    parser.add_argument("--input", type=Path, default=DEFAULT_KEYWORDS_FILE)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    records = load_keywords(args.input, limit=args.limit)
    print(json.dumps([record.to_dict() for record in records], ensure_ascii=False, indent=2))
    print(f"Loaded keyword count: {len(records)}")


if __name__ == "__main__":
    main()
