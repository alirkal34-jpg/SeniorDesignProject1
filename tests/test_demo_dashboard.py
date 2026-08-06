import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import demo_dashboard


class DemoDashboardTests(unittest.TestCase):
    def test_safe_project_path_accepts_project_artifact(self):
        path = demo_dashboard._safe_project_path(
            "reports/final_evaluation_report.md"
        )
        self.assertEqual(
            path,
            demo_dashboard.PROJECT_ROOT
            / "reports"
            / "final_evaluation_report.md",
        )

    def test_safe_project_path_rejects_parent_traversal(self):
        with self.assertRaises(ValueError):
            demo_dashboard._safe_project_path("../.env")

    def test_dashboard_never_returns_environment_values(self):
        snapshot = demo_dashboard.build_dashboard_snapshot()
        serialized = str(snapshot)
        self.assertNotIn("OPENROUTER_API_KEY", serialized)
        self.assertNotIn("TAVILY_API_KEY", serialized)

    def test_artifact_glob_returns_only_latest_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / "results" / "method"
            results.mkdir(parents=True)
            older = results / "older.json"
            newer = results / "newer.json"
            older.write_text("{}", encoding="utf-8")
            newer.write_text("{}", encoding="utf-8")
            older.touch()
            newer.touch()
            older_time = older.stat().st_mtime - 10
            import os

            os.utime(older, (older_time, older_time))
            with patch.object(demo_dashboard, "PROJECT_ROOT", root):
                artifacts = demo_dashboard._artifact_paths(
                    ("results/method/*.json",)
                )
            self.assertEqual(artifacts, ["results/method/newer.json"])


if __name__ == "__main__":
    unittest.main()
