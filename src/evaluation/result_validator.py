"""Validate experiment result JSON files.

Every evaluation method must produce the same basic JSON structure.
This module checks that structure without modifying the result files.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_DIRECTORY = PROJECT_ROOT / "results"

ALLOWED_METHODS = {
    "tavily_llm",
    "agentic_search",
    "selenium_nano_llm",
    "selenium_rule_based",
}

REQUIRED_PAYLOAD_FIELDS = {
    "product_id",
    "keyword",
    "method",
    "execution_mode",
    "provider",
    "model",
    "prompt_version",
    "runtime_seconds",
    "estimated_cost_usd",
    "results",
}

REQUIRED_RESULT_FIELDS = {
    "domain",
    "url",
    "title",
    "snippet",
    "predicted_relevant",
    "relevance_score",
}


class ResultValidationError(ValueError):
    """Raised when a result JSON file does not match the common schema."""


def is_number(value: Any) -> bool:
    """Return True for finite int/float values, but not booleans."""

    if isinstance(value, bool):
        return False

    if not isinstance(value, (int, float)):
        return False

    return math.isfinite(float(value))


def require_non_empty_string(
    value: Any,
    field_name: str,
    context: str,
) -> str:
    """Validate and normalize a required string field."""

    if not isinstance(value, str) or not value.strip():
        raise ResultValidationError(
            f"{context}: '{field_name}' must be a non-empty string."
        )

    return value.strip()


def validate_result_item(
    item: Any,
    index: int,
    source: str,
) -> None:
    """Validate one search result inside the results list."""

    context = f"{source}: results[{index}]"

    if not isinstance(item, dict):
        raise ResultValidationError(
            f"{context} must be a JSON object."
        )

    missing_fields = REQUIRED_RESULT_FIELDS - item.keys()

    if missing_fields:
        raise ResultValidationError(
            f"{context} is missing fields: "
            f"{sorted(missing_fields)}"
        )

    require_non_empty_string(
        item["domain"],
        "domain",
        context,
    )

    url = require_non_empty_string(
        item["url"],
        "url",
        context,
    )

    if not url.startswith(("http://", "https://")):
        raise ResultValidationError(
            f"{context}: 'url' must start with http:// or https://."
        )

    require_non_empty_string(
        item["title"],
        "title",
        context,
    )

    if not isinstance(item["snippet"], str):
        raise ResultValidationError(
            f"{context}: 'snippet' must be a string."
        )

    if not isinstance(item["predicted_relevant"], bool):
        raise ResultValidationError(
            f"{context}: 'predicted_relevant' must be boolean."
        )

    relevance_score = item["relevance_score"]

    if not is_number(relevance_score):
        raise ResultValidationError(
            f"{context}: 'relevance_score' must be a finite number."
        )

    if not 0.0 <= float(relevance_score) <= 1.0:
        raise ResultValidationError(
            f"{context}: 'relevance_score' must be between 0 and 1."
        )


def validate_result_payload(
    payload: Any,
    source: str = "<memory>",
) -> dict[str, Any]:
    """Validate one complete experiment result payload."""

    if not isinstance(payload, dict):
        raise ResultValidationError(
            f"{source}: top-level JSON value must be an object."
        )

    missing_fields = REQUIRED_PAYLOAD_FIELDS - payload.keys()

    if missing_fields:
        raise ResultValidationError(
            f"{source} is missing fields: "
            f"{sorted(missing_fields)}"
        )

    require_non_empty_string(
        payload["product_id"],
        "product_id",
        source,
    )

    require_non_empty_string(
        payload["keyword"],
        "keyword",
        source,
    )

    method = require_non_empty_string(
        payload["method"],
        "method",
        source,
    )

    if method not in ALLOWED_METHODS:
        raise ResultValidationError(
            f"{source}: unsupported method '{method}'. "
            f"Allowed methods: {sorted(ALLOWED_METHODS)}"
        )

    execution_mode = require_non_empty_string(
        payload["execution_mode"],
        "execution_mode",
        source,
    )
    if execution_mode not in {"fake", "live"}:
        raise ResultValidationError(
            f"{source}: 'execution_mode' must be 'fake' or 'live'."
        )

    provider = require_non_empty_string(
        payload["provider"],
        "provider",
        source,
    )
    require_non_empty_string(
        payload["model"],
        "model",
        source,
    )
    require_non_empty_string(
        payload["prompt_version"],
        "prompt_version",
        source,
    )
    if execution_mode == "live" and "fake" in provider.casefold():
        raise ResultValidationError(
            f"{source}: a live result cannot declare a fake provider."
        )

    runtime_seconds = payload["runtime_seconds"]

    if not is_number(runtime_seconds):
        raise ResultValidationError(
            f"{source}: 'runtime_seconds' must be a finite number."
        )

    if float(runtime_seconds) < 0:
        raise ResultValidationError(
            f"{source}: 'runtime_seconds' cannot be negative."
        )

    estimated_cost = payload["estimated_cost_usd"]

    if not is_number(estimated_cost):
        raise ResultValidationError(
            f"{source}: 'estimated_cost_usd' must be a finite number."
        )

    if float(estimated_cost) < 0:
        raise ResultValidationError(
            f"{source}: 'estimated_cost_usd' cannot be negative."
        )

    results = payload["results"]

    if not isinstance(results, list):
        raise ResultValidationError(
            f"{source}: 'results' must be a JSON list."
        )

    if len(results) > 5:
        raise ResultValidationError(
            f"{source}: 'results' cannot contain more than 5 items."
        )

    if not results:
        raise ResultValidationError(
            f"{source}: 'results' cannot be empty."
        )

    for index, item in enumerate(results):
        validate_result_item(
            item=item,
            index=index,
            source=source,
        )

    return payload


def validate_result_file(
    file_path: Path,
) -> dict[str, Any]:
    """Read and validate one result JSON file."""

    try:
        raw_text = file_path.read_text(
            encoding="utf-8-sig"
        )

        payload = json.loads(raw_text)

    except FileNotFoundError as error:
        raise ResultValidationError(
            f"Result file was not found: {file_path}"
        ) from error

    except json.JSONDecodeError as error:
        raise ResultValidationError(
            f"{file_path}: invalid JSON: {error}"
        ) from error

    return validate_result_payload(
        payload=payload,
        source=str(file_path),
    )


def find_result_files(
    input_path: Path,
) -> list[Path]:
    """Find JSON files under a file or directory path."""

    if input_path.is_file():
        return [input_path]

    if not input_path.exists():
        raise ResultValidationError(
            f"Input path was not found: {input_path}"
        )

    files = sorted(input_path.rglob("*.json"))

    if not files:
        raise ResultValidationError(
            f"No JSON result files found under: {input_path}"
        )

    return files


def display_path(file_path: Path) -> str:
    """Return a readable path relative to the project when possible."""

    try:
        return str(file_path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(file_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one result JSON file or every JSON "
            "file under a results directory."
        )
    )

    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_RESULTS_DIRECTORY,
        help=(
            "Result JSON file or results directory. "
            "Defaults to the project's results directory."
        ),
    )

    args = parser.parse_args()

    try:
        result_files = find_result_files(
            args.input
        )

    except ResultValidationError as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error

    valid_count = 0
    invalid_count = 0

    for file_path in result_files:
        readable_path = display_path(file_path)

        try:
            validate_result_file(file_path)

            valid_count += 1
            print(f"[PASS] {readable_path}")

        except ResultValidationError as error:
            invalid_count += 1
            print(f"[FAIL] {readable_path}")
            print(f"       {error}")

    print()
    print("=== RESULT VALIDATION SUMMARY ===")
    print(f"Total files: {len(result_files)}")
    print(f"Valid files: {valid_count}")
    print(f"Invalid files: {invalid_count}")

    if invalid_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
