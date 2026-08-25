"""Freeze which result files a metrics report is allowed to read.

``final_metrics.py`` scores exactly the files a manifest names, so the manifest
is what makes a reported accuracy reproducible months later: rerunning the
pipeline writes new result files, but the report keeps pointing at the run it
was actually computed from.

The frozen ten-product phone manifest was written by hand. This module builds
the same structure from a results directory instead, picking the latest live
run per product and method, so a multi-category experiment can be frozen the
same way without retyping eighty paths.

A missing combination is an error rather than a smaller report. Dropping one
product from one method would quietly change what the four methods are being
compared on, which is precisely the comparison the experiment exists to make.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence


try:
    from .result_validator import find_result_files, validate_result_file
except ImportError:
    from result_validator import find_result_files, validate_result_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_DIRECTORY = PROJECT_ROOT / "results_multicategory"
DEFAULT_SUBSET_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "evaluation_subset_multicategory.csv"
)
DEFAULT_GROUND_TRUTH_PATH = (
    PROJECT_ROOT
    / "data"
    / "labels"
    / "multicategory_ground_truth.csv"
)
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "final_evaluation_manifest_multicategory.json"
)

DEFAULT_REPORT_SCOPE = (
    "latest live result per method for each product in the "
    "20-product multi-category evaluation subset"
)

# Result files are named
# <product>_<method>_<hash>_<mode>_<timestamp>_<hash>.json. The method itself
# contains underscores, so the timestamp is matched directly instead of being
# recovered by splitting the name apart.
TIMESTAMP_PATTERN = re.compile(r"_(\d{8}T\d{6,}Z)_")


class ManifestError(ValueError):
    """Raised when the result files cannot be frozen into a manifest."""


def result_sort_key(result_path: Path) -> tuple[str, float]:
    """Order runs of one product and method from oldest to newest."""

    match = TIMESTAMP_PATTERN.search(result_path.name)

    if match:
        return (match.group(1), 0.0)

    # An unstamped file still has to be orderable; fall back to the
    # filesystem so a hand-copied result does not crash the build.
    return ("", result_path.stat().st_mtime)


def relative_path(file_path: Path) -> str:
    """Render a path the way the manifest stores it."""

    try:
        return str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(file_path).replace("\\", "/")


def select_latest_result_files(
    results_directory: Path,
) -> dict[tuple[str, str], Path]:
    """Pick the newest live run for every product and method."""

    candidates: dict[tuple[str, str], list[Path]] = defaultdict(list)

    for result_path in find_result_files(results_directory):
        payload = validate_result_file(result_path)

        # Fake-mode test runs live in the same directories as real API/scrape
        # runs; this is the one line that keeps them out of any report.
        if payload["execution_mode"] != "live":
            continue

        key = (str(payload["product_id"]), str(payload["method"]))
        candidates[key].append(result_path)

    if not candidates:
        raise ManifestError(
            f"No live result files were found under: {results_directory}"
        )

    return {
        key: max(paths, key=result_sort_key)
        for key, paths in candidates.items()
    }


def read_subset_product_ids(subset_path: Path) -> list[str]:
    """Read the product ids the experiment was supposed to cover."""

    if not subset_path.exists():
        raise ManifestError(
            f"Evaluation subset file was not found: {subset_path}"
        )

    with subset_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)

        if not reader.fieldnames or "product_id" not in reader.fieldnames:
            raise ManifestError(
                f"Evaluation subset file has no product_id column: "
                f"{subset_path}"
            )

        product_ids = [
            str(row.get("product_id") or "").strip()
            for row in reader
        ]

    product_ids = [product_id for product_id in product_ids if product_id]

    if not product_ids:
        raise ManifestError(
            f"Evaluation subset file lists no products: {subset_path}"
        )

    return product_ids


def check_full_coverage(
    selected: dict[tuple[str, str], Path],
    product_ids: list[str],
) -> None:
    """Refuse a manifest with a hole in the product-by-method grid.

    This is why the multi-category manifest always has exactly
    20 products x 4 methods = 80 result files, never fewer: any single
    missing (product, method) pair raises here instead of quietly shrinking
    the comparison.
    """

    methods = sorted({method for _, method in selected})
    missing = [
        f"{product_id}/{method}"
        for product_id in product_ids
        for method in methods
        if (product_id, method) not in selected
    ]

    if missing:
        raise ManifestError(
            f"{len(missing)} product/method combination(s) have no live "
            "result, so the methods would not be compared on the same "
            "products:\n  " + "\n  ".join(missing)
        )

    unexpected = sorted(
        {
            product_id
            for product_id, _ in selected
            if product_id not in set(product_ids)
        }
    )

    if unexpected:
        raise ManifestError(
            "Result files exist for products outside the evaluation "
            f"subset: {unexpected}"
        )


def build_manifest(
    results_directory: Path = DEFAULT_RESULTS_DIRECTORY,
    subset_path: Path = DEFAULT_SUBSET_PATH,
    ground_truth_path: Path = DEFAULT_GROUND_TRUTH_PATH,
    report_scope: str = DEFAULT_REPORT_SCOPE,
    product_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build the manifest structure ``final_metrics.py`` consumes."""

    selected = select_latest_result_files(results_directory)
    expected_ids = read_subset_product_ids(subset_path)

    # A short run covers part of the subset on purpose. Narrowing what the
    # grid must contain keeps the hole check meaningful for that run instead
    # of turning it off, and the named products still have to be in the
    # subset, because only subset URLs carry human labels.
    if product_ids:
        outside = [wanted for wanted in product_ids if wanted not in set(expected_ids)]

        if outside:
            raise ManifestError(
                "These product IDs are not in the evaluation subset: "
                + ", ".join(outside)
            )

        expected_ids = list(product_ids)
        selected = {
            key: path
            for key, path in selected.items()
            if key[0] in set(expected_ids)
        }

    check_full_coverage(selected, expected_ids)

    return {
        "report_scope": report_scope,
        "evaluation_subset_file": relative_path(subset_path),
        "ground_truth_file": relative_path(ground_truth_path),
        "selected_result_files": sorted(
            relative_path(path) for path in selected.values()
        ),
    }


def write_manifest(manifest: dict[str, Any], output_path: Path) -> Path:
    """Write the manifest as formatted JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Freeze the latest live result per product and method into a "
            "metrics manifest."
        )
    )
    parser.add_argument(
        "--results-directory",
        type=Path,
        default=DEFAULT_RESULTS_DIRECTORY,
    )
    parser.add_argument(
        "--evaluation-subset",
        type=Path,
        default=DEFAULT_SUBSET_PATH,
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=DEFAULT_GROUND_TRUTH_PATH,
    )
    parser.add_argument(
        "--report-scope",
        default=DEFAULT_REPORT_SCOPE,
    )
    parser.add_argument(
        "--ids",
        default="",
        help=(
            "Comma-separated product IDs the grid must contain, instead of "
            "the whole evaluation subset. Use it for a short run."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    args = parser.parse_args()

    try:
        manifest = build_manifest(
            results_directory=args.results_directory,
            subset_path=args.evaluation_subset,
            ground_truth_path=args.ground_truth,
            report_scope=args.report_scope,
            product_ids=[
                value.strip() for value in args.ids.split(",") if value.strip()
            ],
        )
    except ManifestError as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error

    output_path = write_manifest(manifest, args.output)
    selected_files = manifest["selected_result_files"]
    methods = sorted(
        {
            Path(path).parent.name
            for path in selected_files
        }
    )

    print("=== MANIFEST BUILT ===")
    print(f"Result files:   {len(selected_files)}")
    print(f"Methods:        {len(methods)} ({', '.join(methods)})")
    print(f"Ground truth:   {manifest['ground_truth_file']}")
    print(f"Manifest:       {output_path}")


if __name__ == "__main__":
    main()
