"""Unit tests for the presentation display helper.

The helper exists to put a pipeline file on a projector, so the properties
worth locking are the ones a viewer would be misled by: a truncated listing
must still say how many records there really are, a requested field that does
not exist must not be silently dropped, and a path outside the project must
never be read just because it was typed.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.show import (  # noqa: E402
    ShowError,
    keep_ids,
    newest_file,
    resolve_inside_project,
    select_fields,
    take,
)


class PathSafetyTests(unittest.TestCase):
    def test_project_file_resolves(self) -> None:
        resolved = resolve_inside_project("README.md")
        self.assertEqual(resolved, (PROJECT_ROOT / "README.md").resolve())

    def test_path_outside_the_project_is_refused(self) -> None:
        with self.assertRaises(ShowError):
            resolve_inside_project("../secrets.txt")

    def test_missing_path_is_refused(self) -> None:
        with self.assertRaises(ShowError):
            resolve_inside_project("data/there_is_no_such_file.json")


class SelectionTests(unittest.TestCase):
    def test_limit_takes_the_first_records(self) -> None:
        payload = [{"n": index} for index in range(10)]
        self.assertEqual(take(payload, 3, [], []), [{"n": 0}, {"n": 1}, {"n": 2}])

    def test_a_single_object_is_not_truncated(self) -> None:
        payload = {"accuracy": 0.7619}
        self.assertEqual(take(payload, 1, [], []), payload)

    def test_fields_are_kept_in_the_requested_order(self) -> None:
        record = {"a": 1, "b": 2, "c": 3}
        self.assertEqual(list(select_fields(record, ["c", "a"])), ["c", "a"])

    def test_a_field_that_does_not_exist_is_shown_as_empty(self) -> None:
        # Dropping it would let a demo claim a field was checked when the
        # file never carried it.
        self.assertEqual(select_fields({"a": 1}, ["missing"]), {"missing": None})


class IdSelectionTests(unittest.TestCase):
    RECORDS = [
        {"product_id": "ELK001"},
        {"product_id": "PET001"},
        {"product_id": "SPM001"},
    ]

    def test_records_come_back_in_the_requested_order(self) -> None:
        picked = keep_ids(self.RECORDS, ["SPM001", "ELK001"])
        self.assertEqual([item["product_id"] for item in picked], ["SPM001", "ELK001"])

    def test_an_id_that_is_not_in_the_file_is_refused(self) -> None:
        # Silently returning the two that matched would let a demo show two
        # products while claiming three.
        with self.assertRaises(ShowError):
            keep_ids(self.RECORDS, ["ELK001", "NOPE"])

    def test_ids_override_the_limit(self) -> None:
        picked = take(self.RECORDS, 1, [], ["ELK001", "SPM001"])
        self.assertEqual(len(picked), 2)

    def test_ids_are_refused_on_a_file_holding_one_object(self) -> None:
        with self.assertRaises(ShowError):
            take({"accuracy": 0.76}, 3, [], ["ELK001"])


class NewestFileTests(unittest.TestCase):
    def test_the_most_recent_result_file_is_chosen(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            older = directory / "run_a.json"
            newer = directory / "nested" / "run_b.json"
            newer.parent.mkdir()
            older.write_text(json.dumps({"run": "a"}), encoding="utf-8")
            newer.write_text(json.dumps({"run": "b"}), encoding="utf-8")
            older.touch()
            newer.touch()
            import os

            os.utime(older, (1_000_000, 1_000_000))

            self.assertEqual(newest_file(directory), newer)

    def test_a_directory_without_json_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            with self.assertRaises(ShowError):
                newest_file(Path(raw_directory))


if __name__ == "__main__":
    unittest.main()
