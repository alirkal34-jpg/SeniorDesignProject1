"""Run Selenium + Rule-Based evaluation for generated keywords in small batches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from keyword_loader import DEFAULT_KEYWORDS_FILE, KeywordRecord, load_keywords
from run_selenium_rule_based import run_selenium_rule_based, save_result


DEFAULT_BATCH_LIMIT = 3
DEFAULT_MAX_RESULTS = 5


def run_rule_based_batch(
    keywords_file: Path = DEFAULT_KEYWORDS_FILE,
    limit: int = DEFAULT_BATCH_LIMIT,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> dict[str, Any]:
    keyword_records = load_keywords(keywords_file, limit=limit)

    summary: dict[str, Any] = {
        "requested_count": len(keyword_records),
        "successful_count": 0,
        "failed_count": 0,
        "outputs": [],
        "errors": [],
    }

    for record in keyword_records:
        try:
            output = run_selenium_rule_based(
                product_id=record.product_id,
                keyword=record.keyword,
                max_results=max_results,
            )
            output_file_path = save_result(output)
            summary["successful_count"] += 1
            summary["outputs"].append(
                {
                    "product_id": record.product_id,
                    "keyword": record.keyword,
                    "path": str(output_file_path),
                }
            )

        except Exception as exc:
            summary["failed_count"] += 1
            summary["errors"].append(
                {
                    "product_id": record.product_id,
                    "keyword": record.keyword,
                    "error": str(exc),
                }
            )

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Selenium + Rule-Based for 2-3 generated keywords.")
    parser.add_argument("--keywords", type=Path, default=DEFAULT_KEYWORDS_FILE)
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_LIMIT)
    parser.add_argument("--max-results", type=int, default=DEFAULT_MAX_RESULTS)
    args = parser.parse_args()

    if args.limit > 3:
        raise ValueError("Use --limit 3 or lower for the initial Google/CAPTCHA-safe batch test.")

    summary = run_rule_based_batch(
        keywords_file=args.keywords,
        limit=args.limit,
        max_results=args.max_results,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
