"""Calculate runtime, cost, relevance and accuracy metrics."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


try:
    from .ground_truth import (
        DEFAULT_GROUND_TRUTH_FILE,
        GroundTruthLookup,
        build_ground_truth_lookup,
        find_human_label,
        load_ground_truth,
    )
    from .result_validator import (
        DEFAULT_RESULTS_DIRECTORY,
        find_result_files,
        validate_result_file,
        validate_result_payload,
    )
except ImportError:
    from ground_truth import (
        DEFAULT_GROUND_TRUTH_FILE,
        GroundTruthLookup,
        build_ground_truth_lookup,
        find_human_label,
        load_ground_truth,
    )
    from result_validator import (
        DEFAULT_RESULTS_DIRECTORY,
        find_result_files,
        validate_result_file,
        validate_result_payload,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MetricsError(ValueError):
    """Raised when experiment metrics cannot be calculated."""


def calculate_method_metrics(
    payloads: list[dict[str, Any]],
    ground_truth_lookup: GroundTruthLookup | None = None,
) -> dict[str, dict[str, Any]]:
    """Group validated result payloads by method and calculate metrics."""

    if not payloads:
        raise MetricsError(
            "At least one result payload is required."
        )

    grouped_payloads: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for index, payload in enumerate(payloads):
        validated_payload = validate_result_payload(
            payload=payload,
            source=f"payload[{index}]",
        )
        grouped_payloads[
            validated_payload["method"]
        ].append(validated_payload)

    method_metrics: dict[str, dict[str, Any]] = {}

    for method in sorted(grouped_payloads):
        method_payloads = grouped_payloads[method]
        runtimes = [
            float(payload["runtime_seconds"])
            for payload in method_payloads
        ]
        costs = [
            float(payload["estimated_cost_usd"])
            for payload in method_payloads
        ]

        result_count = 0
        relevant_count = 0
        labeled_count = 0
        correct_count = 0
        true_positive_count = 0
        true_negative_count = 0
        false_positive_count = 0
        false_negative_count = 0

        for payload in method_payloads:
            for result in payload["results"]:
                result_count += 1

                if result["predicted_relevant"]:
                    relevant_count += 1

                if ground_truth_lookup is None:
                    continue
                # Get the human's decision for this exact (product, keyword,
                # domain, url) result. find_human_label tries a label
                # specific to this "method" first, then falls back to a
                # label shared across all four methods.
                human_label = find_human_label(
                    lookup=ground_truth_lookup,
                    product_id=payload["product_id"],
                    keyword=payload["keyword"],
                    method=payload["method"],
                    domain=result["domain"],
                    url=result["url"],
                )

                if human_label is None:
                    continue

                labeled_count += 1

                predicted_relevant = result[
                    "predicted_relevant"
                ]
                # THE CORE COMPARISON: If AI matches Human, it is a correct prediction.
                if predicted_relevant == human_label:
                    correct_count += 1

                # Build the Confusion Matrix

                # Both AI and Human said "Relevant"
                if predicted_relevant and human_label:
                    true_positive_count += 1

                # Both AI and Human said "Irrelevant"
                elif (
                    not predicted_relevant
                    and not human_label
                ):
                    true_negative_count += 1

                # AI said "Relevant", but Human said "Irrelevant" (False Alarm)
                elif predicted_relevant:
                    false_positive_count += 1

                # AI said "Irrelevant", but Human said "Relevant" (Missed)
                else:
                    false_negative_count += 1

        relevant_ratio = (
            relevant_count / result_count
            if result_count
            else 0.0
        )

        ground_truth_coverage_ratio = (
            round(labeled_count / result_count, 4)
            if result_count
            else 0.0
        )
        # Calculate the final Accuracy percentage for the AI method
        # Formula: (True Positives + True Negatives) / Total Labeled Results
        accuracy = (
            round(correct_count / labeled_count, 4)
            if labeled_count
            else None
        )

        method_metrics[method] = {
            "experiment_count": len(method_payloads),
            "result_count": result_count,
            "relevant_result_count": relevant_count,
            "relevant_result_ratio": round(
                relevant_ratio,
                4,
            ),
            "average_runtime_seconds": round(
                mean(runtimes),
                4,
            ),
            "total_estimated_cost_usd": round(
                sum(costs),
                8,
            ),
            "average_estimated_cost_usd": round(
                mean(costs),
                8,
            ),
            "labeled_result_count": labeled_count,
            "ground_truth_coverage_ratio": (
                ground_truth_coverage_ratio
            ),
            "correct_prediction_count": correct_count,
            "true_positive_count": true_positive_count,
            "true_negative_count": true_negative_count,
            "false_positive_count": false_positive_count,
            "false_negative_count": false_negative_count,
            "accuracy": accuracy,
        }

    return method_metrics


def build_metrics_report(
    input_path: Path = DEFAULT_RESULTS_DIRECTORY,
    ground_truth_path: Path | None = DEFAULT_GROUND_TRUTH_FILE,
) -> dict[str, Any]:
    """Load result files and build the full metrics report."""

    result_files = find_result_files(input_path)
    payloads: list[dict[str, Any]] = []
    invalid_result_files: list[dict[str, str]] = []
    for file_path in result_files:
        try:
            payloads.append(
                validate_result_file(file_path)
            )
        except (ValueError, OSError) as error:
            invalid_result_files.append(
                {
                    "path": str(file_path),
                    "error": str(error),
                }
            )

    if not payloads:
        raise MetricsError(
            "No valid result JSON files were found. "
            f"Invalid file count: {len(invalid_result_files)}."
        )

    ground_truth_lookup: GroundTruthLookup | None = None
    ground_truth_record_count = 0

    # Load the absolute Ground Truth (human labels) before the evaluation starts
    if ground_truth_path is not None:
        # Parse the CSV and convert text values to booleans
        records = load_ground_truth(
            ground_truth_path
        )
        ground_truth_record_count = len(records)
        ground_truth_lookup = (
            build_ground_truth_lookup(records)
        )

    method_metrics = calculate_method_metrics(
        payloads=payloads,
        ground_truth_lookup=ground_truth_lookup,
    )

    result_count = sum(
        metrics["result_count"]
        for metrics in method_metrics.values()
    )
    relevant_count = sum(
        metrics["relevant_result_count"]
        for metrics in method_metrics.values()
    )
    labeled_count = sum(
        metrics["labeled_result_count"]
        for metrics in method_metrics.values()
    )
    correct_count = sum(
        metrics["correct_prediction_count"]
        for metrics in method_metrics.values()
    )
    true_positive_count = sum(
        metrics["true_positive_count"]
        for metrics in method_metrics.values()
    )
    true_negative_count = sum(
        metrics["true_negative_count"]
        for metrics in method_metrics.values()
    )
    false_positive_count = sum(
        metrics["false_positive_count"]
        for metrics in method_metrics.values()
    )
    false_negative_count = sum(
        metrics["false_negative_count"]
        for metrics in method_metrics.values()
    )

    overall_accuracy = (
        round(correct_count / labeled_count, 4)
        if labeled_count
        else None
    )
    ground_truth_coverage_ratio = (
        round(labeled_count / result_count, 4)
        if result_count
        else 0.0
    )

    return {
        "result_file_count": len(result_files),
        "valid_result_file_count": len(payloads),
        "invalid_result_file_count": len(
            invalid_result_files
        ),
        "missing_or_invalid_result_file_count": len(
            invalid_result_files
        ),
        "invalid_result_files": invalid_result_files,
        "experiment_count": len(payloads),
        "method_count": len(method_metrics),
        "result_count": result_count,
        "relevant_result_count": relevant_count,
        "ground_truth_record_count": (
            ground_truth_record_count
        ),
        "labeled_result_count": labeled_count,
        "ground_truth_coverage_ratio": (
            ground_truth_coverage_ratio
        ),
        "correct_prediction_count": correct_count,
        "true_positive_count": true_positive_count,
        "true_negative_count": true_negative_count,
        "false_positive_count": false_positive_count,
        "false_negative_count": false_negative_count,
        "accuracy": overall_accuracy,
        "methods": method_metrics,
    }


def save_metrics_report(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    """Save a metrics report as UTF-8 JSON."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate runtime, cost, relevance and "
            "human-label accuracy metrics."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_RESULTS_DIRECTORY,
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=DEFAULT_GROUND_TRUTH_FILE,
    )
    parser.add_argument(
        "--without-ground-truth",
        action="store_true",
        help="Calculate metrics without loading human labels.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    args = parser.parse_args()

    ground_truth_path = (
        None
        if args.without_ground_truth
        else args.ground_truth
    )

    try:
        report = build_metrics_report(
            input_path=args.input,
            ground_truth_path=ground_truth_path,
        )
    except (ValueError, OSError) as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )

    if args.output is not None:
        save_metrics_report(
            report=report,
            output_path=args.output,
        )
        print()
        print(f"Metrics report saved: {args.output}")


if __name__ == "__main__":
    main()
