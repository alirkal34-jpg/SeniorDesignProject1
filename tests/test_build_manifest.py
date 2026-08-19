"""Unit tests for freezing result files into a metrics manifest."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation import build_manifest as build_manifest_module  # noqa: E402
from evaluation.build_manifest import (  # noqa: E402
    ManifestError,
    build_manifest,
    read_subset_product_ids,
    result_sort_key,
    select_latest_result_files,
)


SUBSET_HEADER = "product_id,product_name,category_group\n"

METHODS = (
    "tavily_llm",
    "agentic_search",
    "selenium_nano_llm",
    "selenium_rule_based",
)


class ResultSortKeyTests(unittest.TestCase):
    """Newest run wins, and the method name must not confuse the parse."""

    def test_timestamp_is_read_out_of_the_file_name(self) -> None:
        older = Path(
            "ELK001_selenium_nano_llm_abc_live_20260818T172936030993Z_x.json"
        )
        newer = Path(
            "ELK001_selenium_nano_llm_abc_live_20260819T090000000000Z_y.json"
        )

        self.assertLess(result_sort_key(older), result_sort_key(newer))

    def test_method_underscores_do_not_break_the_parse(self) -> None:
        # 'selenium_rule_based' contains the separator, so splitting the name
        # apart would pick up the wrong field.
        path = Path(
            "PET001_selenium_rule_based_abc_live_20260818T172936030993Z_z.json"
        )

        self.assertEqual(result_sort_key(path)[0], "20260818T172936030993Z")


class ManifestBuildTests(unittest.TestCase):
    """The manifest has to cover every product on every method, or fail."""

    def setUp(self) -> None:
        temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temp_directory.cleanup)
        self.root = Path(temp_directory.name)

        original_root = build_manifest_module.PROJECT_ROOT
        build_manifest_module.PROJECT_ROOT = self.root
        self.addCleanup(
            setattr,
            build_manifest_module,
            "PROJECT_ROOT",
            original_root,
        )

        self.results_directory = self.root / "results_multicategory"
        self.subset_path = self.root / "subset.csv"
        self.subset_path.write_text(
            SUBSET_HEADER
            + "ELK001,iPhone,elektronik_cep_telefonu\n"
            + "PET001,Mama,petshop\n",
            encoding="utf-8",
        )

    def write_result(
        self,
        product_id: str,
        method: str,
        timestamp: str = "20260818T172936030993Z",
        execution_mode: str = "live",
    ) -> Path:
        payload: dict[str, Any] = {
            "product_id": product_id,
            "keyword": f"{product_id} fiyat",
            "method": method,
            "execution_mode": execution_mode,
            "provider": "test",
            "model": "test-model",
            "prompt_version": "v1",
            "runtime_seconds": 1.0,
            "estimated_cost_usd": 0.0,
            "results": [
                {
                    "domain": "shop.example",
                    "url": "https://shop.example/a",
                    "title": "listing",
                    "snippet": "",
                    "predicted_relevant": True,
                    "relevance_score": 1.0,
                }
            ],
        }
        file_path = (
            self.results_directory
            / method
            / f"{product_id}_{method}_abc_{execution_mode}_{timestamp}_z.json"
        )
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return file_path

    def write_full_grid(self) -> None:
        for product_id in ("ELK001", "PET001"):
            for method in METHODS:
                self.write_result(product_id, method)

    def test_full_grid_is_frozen_with_relative_paths(self) -> None:
        self.write_full_grid()

        manifest = build_manifest(
            results_directory=self.results_directory,
            subset_path=self.subset_path,
            ground_truth_path=self.root / "labels.csv",
        )

        self.assertEqual(len(manifest["selected_result_files"]), 8)
        self.assertTrue(
            all(
                path.startswith("results_multicategory/")
                for path in manifest["selected_result_files"]
            )
        )
        self.assertEqual(manifest["ground_truth_file"], "labels.csv")

    def test_latest_run_of_a_product_replaces_the_earlier_one(self) -> None:
        self.write_full_grid()
        newest = self.write_result(
            "ELK001",
            "tavily_llm",
            timestamp="20260819T235959999999Z",
        )

        selected = select_latest_result_files(self.results_directory)

        self.assertEqual(selected[("ELK001", "tavily_llm")], newest)

    def test_fake_runs_are_never_frozen(self) -> None:
        self.write_full_grid()
        self.write_result(
            "ELK001",
            "tavily_llm",
            timestamp="20260819T235959999999Z",
            execution_mode="fake",
        )

        selected = select_latest_result_files(self.results_directory)

        self.assertIn(
            "20260818T172936030993Z",
            selected[("ELK001", "tavily_llm")].name,
        )

    def test_missing_method_for_one_product_fails_the_build(self) -> None:
        self.write_full_grid()
        (
            self.results_directory
            / "tavily_llm"
            / "PET001_tavily_llm_abc_live_20260818T172936030993Z_z.json"
        ).unlink()

        with self.assertRaises(ManifestError) as error:
            build_manifest(
                results_directory=self.results_directory,
                subset_path=self.subset_path,
                ground_truth_path=self.root / "labels.csv",
            )

        message = str(error.exception)
        self.assertIn("PET001/tavily_llm", message)
        self.assertIn("same products", message)

    def test_result_outside_the_subset_fails_the_build(self) -> None:
        self.write_full_grid()

        for method in METHODS:
            self.write_result("SPM009", method)

        with self.assertRaises(ManifestError) as error:
            build_manifest(
                results_directory=self.results_directory,
                subset_path=self.subset_path,
                ground_truth_path=self.root / "labels.csv",
            )

        self.assertIn("SPM009", str(error.exception))

    def test_directory_without_live_runs_is_refused(self) -> None:
        self.write_result("ELK001", "tavily_llm", execution_mode="fake")

        with self.assertRaises(ManifestError) as error:
            select_latest_result_files(self.results_directory)

        self.assertIn("No live result files", str(error.exception))


class SubsetReadTests(unittest.TestCase):
    """The subset file decides which products must be covered."""

    def write_subset(self, content: str) -> Path:
        temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temp_directory.cleanup)
        file_path = Path(temp_directory.name) / "subset.csv"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_reads_product_ids_in_file_order(self) -> None:
        subset_path = self.write_subset(
            SUBSET_HEADER
            + "ELK001,iPhone,elektronik_cep_telefonu\n"
            + "PET001,Mama,petshop\n"
        )

        self.assertEqual(
            read_subset_product_ids(subset_path),
            ["ELK001", "PET001"],
        )

    def test_missing_column_is_reported(self) -> None:
        subset_path = self.write_subset("name\nfoo\n")

        with self.assertRaises(ManifestError) as error:
            read_subset_product_ids(subset_path)

        self.assertIn("product_id", str(error.exception))

    def test_empty_subset_is_refused(self) -> None:
        subset_path = self.write_subset(SUBSET_HEADER)

        with self.assertRaises(ManifestError) as error:
            read_subset_product_ids(subset_path)

        self.assertIn("lists no products", str(error.exception))


if __name__ == "__main__":
    unittest.main()
