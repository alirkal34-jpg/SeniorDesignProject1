"""Lock the committed Markdown reports to the committed metrics files.

The Markdown reports under ``reports_multicategory/`` are generated, not
written by hand, but they are committed so the thesis can quote a stable
file. That only holds if regenerating them changes nothing. It did not hold
once: the percent-encoding fix reduced the unique-URL count from 194 to 193
and every JSON metrics file was recomputed, but
``multicategory_evaluation_report.md`` was left at 194. The consistency
checker reads the Turkish report and the JSON files, so the stale English
report passed every gate for a full commit.

These tests re-render each committed report from the committed metrics and
require a byte-identical result. Regenerating and committing the report is
then part of any change that moves a number.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.category_metrics import render_markdown  # noqa: E402
from evaluation.multicategory_report import render_report  # noqa: E402


REPORTS = PROJECT_ROOT / "reports_multicategory"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class GeneratedReportsAreCurrentTest(unittest.TestCase):
    def assert_regenerates(self, path: Path, rendered: str) -> None:
        self.assertEqual(
            rendered,
            path.read_text(encoding="utf-8"),
            f"{path.name} does not match a fresh render of the committed "
            f"metrics. Regenerate it and commit the result.",
        )

    def test_comparison_report_matches_its_metrics(self) -> None:
        self.assert_regenerates(
            REPORTS / "multicategory_evaluation_report.md",
            render_report(
                load(REPORTS / "multicategory_evaluation_metrics.json"),
                load(REPORTS / "multicategory_category_metrics.json"),
                load(PROJECT_ROOT / "reports" / "final_evaluation_metrics.json"),
            ),
        )

    def test_category_tables_match_their_metrics(self) -> None:
        self.assert_regenerates(
            REPORTS / "multicategory_category_metrics.md",
            render_markdown(load(REPORTS / "multicategory_category_metrics.json")),
        )

    def test_aligned_prompt_category_tables_match_their_metrics(self) -> None:
        self.assert_regenerates(
            REPORTS / "prompt_v2_category_metrics.md",
            render_markdown(load(REPORTS / "prompt_v2_category_metrics.json")),
        )


if __name__ == "__main__":
    unittest.main()
