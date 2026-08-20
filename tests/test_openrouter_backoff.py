"""Unit tests for how the OpenRouter client waits after a rate-limit answer.

A batch run touches the provider once per product, so a single unbounded pause
stops the whole experiment. These tests pin down the two rules that keep a run
moving: rotate to a key that has not been tried, and never sleep longer than
the cap even when the provider asks for it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any
from urllib import error


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from keyword_generator import (  # noqa: E402
    OPENROUTER_MAX_BACKOFF_SECONDS,
    KeywordGenerationError,
    OpenRouterKeywordClient,
)


DAILY_LIMIT_BODY = (
    '{"error":{"message":"Rate limit exceeded: free-models-per-day",'
    '"code":429}}'
)
PER_MINUTE_BODY = '{"error":{"message":"Rate limit exceeded","code":429}}'


def rate_limit_error(body: str, retry_after: str | None) -> error.HTTPError:
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    return error.HTTPError(
        url="https://openrouter.ai/api/v1/chat/completions",
        code=429,
        msg="Too Many Requests",
        hdrs=headers,  # type: ignore[arg-type]
        fp=None,
    )


class RecordingClient(OpenRouterKeywordClient):
    """Client whose transport and clock are replaced by recorders."""

    def __init__(self, api_keys: list[str], responses: list[Any]) -> None:
        super().__init__(api_keys=api_keys, model="test-model")
        self.responses = list(responses)
        self.slept: list[float] = []
        self.keys_used: list[str] = []

    def _send(self, body: bytes) -> dict[str, Any]:
        self.keys_used.append(self.api_key)
        outcome = self.responses.pop(0)

        if isinstance(outcome, Exception):
            raise outcome

        return outcome


class BackoffTests(unittest.TestCase):
    """The pause after a 429 has to stay bounded."""

    def setUp(self) -> None:
        import keyword_generator

        self.module = keyword_generator
        self.original_sleep = keyword_generator.sleep
        self.addCleanup(
            setattr, keyword_generator, "sleep", self.original_sleep
        )

    def build(
        self,
        responses: list[Any],
        keys: list[str] | None = None,
    ) -> RecordingClient:
        client = RecordingClient(keys or ["key-a"], responses)
        self.module.sleep = client.slept.append
        return client

    def test_an_hours_long_retry_after_is_capped(self) -> None:
        # A spent daily allowance can come back with a Retry-After pointing at
        # midnight. Honouring it would park the batch for hours.
        client = self.build(
            [
                rate_limit_error(PER_MINUTE_BODY, retry_after="86400"),
                {"choices": [{"message": {"content": "{}"}}]},
            ]
        )

        client._post_json({"model": "test-model"})

        self.assertEqual(len(client.slept), 1)
        self.assertLessEqual(client.slept[0], OPENROUTER_MAX_BACKOFF_SECONDS)

    def test_a_short_retry_after_is_honoured_as_asked(self) -> None:
        client = self.build(
            [
                rate_limit_error(PER_MINUTE_BODY, retry_after="5"),
                {"choices": [{"message": {"content": "{}"}}]},
            ]
        )

        client._post_json({"model": "test-model"})

        self.assertEqual(client.slept, [5.0])

    def test_missing_retry_after_falls_back_to_exponential_backoff(
        self,
    ) -> None:
        client = self.build(
            [
                rate_limit_error(PER_MINUTE_BODY, retry_after=None),
                {"choices": [{"message": {"content": "{}"}}]},
            ]
        )

        client._post_json({"model": "test-model"})

        self.assertEqual(client.slept, [1.0])

    def test_rotation_is_tried_before_any_sleeping(self) -> None:
        # Another key may have its own allowance, so switching costs nothing
        # while waiting costs the whole batch its throughput.
        client = self.build(
            [
                rate_limit_error(DAILY_LIMIT_BODY, retry_after="3600"),
                {"choices": [{"message": {"content": "{}"}}]},
            ],
            keys=["key-a", "key-b"],
        )

        client._post_json({"model": "test-model"})

        self.assertEqual(client.slept, [])
        self.assertEqual(client.keys_used, ["key-a", "key-b"])

    def test_giving_up_beats_sleeping_forever(self) -> None:
        client = self.build(
            [rate_limit_error(PER_MINUTE_BODY, retry_after="86400")] * 8
        )

        with self.assertRaises(KeywordGenerationError):
            client._post_json({"model": "test-model"})

        # Bounded attempts, each bounded in length: the caller regains control
        # instead of the run hanging.
        self.assertLessEqual(
            sum(client.slept),
            OPENROUTER_MAX_BACKOFF_SECONDS * self.module.OPENROUTER_MAX_ATTEMPTS,
        )


if __name__ == "__main__":
    unittest.main()
