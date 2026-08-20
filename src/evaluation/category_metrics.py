"""Score the four methods per category, and against a trivial baseline.

The advisor's question is whether the pipeline generalizes beyond phones, and a
single overall accuracy cannot answer it: one easy category can carry a method
that fails everywhere else. This module therefore reports every method broken
down by category group.

It also reports what a method that answers "relevant" to everything would
score. On a result set where most URLs really are relevant, that trivial
classifier already scores well, so accuracy alone can make a method look
skilled when it has simply stopped saying no. Precision, recall and balanced
accuracy are reported next to it to keep that distinction visible.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


try:
    from .ground_truth import (
        build_ground_truth_lookup,
        find_human_label,
        load_ground_truth,
    )
    from .result_validator import validate_result_file
except ImportError:
    from ground_truth import (
        build_ground_truth_lookup,
        find_human_label,
        load_ground_truth,
    )
    from result_validator import validate_result_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "final_evaluation_manifest_multicategory.json"
)
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "reports_multicategory"
    / "multicategory_category_metrics.json"
)
DEFAULT_MARKDOWN_PATH = (
    PROJECT_ROOT
    / "reports_multicategory"
    / "multicategory_category_metrics.md"
)

UNKNOWN_CATEGORY = "unknown"


class CategoryMetricsError(ValueError):
    """Raised when the per-category report cannot be built."""


def relative_to_project(file_path: Path) -> str:
    """Render a path the way the report stores it, however it was given."""

    resolved = Path(file_path).resolve()

    try:
        return str(resolved.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        # A manifest kept outside the project still deserves a readable name.
        return str(resolved).replace("\\", "/")


def load_category_by_product(subset_path: Path) -> dict[str, str]:
    """Map every evaluated product to the category group it belongs to."""

    if not subset_path.exists():
        raise CategoryMetricsError(
            f"Evaluation subset file was not found: {subset_path}"
        )

    with subset_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        field_names = reader.fieldnames or []

        for column in ("product_id", "category_group"):
            if column not in field_names:
                raise CategoryMetricsError(
                    f"Evaluation subset file has no {column} column: "
                    f"{subset_path}"
                )

        return {
            str(row["product_id"]).strip(): str(
                row["category_group"] or ""
            ).strip()
            for row in reader
            if str(row.get("product_id") or "").strip()
        }


def score_predictions(
    predictions: list[tuple[bool, bool]],
) -> dict[str, Any]:
    """Turn (predicted, human) pairs into the numbers the report shows."""

    true_positive = sum(
        1 for predicted, actual in predictions if predicted and actual
    )
    true_negative = sum(
        1
        for predicted, actual in predictions
        if not predicted and not actual
    )
    false_positive = sum(
        1 for predicted, actual in predictions if predicted and not actual
    )
    false_negative = sum(
        1 for predicted, actual in predictions if not predicted and actual
    )
    labeled = len(predictions)

    if labeled == 0:
        raise CategoryMetricsError(
            "Cannot score an empty set of predictions."
        )

    correct = true_positive + true_negative
    relevant_labels = true_positive + false_negative
    irrelevant_labels = true_negative + false_positive

    def ratio(numerator: int, denominator: int) -> float | None:
        if denominator == 0:
            return None
        return round(numerator / denominator, 4)

    recall = ratio(true_positive, relevant_labels)
    specificity = ratio(true_negative, irrelevant_labels)
    precision = ratio(true_positive, true_positive + false_positive)

    f1_score = None
    if precision is not None and recall is not None and precision + recall:
        f1_score = round(
            2 * precision * recall / (precision + recall),
            4,
        )

    balanced_accuracy = None
    if recall is not None and specificity is not None:
        balanced_accuracy = round((recall + specificity) / 2, 4)

    return {
        "labeled_result_count": labeled,
        "correct_prediction_count": correct,
        "accuracy": round(correct / labeled, 4),
        "true_positive_count": true_positive,
        "true_negative_count": true_negative,
        "false_positive_count": false_positive,
        "false_negative_count": false_negative,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1_score": f1_score,
        "balanced_accuracy": balanced_accuracy,
        "predicted_relevant_ratio": round(
            (true_positive + false_positive) / labeled,
            4,
        ),
        # What a method scores by answering "relevant" to everything. A
        # method that does not beat this has not learned to say no.
        "always_relevant_accuracy": round(relevant_labels / labeled, 4),
    }


def collect_predictions(
    manifest_path: Path,
    category_by_product: dict[str, str],
) -> tuple[
    dict[tuple[str, str], list[tuple[bool, bool]]],
    dict[str, int],
    list[str],
]:
    """Pair every labeled result with its human label, per method and group."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result_files = manifest.get("selected_result_files", [])

    if not result_files:
        raise CategoryMetricsError(
            f"Manifest names no result files: {manifest_path}"
        )

    ground_truth_path = PROJECT_ROOT / manifest["ground_truth_file"]
    lookup = build_ground_truth_lookup(load_ground_truth(ground_truth_path))

    predictions: dict[
        tuple[str, str],
        list[tuple[bool, bool]],
    ] = defaultdict(list)
    unlabeled_by_method: dict[str, int] = defaultdict(int)
    methods_seen: set[str] = set()

    for relative_path in result_files:
        result_path = PROJECT_ROOT / str(relative_path).replace("\\", "/")
        payload = validate_result_file(result_path)
        method = str(payload["method"])
        methods_seen.add(method)
        product_id = str(payload["product_id"])
        category_group = category_by_product.get(
            product_id,
            UNKNOWN_CATEGORY,
        )

        for result in payload["results"]:
            human_label = find_human_label(
                lookup=lookup,
                product_id=product_id,
                keyword=payload["keyword"],
                method=method,
                domain=result["domain"],
                url=result["url"],
            )

            if human_label is None:
                unlabeled_by_method[method] += 1
                continue

            predictions[(method, category_group)].append(
                (bool(result["predicted_relevant"]), human_label)
            )

    if not predictions:
        raise CategoryMetricsError(
            "No result matched a human label, so nothing can be scored."
        )

    return predictions, dict(unlabeled_by_method), sorted(methods_seen)


def build_category_report(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    """Build the per-method, per-category report."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    subset_path = PROJECT_ROOT / manifest["evaluation_subset_file"]
    category_by_product = load_category_by_product(subset_path)
    predictions, unlabeled_by_method, methods = collect_predictions(
        manifest_path,
        category_by_product,
    )

    category_groups = sorted({group for _, group in predictions})

    by_method: dict[str, Any] = {}
    for method in methods:
        pooled = [
            pair
            for (pair_method, _), pairs in predictions.items()
            if pair_method == method
            for pair in pairs
        ]
        by_method[method] = {
            # A method whose results carry no labels still belongs in the
            # comparison; dropping it would quietly turn a four-method
            # experiment into a three-method one.
            "overall": score_predictions(pooled) if pooled else None,
            "unlabeled_result_count": unlabeled_by_method.get(method, 0),
            "categories": {
                group: score_predictions(predictions[(method, group)])
                for group in category_groups
                if (method, group) in predictions
            },
        }

    by_category: dict[str, Any] = {}
    for group in category_groups:
        pooled = [
            pair
            for (_, pair_group), pairs in predictions.items()
            if pair_group == group
            for pair in pairs
        ]
        by_category[group] = {
            "overall": score_predictions(pooled),
            "methods": {
                method: score_predictions(predictions[(method, group)])
                for method in methods
                if (method, group) in predictions
            },
        }

    return {
        # The path may arrive relative, from a shell run inside the project,
        # or absolute from the default. Resolve it before making it relative
        # so a plain `--manifest data/...` does not crash the report.
        "manifest_file": relative_to_project(manifest_path),
        "evaluation_subset_file": manifest["evaluation_subset_file"],
        "ground_truth_file": manifest["ground_truth_file"],
        "product_count": len(category_by_product),
        "category_group_count": len(category_groups),
        "method_count": len(methods),
        "methods": by_method,
        "category_groups": by_category,
    }


def format_value(value: Any) -> str:
    """Render a metric for a Markdown cell."""

    if value is None:
        return "–"

    if isinstance(value, float):
        return f"{value:.3f}"

    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    """Render the report as the tables that go into the written report."""

    lines: list[str] = []
    lines.append("# Multi-category evaluation, per method and category")
    lines.append("")
    lines.append(
        f"Ground truth: `{report['ground_truth_file']}` · "
        f"{report['product_count']} products · "
        f"{report['category_group_count']} category groups · "
        f"{report['method_count']} methods"
    )
    lines.append("")
    lines.append("## Overall, per method")
    lines.append("")
    lines.append(
        "| method | labeled | accuracy | always-relevant | balanced acc. "
        "| precision | recall | specificity | F1 | said relevant |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: "
        "| ---: |"
    )

    def rank_key(item: tuple[str, dict[str, Any]]) -> float:
        overall = item[1]["overall"]
        # An unscorable method sorts last but is still shown.
        return overall["accuracy"] if overall else -1.0

    ranked_methods = sorted(
        report["methods"].items(),
        key=rank_key,
        reverse=True,
    )

    for method, payload in ranked_methods:
        overall = payload["overall"]

        if overall is None:
            lines.append(
                f"| {method} | 0 | – | – | – | – | – | – | – | – |"
            )
            continue

        lines.append(
            f"| {method} "
            f"| {overall['labeled_result_count']} "
            f"| {format_value(overall['accuracy'])} "
            f"| {format_value(overall['always_relevant_accuracy'])} "
            f"| {format_value(overall['balanced_accuracy'])} "
            f"| {format_value(overall['precision'])} "
            f"| {format_value(overall['recall'])} "
            f"| {format_value(overall['specificity'])} "
            f"| {format_value(overall['f1_score'])} "
            f"| {format_value(overall['predicted_relevant_ratio'])} |"
        )

    lines.append("")
    lines.append("## Accuracy per category group")
    lines.append("")

    method_names = [method for method, _ in ranked_methods]
    header = "| category group | labeled | " + " | ".join(method_names) + " |"
    separator = "| --- | ---: | " + " | ".join(["---:"] * len(method_names))
    separator += " |"
    lines.append(header)
    lines.append(separator)

    for group, payload in sorted(report["category_groups"].items()):
        cells = []
        for method in method_names:
            scores = payload["methods"].get(method)
            cells.append(
                format_value(scores["accuracy"]) if scores else "–"
            )
        labeled = payload["overall"]["labeled_result_count"]
        lines.append(f"| {group} | {labeled} | " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("## Share of labeled URLs that are relevant, per category")
    lines.append("")
    lines.append("| category group | labeled | relevant share |")
    lines.append("| --- | ---: | ---: |")

    for group, payload in sorted(report["category_groups"].items()):
        overall = payload["overall"]
        lines.append(
            f"| {group} | {overall['labeled_result_count']} "
            f"| {format_value(overall['always_relevant_accuracy'])} |"
        )

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Score every method per category group against human labels."
        )
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
    parser.add_argument(
        "--markdown",
        type=Path,
        default=DEFAULT_MARKDOWN_PATH,
    )
    args = parser.parse_args()

    try:
        report = build_category_report(args.manifest)
    except CategoryMetricsError as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    markdown = render_markdown(report)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown, encoding="utf-8")

    print(markdown)
    print(f"Category metrics saved: {args.output}")
    print(f"Markdown tables saved:  {args.markdown}")


if __name__ == "__main__":
    main()
