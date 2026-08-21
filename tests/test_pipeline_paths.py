"""Lock the path overrides a fresh, self-contained run depends on.

The pipeline can be shown end to end only if a run can start from a newly
collected file and never touch the committed dataset. Three modules take the
paths that make that possible, and the property worth locking is not that the
options exist but that they actually redirect: an override that silently fell
back to the default would let a demonstration overwrite the dataset the
report is computed from, or read the committed file while claiming to read
the new one.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from category_taxonomy import load_category_groups  # noqa: E402
from data_processor import MULTICATEGORY_PROFILE  # noqa: E402
from quality_check import build_multicategory_quality_profile  # noqa: E402


RAW_HEADER = (
    "product_id,product_name,brand,category,category_group,source_url,attributes\n"
)
RAW_ROW = (
    '{product_id},{name},{brand},"Elektronik, Cep Telefonu",'
    "elektronik_cep_telefonu,"
    'https://example.com/{product_id},"{{""variant_label"": ""256 GB""}}"\n'
)


def write_raw(path: Path, count: int = 2) -> None:
    rows = [RAW_HEADER]
    for index in range(1, count + 1):
        rows.append(
            RAW_ROW.format(
                product_id=f"ELK{index:03d}",
                name=f"Telefon {index}",
                brand=f"Marka{index}",
            )
        )
    path.write_text("".join(rows), encoding="utf-8")


def run_module(module: str, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / module), *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class DataProcessorPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.directory = Path(self._temporary.name)
        self.raw = self.directory / "raw.csv"
        write_raw(self.raw)

    def test_the_override_writes_only_into_the_given_directory(self) -> None:
        committed = MULTICATEGORY_PROFILE.output_json
        before = committed.read_bytes() if committed.exists() else None

        result = run_module(
            "data_processor.py",
            "--dataset",
            "multicategory",
            "--input",
            str(self.raw),
            "--output-directory",
            str(self.directory),
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        written = self.directory / MULTICATEGORY_PROFILE.output_json.name
        self.assertTrue(written.is_file(), "processed JSON was not redirected")
        self.assertEqual(
            [record["product_id"] for record in json.loads(written.read_text("utf-8"))],
            ["ELK001", "ELK002"],
        )

        after = committed.read_bytes() if committed.exists() else None
        self.assertEqual(before, after, "the committed dataset was overwritten")


class QualityCheckPathTests(unittest.TestCase):
    def test_narrowing_expects_only_the_named_groups(self) -> None:
        groups = load_category_groups()
        petshop = [group for group in groups if group.category_group == "petshop"]

        narrow = build_multicategory_quality_profile(
            groups=petshop, minimum_per_category=5
        )

        self.assertEqual(list(narrow.category_targets), ["petshop"])
        # The floor moved; the identifiers still belong to the real group,
        # so narrowing cannot smuggle in a product the taxonomy never named.
        self.assertTrue(
            all(
                product_id.startswith("PET")
                for product_id in narrow.expected_product_ids
            )
        )
        self.assertEqual(len(narrow.required_product_ids), 5)

    def test_a_processed_file_elsewhere_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            raw = directory / "raw.csv"
            write_raw(raw, count=5)

            processed = run_module(
                "data_processor.py",
                "--dataset",
                "multicategory",
                "--input",
                str(raw),
                "--output-directory",
                str(directory),
            )
            self.assertEqual(processed.returncode, 0, processed.stdout)

            result = run_module(
                "quality_check.py",
                "--dataset",
                "multicategory",
                "--input",
                str(directory / MULTICATEGORY_PROFILE.output_csv.name),
                "--categories",
                "elektronik_cep_telefonu",
                "--min-per-category",
                "5",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASSED", result.stdout)

    def test_an_unknown_category_stops_the_gate(self) -> None:
        result = run_module(
            "quality_check.py",
            "--dataset",
            "multicategory",
            "--categories",
            "there_is_no_such_group",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unknown category group", result.stdout)


if __name__ == "__main__":
    unittest.main()
