"""Run the fixed evaluation subset through all four method runners.

The default fake mode is API-free. Live mode is intentionally limited to at
most three products unless the caller explicitly opts into a larger batch.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Sequence

from result_storage import create_unique_result_path

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
    product_ids: Sequence[str] | None = None,
) -> list[dict[str, str]]:
    with subset_file.open(encoding="utf-8-sig", newline="") as handle:
        subset_ids = [
            row["product_id"].strip()
            for row in csv.DictReader(handle)
            if row.get("product_id", "").strip()
        ]

    # A limit always takes the head of the subset, and the head of this subset
    # is two phones. Naming the products is how a short run can cover several
    # categories. An ID outside the subset is refused: the labeled URLs only
    # cover the subset, so a run on any other product could not be scored.
    if product_ids:
        outside = [wanted for wanted in product_ids if wanted not in set(subset_ids)]

        if outside:
            raise ValueError(
                "These product IDs are not in the evaluation subset: "
                + ", ".join(outside)
            )

        subset_ids = list(product_ids)
    elif limit is not None:
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
                search_provider="fake" if execution_mode == "fake" else "selenium",
                evaluator_provider="fake" if execution_mode == "fake" else "openrouter",
                max_results=max_results,
            ),
            save_agentic,
        )
    raise ValueError(f"Unsupported evaluation method: {method}")


def save_to_directory(
    output: dict[str, Any],
    results_root: Path,
) -> Path:
    """Save one payload beneath a caller-chosen results root.

    The per-method ``save_result`` helpers always write into ``results/``,
    which holds the frozen smartphone baseline. New experiments - the
    multi-category runs in particular - must be kept out of that directory so
    the committed evaluation stays reproducible.
    """

    method = str(output["method"])
    method_directory = results_root / method
    method_directory.mkdir(parents=True, exist_ok=True)
    keyword_digest = hashlib.sha256(
        str(output["keyword"]).encode("utf-8")
    ).hexdigest()[:8]
    output_path = create_unique_result_path(
        directory=method_directory,
        product_id=str(output["product_id"]),
        method=method,
        keyword_digest=keyword_digest,
        execution_mode=str(output.get("execution_mode", "unknown")),
    )
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def find_completed_runs(results_directory: Path | None) -> set[tuple[str, str]]:
    """Return the (product_id, method) pairs that already have a result file.

    Provider free tiers cap how many model requests a day allows, so a batch
    can stop half way through. Knowing what is already on disk lets the next
    session spend its quota only on what is missing.
    """

    completed: set[tuple[str, str]] = set()

    if results_directory is None or not results_directory.is_dir():
        return completed

    for method in METHODS:
        method_directory = results_directory / method

        if not method_directory.is_dir():
            continue

        for path in method_directory.glob("*.json"):
            product_id = path.name.split("_", 1)[0]

            if product_id:
                completed.add((product_id, method))

    return completed


def run_evaluation_batch(
    subset_file: Path = DEFAULT_SUBSET_FILE,
    keywords_file: Path = DEFAULT_KEYWORDS_FILE,
    methods: tuple[str, ...] = METHODS,
    execution_mode: str = "fake",
    limit: int = 2,
    max_results: int = 5,
    save: bool = False,
    allow_live_batch: bool = False,
    results_directory: Path | None = None,
    skip_existing: bool = False,
    product_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    if execution_mode not in {"fake", "live"}:
        raise ValueError("execution_mode must be 'fake' or 'live'.")
    unknown_methods = set(methods) - set(METHODS)
    if unknown_methods:
        raise ValueError(f"Unsupported methods: {sorted(unknown_methods)}")
    # Naming products must not become a way around the live-batch cap, so the
    # guard counts whatever the run will actually cover.
    requested_count = len(product_ids) if product_ids else limit
    if execution_mode == "live" and requested_count > 3 and not allow_live_batch:
        raise ValueError(
            "Live batches are limited to three products. "
            "Use explicit opt-in only after smoke tests succeed."
        )

    records = load_evaluation_keywords(
        subset_file=subset_file,
        keywords_file=keywords_file,
        limit=limit,
        product_ids=product_ids,
    )
    outputs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    completed = (
        find_completed_runs(results_directory) if skip_existing else set()
    )
    skipped: list[dict[str, str]] = []

    for record in records:
        for method in methods:
            if (record["product_id"], method) in completed:
                skipped.append(
                    {
                        "product_id": record["product_id"],
                        "method": method,
                    }
                )
                continue

            try:
                output, saver = _run_method(
                    method=method,
                    product_id=record["product_id"],
                    keyword=record["keyword"],
                    execution_mode=execution_mode,
                    max_results=max_results,
                )
                if not save:
                    output_path = None
                elif results_directory is not None:
                    output_path = str(
                        save_to_directory(output, results_directory)
                    )
                else:
                    output_path = str(saver(output))
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
        "skipped_count": len(skipped),
        "skipped": skipped,
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
    parser.add_argument(
        "--ids",
        default="",
        help=(
            "Comma-separated product IDs from the subset to run, in this "
            "order, instead of the first --limit products."
        ),
    )
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--allow-live-batch", action="store_true")
    parser.add_argument(
        "--results-directory",
        type=Path,
        default=None,
        help=(
            "Save results beneath this directory instead of results/. Use it "
            "for every new experiment so the frozen smartphone baseline in "
            "results/ stays untouched."
        ),
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help=(
            "Skip product/method pairs that already have a result file in "
            "--results-directory. Use it to continue a batch that stopped on "
            "a provider daily limit without spending quota on finished work."
        ),
    )
    args = parser.parse_args()

    if args.skip_existing and args.results_directory is None:
        parser.error("--skip-existing requires --results-directory.")

    try:
        summary = run_evaluation_batch(
            subset_file=args.subset,
            keywords_file=args.keywords,
            methods=tuple(args.methods),
            execution_mode=args.execution_mode,
            limit=args.limit,
            max_results=args.max_results,
            save=args.save,
            allow_live_batch=args.allow_live_batch,
            results_directory=args.results_directory,
            skip_existing=args.skip_existing,
            product_ids=[
                value.strip() for value in args.ids.split(",") if value.strip()
            ],
        )
    except ValueError as error:
        # A mistyped --ids is an ordinary operator error, not a crash worth a
        # traceback in front of an audience.
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["failed_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
