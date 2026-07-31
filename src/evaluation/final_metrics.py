"""Rebuild metrics for the frozen 10-product, four-method experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


try:
    from .ground_truth import build_ground_truth_lookup, load_ground_truth
    from .metrics import calculate_method_metrics, save_metrics_report
    from .result_validator import validate_result_file
except ImportError:
    from ground_truth import build_ground_truth_lookup, load_ground_truth
    from metrics import calculate_method_metrics, save_metrics_report
    from result_validator import validate_result_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "final_evaluation_manifest.json"
)
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "reports" / "final_evaluation_metrics.json"
)


def build_final_metrics_report(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    """Calculate metrics only from the result files frozen in the manifest."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected_result_files = manifest.get("selected_result_files", [])
    if not selected_result_files:
        raise ValueError("Final evaluation manifest has no result files.")

    payloads: list[dict[str, Any]] = []
    normalized_paths: list[str] = []
    for relative_path in selected_result_files:
        normalized_path = str(relative_path).replace("\\", "/")
        result_path = PROJECT_ROOT / normalized_path
        if not result_path.is_file():
            raise FileNotFoundError(
                f"Selected final result file does not exist: {normalized_path}"
            )
        payloads.append(validate_result_file(result_path))
        normalized_paths.append(normalized_path)

    ground_truth_relative = manifest["ground_truth_file"]
    ground_truth_path = PROJECT_ROOT / ground_truth_relative
    ground_truth_records = load_ground_truth(ground_truth_path)
    ground_truth_lookup = build_ground_truth_lookup(ground_truth_records)
    method_metrics = calculate_method_metrics(
        payloads=payloads,
        ground_truth_lookup=ground_truth_lookup,
    )

    totals = {
        key: sum(method[key] for method in method_metrics.values())
        for key in (
            "result_count",
            "labeled_result_count",
            "correct_prediction_count",
            "true_positive_count",
            "true_negative_count",
            "false_positive_count",
            "false_negative_count",
        )
    }
    if totals["result_count"] == 0:
        raise ValueError("The selected final evaluation contains no results.")

    labeled_count = totals["labeled_result_count"]
    accuracy = (
        round(totals["correct_prediction_count"] / labeled_count, 4)
        if labeled_count
        else None
    )
    coverage = round(labeled_count / totals["result_count"], 4)

    product_ids = {payload["product_id"] for payload in payloads}
    return {
        "report_scope": manifest["report_scope"],
        "evaluation_subset_file": manifest["evaluation_subset_file"],
        "ground_truth_file": ground_truth_relative,
        "ground_truth_record_count": len(ground_truth_records),
        "product_count": len(product_ids),
        "method_count": len(method_metrics),
        "experiment_count": len(payloads),
        "selected_result_files": normalized_paths,
        "result_count": totals["result_count"],
        "labeled_result_count": labeled_count,
        "ground_truth_coverage_ratio": coverage,
        "correct_prediction_count": totals["correct_prediction_count"],
        "accuracy": accuracy,
        "true_positive_count": totals["true_positive_count"],
        "true_negative_count": totals["true_negative_count"],
        "false_positive_count": totals["false_positive_count"],
        "false_negative_count": totals["false_negative_count"],
        "methods": method_metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recalculate the frozen final four-method evaluation."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    args = parser.parse_args()

    report = build_final_metrics_report(args.manifest)
    save_metrics_report(report, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print()
    print(f"Final metrics report saved: {args.output}")


if __name__ == "__main__":
    main()
