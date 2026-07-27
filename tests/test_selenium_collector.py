"""Unit tests for search-engine-independent Selenium collection helpers."""

from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from selenium_collector import (
    collect_search_results,
    normalize_result_url,
)


class SeleniumCollectorTests(unittest.TestCase):
    def test_bing_redirect_is_normalized(self) -> None:
        target_url = (
            "https://www.trendyol.com/apple/"
            "iphone-16-pro-max-p-123"
        )
        encoded_target = base64.urlsafe_b64encode(
            target_url.encode("utf-8")
        ).decode("ascii").rstrip("=")
        redirect_url = (
            "https://www.bing.com/ck/a"
            f"?u=a1{encoded_target}"
        )

        self.assertEqual(
            normalize_result_url(redirect_url),
            target_url,
        )

    def test_unknown_search_engine_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported search engine",
        ):
            collect_search_results(
                browser=Mock(),
                keyword="Apple iPhone fiyat",
                search_engine="unsupported",
            )


if __name__ == "__main__":
    unittest.main()
