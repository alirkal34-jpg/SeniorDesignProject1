"""Create the human-readable four-method comparison report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METRICS_PATH = (
    PROJECT_ROOT / "reports" / "final_evaluation_metrics.json"
)
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "reports" / "final_evaluation_report.md"
)
METHOD_LABELS = {
    "agentic_search": "Agentic Search",
    "selenium_nano_llm": "Selenium + NanoLLM",
    "selenium_rule_based": "Selenium + Rule-Based",
    "tavily_llm": "Tavily + NanoLLM",
}


def _percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def render_report(metrics: dict[str, Any]) -> str:
    """Render validated final metrics as a concise Markdown report."""

    methods = metrics.get("methods", {})
    missing_methods = set(METHOD_LABELS) - set(methods)
    if missing_methods:
        raise ValueError(
            f"Metrics report is missing methods: {sorted(missing_methods)}"
        )
    if metrics.get("ground_truth_coverage_ratio") != 1.0:
        raise ValueError(
            "Final comparison report requires complete ground-truth coverage."
        )

    accuracy_winner = max(
        methods,
        key=lambda name: methods[name]["accuracy"],
    )
    runtime_winner = min(
        methods,
        key=lambda name: methods[name]["average_runtime_seconds"],
    )

    rows = []
    for method_name in METHOD_LABELS:
        method = methods[method_name]
        rows.append(
            "| "
            f"{METHOD_LABELS[method_name]} | "
            f"{method['experiment_count']} | "
            f"{method['result_count']} | "
            f"{_percent(method['accuracy'])} | "
            f"{method['average_runtime_seconds']:.3f} s | "
            f"{_percent(method['relevant_result_ratio'])} | "
            f"${method['total_estimated_cost_usd']:.8f} |"
        )

    return "\n".join(
        [
            "# Final Four-Method Evaluation Report",
            "",
            "## Objective",
            "",
            "This report compares four approaches for finding transactional e-commerce pages from fixed smartphone keywords.",
            "It is the human-readable companion to `final_evaluation_metrics.json`.",
            "",
            "## Experimental protocol",
            "",
            f"- Products: {metrics['product_count']} fixed smartphones.",
            "- Input: one fixed keyword per product, reused unchanged by every method.",
            "- Maximum search results: 5 per product and method.",
            "- Rule-Based relevance threshold: 0.60.",
            f"- Experiments: {metrics['experiment_count']} live method/product runs.",
            f"- Evaluated results: {metrics['result_count']}.",
            f"- Ground-truth records available: {metrics['ground_truth_record_count']}.",
            f"- Final-run label coverage: {_percent(metrics['ground_truth_coverage_ratio'])}.",
            "- Relevance rule: correct model and capacity in a transactional page; wrong model/capacity, accessories, news, and reviews are irrelevant.",
            "",
            "## Results",
            "",
            "| Method | Runs | Results | Accuracy | Avg. runtime | Relevant ratio | Total estimated cost |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *rows,
            "",
            f"Overall accuracy was **{_percent(metrics['accuracy'])}** ({metrics['correct_prediction_count']} correct predictions out of {metrics['labeled_result_count']} labeled results). The aggregate",
            "confusion counts were:",
            "",
            f"- True positives: {metrics['true_positive_count']}",
            f"- True negatives: {metrics['true_negative_count']}",
            f"- False positives: {metrics['false_positive_count']}",
            f"- False negatives: {metrics['false_negative_count']}",
            "",
            "## Interpretation",
            "",
            f"- Highest measured accuracy: **{METHOD_LABELS[accuracy_winner]}** at {_percent(methods[accuracy_winner]['accuracy'])}.",
            f"- Lowest average runtime: **{METHOD_LABELS[runtime_winner]}** at {methods[runtime_winner]['average_runtime_seconds']:.3f} seconds.",
            "- Agentic Search marked every returned result relevant, which produced high recall behavior but also the largest false-positive tendency.",
            "- Relevant-result ratio is not accuracy; it only describes how often a method predicted relevance.",
            "",
            "## Cost interpretation",
            "",
            "Every retained run reports an estimated cost of $0.00 because the configured OpenRouter model was free and Tavily search cost was recorded as zero for this experiment.",
            "This does not mean the providers or future runs are always free.",
            "",
            "## Limitations",
            "",
            "- The 86 final-evaluation labels were AI-assisted and then explicitly accepted by the project owner; they were not independently entered one URL at a time.",
            "- The fixed 100-keyword file is deterministic; a separate three-product live OpenRouter smoke output proves the real keyword API path.",
            "- Selenium used Bing for the successful retained NanoLLM run after Google presented a CAPTCHA page.",
            "- One run per product/method is reported, so variance and confidence intervals are outside this task's current scope.",
            "",
            "## Reproduction",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe src\\evaluation\\final_report.py",
            ".\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p \"test*.py\" -v",
            "```",
            "",
        ]
    )


def write_report(
    metrics_path: Path = DEFAULT_METRICS_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(metrics), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the final human-readable comparison report."
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=DEFAULT_METRICS_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    args = parser.parse_args()
    print(write_report(args.metrics, args.output))


if __name__ == "__main__":
    main()
