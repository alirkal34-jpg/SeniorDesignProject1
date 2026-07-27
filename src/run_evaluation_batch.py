"""Run the fixed evaluation subset through all four method runners.

The default fake mode is API-free. Live mode is intentionally limited to at
most three products unless the caller explicitly opts into a larger batch.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Callable

from keyword_loader import DEFAULT_KEYWORDS_FILE, load_keywords
from run_agentic_search import run_agentic_search, save_result as save_agentic
from run_selenium_nano_llm import (
    run_selenium_nano_llm,
    save_result as save_selenium_nano,
)
from run_selenium_rule_based import (
    run_selenium_rule_based,
    save_result as save_rule_based,
)
from run_tavily_llm import run_tavily_llm, save_result as save_tavily


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUBSET_FILE = (
    PROJECT_ROOT / "data" / "evaluation" / "evaluation_subset.csv"
)
METHODS = (
    "selenium_rule_based",
    "selenium_nano_llm",
    "tavily_llm",
    "agentic_search",
)


def load_evaluation_keywords(
    subset_file: Path = DEFAULT_SUBSET_FILE,
    keywords_file: Path = DEFAULT_KEYWORDS_FILE,
    limit: int | None = None,
) -> list[dict[str, str]]:
    with subset_file.open(encoding="utf-8-sig", newline="") as handle:
        subset_ids = [
            row["product_id"].strip()
            for row in csv.DictReader(handle)
            if row.get("product_id", "").strip()
        ]
    if limit is not None:
        subset_ids = subset_ids[:limit]

    keyword_records = load_keywords(keywords_file)
    keyword_by_id = {record.product_id: record.keyword for record in keyword_records}
    missing_ids = [
        product_id
        for product_id in subset_ids
        if product_id not in keyword_by_id
    ]
    if missing_ids:
        raise ValueError(
            f"Fixed keyword list is missing evaluation product IDs: {missing_ids}"
        )
    return [
        {"product_id": product_id, "keyword": keyword_by_id[product_id]}
        for product_id in subset_ids
    ]


def _run_method(
    method: str,
    product_id: str,
    keyword: str,
    execution_mode: str,
    max_results: int,
) -> tuple[dict[str, Any], Callable[[dict], Path]]:
    if method == "selenium_rule_based":
        return (
            run_selenium_rule_based(
                product_id,
                keyword,
                max_results=max_results,
                search_provider="fake" if execution_mode == "fake" else "selenium",
            ),
            save_rule_based,
        )
    if method == "selenium_nano_llm":
        return (
            run_selenium_nano_llm(
                product_id,
                keyword,
                max_results=max_results,
                provider="fake" if execution_mode == "fake" else "openrouter",
                search_provider="fake" if execution_mode == "fake" else "selenium",
            ),
            save_selenium_nano,
        )
    if method == "tavily_llm":
        return (
            run_tavily_llm(
                product_id,
                keyword,
                search_provider="fake" if execution_mode == "fake" else "tavily",
                evaluator_provider="fake" if execution_mode == "fake" else "openrouter",
                max_results=max_results,
            ),
            save_tavily,
        )
    if method == "agentic_search":
        return (
            run_agentic_search(
                product_id,
                keyword,
                planner_provider="fake" if execution_mode == "fake" else "openrouter",
                search_provider="fake" if execution_mode == "fake" else "tavily",
                evaluator_provider="fake" if execution_mode == "fake" else "openrouter",
                max_results=max_results,
            ),
            save_agentic,
        )
    raise ValueError(f"Unsupported evaluation method: {method}")


def run_evaluation_batch(
    subset_file: Path = DEFAULT_SUBSET_FILE,
    keywords_file: Path = DEFAULT_KEYWORDS_FILE,
    methods: tuple[str, ...] = METHODS,
    execution_mode: str = "fake",
    limit: int = 2,
    max_results: int = 5,
    save: bool = False,
    allow_live_batch: bool = False,
) -> dict[str, Any]:
    if execution_mode not in {"fake", "live"}:
        raise ValueError("execution_mode must be 'fake' or 'live'.")
    unknown_methods = set(methods) - set(METHODS)
    if unknown_methods:
        raise ValueError(f"Unsupported methods: {sorted(unknown_methods)}")
    if execution_mode == "live" and limit > 3 and not allow_live_batch:
        raise ValueError(
            "Live batches are limited to three products. "
            "Use explicit opt-in only after smoke tests succeed."
        )

    records = load_evaluation_keywords(
        subset_file=subset_file,
        keywords_file=keywords_file,
        limit=limit,
    )
    outputs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for record in records:
        for method in methods:
            try:
                output, saver = _run_method(
                    method=method,
                    product_id=record["product_id"],
                    keyword=record["keyword"],
                    execution_mode=execution_mode,
                    max_results=max_results,
                )
                output_path = str(saver(output)) if save else None
                outputs.append(
                    {
                        "product_id": record["product_id"],
                        "keyword": record["keyword"],
                        "method": method,
                        "output_path": output_path,
                        "payload": output,
                    }
                )
            except Exception as exc:
                errors.append(
                    {
                        "product_id": record["product_id"],
                        "keyword": record["keyword"],
                        "method": method,
                        "error": str(exc),
                    }
                )

    return {
        "execution_mode": execution_mode,
        "product_count": len(records),
        "method_count": len(methods),
        "successful_count": len(outputs),
        "failed_count": len(errors),
        "outputs": outputs,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run fixed evaluation products through identical method inputs."
    )
    parser.add_argument("--subset", type=Path, default=DEFAULT_SUBSET_FILE)
    parser.add_argument("--keywords", type=Path, default=DEFAULT_KEYWORDS_FILE)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--execution-mode", choices=["fake", "live"], default="fake")
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--allow-live-batch", action="store_true")
    args = parser.parse_args()

    summary = run_evaluation_batch(
        subset_file=args.subset,
        keywords_file=args.keywords,
        methods=tuple(args.methods),
        execution_mode=args.execution_mode,
        limit=args.limit,
        max_results=args.max_results,
        save=args.save,
        allow_live_batch=args.allow_live_batch,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["failed_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
