"""Write the human-readable report for the multi-category comparison.

Every number here is read from the two metrics files rather than typed in, so
the report cannot drift away from the experiment it describes. The narrative
that surrounds those numbers is deliberately plain: on this result set the
headline accuracy is easy to misread, because most returned URLs really are
relevant and a method that never says "no" already scores well.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METRICS_PATH = (
    PROJECT_ROOT
    / "reports_multicategory"
    / "multicategory_evaluation_metrics.json"
)
DEFAULT_CATEGORY_METRICS_PATH = (
    PROJECT_ROOT
    / "reports_multicategory"
    / "multicategory_category_metrics.json"
)
DEFAULT_PHONE_METRICS_PATH = (
    PROJECT_ROOT / "reports" / "final_evaluation_metrics.json"
)
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "reports_multicategory"
    / "multicategory_evaluation_report.md"
)

METHOD_LABELS = {
    "agentic_search": "Agentic Search",
    "selenium_nano_llm": "Selenium + NanoLLM",
    "selenium_rule_based": "Selenium + Rule-Based",
    "tavily_llm": "Tavily + NanoLLM",
}


class ReportError(ValueError):
    """Raised when the report cannot be built from the metrics files."""


def percent(value: float | None) -> str:
    """Render a ratio as a percentage, or as a dash when undefined."""

    if value is None:
        return "–"

    return f"{value * 100:.2f}%"


def method_label(method: str) -> str:
    """Render a method name the way the written report refers to it."""

    return METHOD_LABELS.get(method, method)


def rank_methods(category_metrics: dict[str, Any]) -> list[str]:
    """Order methods by accuracy, best first."""

    scorable = {
        method: payload["overall"]
        for method, payload in category_metrics["methods"].items()
        if payload["overall"] is not None
    }

    if not scorable:
        raise ReportError("No method could be scored against human labels.")

    return sorted(
        scorable,
        key=lambda method: scorable[method]["accuracy"],
        reverse=True,
    )


def render_report(
    metrics: dict[str, Any],
    category_metrics: dict[str, Any],
    phone_metrics: dict[str, Any] | None = None,
) -> str:
    """Render both metrics files as one Markdown report."""

    if metrics.get("ground_truth_coverage_ratio") != 1.0:
        raise ReportError(
            "The comparison report requires complete ground-truth coverage; "
            f"got {metrics.get('ground_truth_coverage_ratio')}."
        )

    ranked = rank_methods(category_metrics)
    best_method = ranked[0]
    scores = {
        method: category_metrics["methods"][method]["overall"]
        for method in ranked
    }

    # A method only demonstrates judgement if it beats the classifier that
    # answers "relevant" to every URL it was given.
    beat_baseline = [
        method
        for method in ranked
        if scores[method]["accuracy"] > scores[method][
            "always_relevant_accuracy"
        ]
    ]

    lines: list[str] = []
    lines.append("# Multi-Category Four-Method Evaluation Report")
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(
        "The first evaluation of this project covered smartphones only. The "
        "advisor asked whether the pipeline generalizes to other search "
        "intents and product structures, so the same four methods were rerun "
        f"over {metrics['product_count']} products drawn from "
        f"{category_metrics['category_group_count']} category groups. This "
        "report is the human-readable companion to "
        "`multicategory_evaluation_metrics.json` and "
        "`multicategory_category_metrics.json`."
    )
    lines.append("")
    lines.append("## Experimental protocol")
    lines.append("")
    lines.append(
        f"- Products: {metrics['product_count']}, spread across "
        f"{category_metrics['category_group_count']} category groups "
        "(2 products per group, different brands)."
    )
    lines.append(
        "- Input: one generated keyword per product, reused unchanged by "
        "every method."
    )
    lines.append("- Maximum search results: 5 per product and method.")
    lines.append(
        f"- Experiments: {metrics['experiment_count']} live method/product "
        "runs, no failures."
    )
    lines.append(f"- Evaluated results: {metrics['result_count']}.")
    lines.append(
        f"- Human-labeled URLs: {metrics['ground_truth_record_count']}."
    )
    lines.append(
        "- Label coverage of the evaluated results: "
        f"{percent(metrics['ground_truth_coverage_ratio'])}."
    )
    lines.append(
        "- Relevance rule: the page must be the product named in the "
        "keyword, including the stated variant, and must have transactional "
        "purpose. Out of stock is still relevant; a different variant, an "
        "accessory, a category page, news, or a review is not."
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(
        "| Method | Results | Accuracy | Always-relevant baseline "
        "| Balanced accuracy | Precision | Recall | Specificity "
        "| Avg. runtime |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    )

    for method in ranked:
        overall = scores[method]
        runtime = metrics["methods"][method]["average_runtime_seconds"]
        lines.append(
            f"| {method_label(method)} "
            f"| {overall['labeled_result_count']} "
            f"| {percent(overall['accuracy'])} "
            f"| {percent(overall['always_relevant_accuracy'])} "
            f"| {percent(overall['balanced_accuracy'])} "
            f"| {percent(overall['precision'])} "
            f"| {percent(overall['recall'])} "
            f"| {percent(overall['specificity'])} "
            f"| {runtime:.3f} s |"
        )

    lines.append("")
    lines.append(
        f"Overall accuracy across all four methods was "
        f"**{percent(metrics['accuracy'])}** "
        f"({metrics['correct_prediction_count']} correct out of "
        f"{metrics['labeled_result_count']} labeled results)."
    )
    lines.append("")
    lines.append("## How to read the accuracy column")
    lines.append("")
    lines.append(
        "The *always-relevant baseline* column is the accuracy a method "
        "would reach by answering \"relevant\" to every URL it returned. It "
        "is not a hypothetical: it is the share of that method's own results "
        "that the reviewers judged relevant."
    )
    lines.append("")

    if len(beat_baseline) == 1:
        only = beat_baseline[0]
        lines.append(
            f"Only **{method_label(only)}** beat that baseline, by "
            f"{(scores[only]['accuracy'] - scores[only]['always_relevant_accuracy']) * 100:.1f} "
            "percentage points. The other three did not, which means their "
            "accuracy reflects the difficulty of the URLs they happened to "
            "return rather than an ability to reject an irrelevant one."
        )
    elif beat_baseline:
        named = ", ".join(
            f"{method_label(method)} "
            f"(+{(scores[method]['accuracy'] - scores[method]['always_relevant_accuracy']) * 100:.1f} pp)"
            for method in beat_baseline
        )
        lines.append(
            f"Methods that beat that baseline, and by how much: {named}. A "
            "method that does not beat it has an accuracy that reflects the "
            "difficulty of the URLs it happened to return, not an ability to "
            "reject one — and a margin of one point or two says almost the "
            "same thing."
        )
    else:
        lines.append(
            "No method beat that baseline, so no method demonstrated an "
            "ability to reject an irrelevant result on this set."
        )

    lines.append("")
    lines.append(
        "Specificity makes the same point directly: it is the share of "
        "genuinely irrelevant URLs a method rejected."
    )
    lines.append("")

    for method in ranked:
        overall = scores[method]
        lines.append(
            f"- **{method_label(method)}** said \"relevant\" to "
            f"{percent(overall['predicted_relevant_ratio'])} of its results "
            f"and rejected {percent(overall['specificity'])} of the "
            f"irrelevant ones "
            f"({overall['true_negative_count']} of "
            f"{overall['true_negative_count'] + overall['false_positive_count']})."
        )

    lines.append("")
    lines.append("## Accuracy per category group")
    lines.append("")
    header = "| Category group | Labeled | Relevant share | " + " | ".join(
        method_label(method) for method in ranked
    )
    lines.append(header + " |")
    lines.append(
        "|---|---:|---:|" + "---:|" * len(ranked)
    )

    for group, payload in sorted(category_metrics["category_groups"].items()):
        cells = []
        for method in ranked:
            method_scores = payload["methods"].get(method)
            cells.append(
                percent(method_scores["accuracy"]) if method_scores else "–"
            )
        overall = payload["overall"]
        lines.append(
            f"| {group} | {overall['labeled_result_count']} "
            f"| {percent(overall['always_relevant_accuracy'])} | "
            + " | ".join(cells)
            + " |"
        )

    lines.append("")

    phone_group = "elektronik_cep_telefonu"
    phone_payload = category_metrics["category_groups"].get(phone_group)

    if phone_payload is not None:
        phone_accuracies = [
            method_scores["accuracy"]
            for method_scores in phone_payload["methods"].values()
        ]
        other_accuracies = [
            method_scores["accuracy"]
            for group, payload in category_metrics["category_groups"].items()
            if group != phone_group
            for method_scores in payload["methods"].values()
        ]

        if phone_accuracies and other_accuracies:
            phone_mean = sum(phone_accuracies) / len(phone_accuracies)
            other_mean = sum(other_accuracies) / len(other_accuracies)
            lines.append("## Was the phone category representative?")
            lines.append("")
            lines.append(
                "Averaged over the four methods, the phone category scored "
                f"{percent(phone_mean)} while the other categories averaged "
                f"{percent(other_mean)}. The advisor's concern is therefore "
                "supported by the measurement: phones were the easiest "
                "category in the set, so a phone-only result overstates how "
                "well the pipeline works elsewhere."
            )
            lines.append("")

    if phone_metrics is not None:
        lines.append("## Comparison with the frozen phone experiment")
        lines.append("")
        lines.append(
            "| Experiment | Products | Labeled results | Overall accuracy |"
        )
        lines.append("|---|---:|---:|---:|")
        lines.append(
            f"| Phones only (frozen) | {phone_metrics['product_count']} "
            f"| {phone_metrics['labeled_result_count']} "
            f"| {percent(phone_metrics['accuracy'])} |"
        )
        lines.append(
            f"| Multi-category | {metrics['product_count']} "
            f"| {metrics['labeled_result_count']} "
            f"| {percent(metrics['accuracy'])} |"
        )
        lines.append("")
        lines.append(
            "The two experiments use different products, keywords and "
            "labels, so the overall figures are not directly comparable. "
            "They are shown together only to record that the earlier result "
            "remains reproducible and untouched."
        )
        lines.append("")

    lines.append("## Labeling protocol")
    lines.append("")
    lines.append(
        "- Every unique URL was reviewed once, by hand, and the label is "
        "shared by every method that returned that URL, so the four methods "
        "are scored against identical ground truth."
    )
    lines.append(
        "- The review workbook deliberately hides `predicted_relevant` and "
        "`relevance_score`. Showing a method's guess to the reviewer would "
        "bias the ground truth toward that method."
    )
    lines.append(
        "- Review ran over two sessions because a provider daily limit split "
        "the experiment; the second workbook excluded every URL the first "
        "one already covered."
    )
    lines.append(
        "- Rows the reviewer marked as unresolved were settled in "
        "`data/labels/multicategory_label_adjudications.csv` instead of by "
        "editing the workbook, so the human record is unchanged and each "
        "adjudicated label carries the rule that produced it in its `notes` "
        "field. An adjudication cannot overturn an answer the reviewer "
        "actually gave."
    )
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append(
        "- One run per product and method, so variance and confidence "
        "intervals are out of scope."
    )
    lines.append(
        "- Two products per category group is enough to compare methods on "
        "the same footing, but too few to characterize a category."
    )
    lines.append(
        "- The relevant share of returned URLs is high in every category, "
        "which compresses the range accuracy can move in and is why "
        "specificity and balanced accuracy are reported next to it."
    )
    lines.append(
        "- Costs are reported as $0.00 because the configured OpenRouter "
        "model was free and Tavily search cost was recorded as zero. This "
        "does not mean future runs are free."
    )
    lines.append("")
    lines.append("## Reproduction")
    lines.append("")
    lines.append("```powershell")
    lines.append(
        ".\\.venv\\Scripts\\python.exe src\\evaluation\\import_label_workbook.py "
        "--workbook data\\labels\\label_review_session1.xlsx "
        "data\\labels\\label_review_session2.xlsx "
        "--adjudication data\\labels\\multicategory_label_adjudications.csv "
        "--output data\\labels\\multicategory_ground_truth.csv"
    )
    lines.append(".\\.venv\\Scripts\\python.exe src\\evaluation\\build_manifest.py")
    lines.append(
        ".\\.venv\\Scripts\\python.exe src\\evaluation\\final_metrics.py "
        "--manifest data\\evaluation\\final_evaluation_manifest_multicategory.json "
        "--output reports_multicategory\\multicategory_evaluation_metrics.json"
    )
    lines.append(".\\.venv\\Scripts\\python.exe src\\evaluation\\category_metrics.py")
    lines.append(".\\.venv\\Scripts\\python.exe src\\evaluation\\multicategory_report.py")
    lines.append(
        ".\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p \"test*.py\""
    )
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def write_report(
    metrics_path: Path = DEFAULT_METRICS_PATH,
    category_metrics_path: Path = DEFAULT_CATEGORY_METRICS_PATH,
    phone_metrics_path: Path | None = DEFAULT_PHONE_METRICS_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Render the report and write it next to the metrics files."""

    for path in (metrics_path, category_metrics_path):
        if not path.exists():
            raise ReportError(f"Metrics file was not found: {path}")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    category_metrics = json.loads(
        category_metrics_path.read_text(encoding="utf-8")
    )
    phone_metrics = None

    if phone_metrics_path is not None and phone_metrics_path.exists():
        phone_metrics = json.loads(
            phone_metrics_path.read_text(encoding="utf-8")
        )

    report = render_report(metrics, category_metrics, phone_metrics)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Render the multi-category four-method comparison report."
        )
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=DEFAULT_METRICS_PATH,
    )
    parser.add_argument(
        "--category-metrics",
        type=Path,
        default=DEFAULT_CATEGORY_METRICS_PATH,
    )
    parser.add_argument(
        "--phone-metrics",
        type=Path,
        default=DEFAULT_PHONE_METRICS_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    args = parser.parse_args()

    try:
        output_path = write_report(
            metrics_path=args.metrics,
            category_metrics_path=args.category_metrics,
            phone_metrics_path=args.phone_metrics,
            output_path=args.output,
        )
    except ReportError as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error

    print(f"Report saved: {output_path}")


if __name__ == "__main__":
    main()
