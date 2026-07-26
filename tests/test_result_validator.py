"""Unit tests for the common result JSON validator."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(
    0,
    str(SRC_DIRECTORY),
)

from evaluation.result_validator import (
    ResultValidationError,
    validate_result_file,
    validate_result_payload,
)


def create_valid_payload() -> dict:
    """Create a valid result payload for use in tests."""

    return {
        "product_id": "P001",
        "keyword": "Apple iPhone 16 Pro Max 256 GB fiyat",
        "method": "selenium_rule_based",
        "runtime_seconds": 12.5,
        "estimated_cost_usd": 0.0,
        "results": [
            {
                "domain": "example.com",
                "url": "https://example.com/product",
                "title": "Apple iPhone 16 Pro Max",
                "snippet": "Fiyat ve satın alma seçenekleri.",
                "predicted_relevant": True,
                "relevance_score": 0.9,
            }
        ],
    }


class ResultValidatorTests(unittest.TestCase):
    """Test valid and invalid common result payloads."""

    def test_valid_payload_is_accepted(self) -> None:
        payload = create_valid_payload()

        validated = validate_result_payload(
            payload=payload,
            source="test",
        )

        self.assertEqual(
            validated,
            payload,
        )

    def test_missing_required_field_is_rejected(self) -> None:
        payload = create_valid_payload()
        del payload["method"]

        with self.assertRaises(ResultValidationError):
            validate_result_payload(
                payload=payload,
                source="test",
            )

    def test_missing_runtime_seconds_is_rejected(self) -> None:
        payload = create_valid_payload()
        del payload["runtime_seconds"]

        with self.assertRaisesRegex(
            ResultValidationError,
            "runtime_seconds",
        ):
            validate_result_payload(
                payload=payload,
                source="test",
            )

    def test_missing_estimated_cost_is_rejected(self) -> None:
        payload = create_valid_payload()
        del payload["estimated_cost_usd"]

        with self.assertRaisesRegex(
            ResultValidationError,
            "estimated_cost_usd",
        ):
            validate_result_payload(
                payload=payload,
                source="test",
            )

    def test_unsupported_method_is_rejected(self) -> None:
        payload = create_valid_payload()
        payload["method"] = "unknown_method"

        with self.assertRaises(ResultValidationError):
            validate_result_payload(
                payload=payload,
                source="test",
            )

    def test_negative_runtime_is_rejected(self) -> None:
        payload = create_valid_payload()
        payload["runtime_seconds"] = -1.0

        with self.assertRaises(ResultValidationError):
            validate_result_payload(
                payload=payload,
                source="test",
            )

    def test_score_outside_range_is_rejected(self) -> None:
        payload = create_valid_payload()
        payload["results"][0]["relevance_score"] = 1.5

        with self.assertRaises(ResultValidationError):
            validate_result_payload(
                payload=payload,
                source="test",
            )

    def test_predicted_relevant_must_be_boolean(self) -> None:
        payload = create_valid_payload()
        payload["results"][0]["predicted_relevant"] = "true"

        with self.assertRaises(ResultValidationError):
            validate_result_payload(
                payload=payload,
                source="test",
            )

    def test_empty_results_are_rejected(self) -> None:
        payload = create_valid_payload()
        payload["results"] = []

        with self.assertRaises(ResultValidationError):
            validate_result_payload(
                payload=payload,
                source="test",
            )

    def test_result_file_is_read_and_validated(self) -> None:
        payload = copy.deepcopy(
            create_valid_payload()
        )

        with tempfile.TemporaryDirectory() as temp_directory:
            file_path = (
                Path(temp_directory)
                / "sample_result.json"
            )

            file_path.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            validated = validate_result_file(
                file_path
            )

        self.assertEqual(
            validated["product_id"],
            "P001",
        )

        self.assertEqual(
            validated["method"],
            "selenium_rule_based",
        )

    def test_invalid_json_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            file_path = (
                Path(temp_directory)
                / "invalid_result.json"
            )

            file_path.write_text(
                '{"product_id": "P001", invalid}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ResultValidationError,
                "invalid JSON",
            ):
                validate_result_file(file_path)

if __name__ == "__main__":
    unittest.main()
