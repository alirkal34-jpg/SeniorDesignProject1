"""Characterization tests that lock the current LangGraph orchestration.

These record the shape of the Task 1 pipeline as it runs today, so the
multi-category revision cannot silently change the graph topology, the shared
result contract, or the fake end-to-end output that every demo depends on.

Everything here runs in `fake` execution mode. No network call, no browser, and
no API key is involved.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.result_validator import (
    ALLOWED_METHODS,
    REQUIRED_PAYLOAD_FIELDS,
    REQUIRED_RESULT_FIELDS,
    validate_result_payload,
)
from langgraph_flow import (
    build_comparison_langgraph,
    build_end_to_end_langgraph,
    build_langgraph_flow,
    run_comparison_langgraph,
    run_end_to_end_langgraph,
)


ORDERED_METHODS = (
    "selenium_rule_based",
    "selenium_nano_llm",
    "tavily_llm",
    "agentic_search",
)


class GraphTopologyTests(unittest.TestCase):
    """Freeze the node names of the three compiled graphs."""

    def test_agentic_graph_has_four_nodes(self) -> None:
        nodes = set(build_langgraph_flow().get_graph().nodes)

        self.assertTrue(
            {"plan", "search", "evaluate", "aggregate"}.issubset(nodes)
        )

    def test_comparison_graph_has_input_four_methods_and_aggregation(
        self,
    ) -> None:
        nodes = set(build_comparison_langgraph().get_graph().nodes)

        self.assertTrue(
            {"input", "result_aggregation", *ORDERED_METHODS}.issubset(nodes)
        )

    def test_end_to_end_graph_covers_product_to_persisted_output(self) -> None:
        nodes = set(build_end_to_end_langgraph().get_graph().nodes)

        self.assertTrue(
            {
                "load_product",
                "generate_keyword",
                "compare_methods",
                "rank_results",
                "aggregate",
                "persist_output",
            }.issubset(nodes)
        )


class SharedResultContractTests(unittest.TestCase):
    """Freeze the JSON contract every method payload has to satisfy."""

    def test_allowed_methods_are_exactly_the_four_compared_methods(
        self,
    ) -> None:
        self.assertEqual(ALLOWED_METHODS, set(ORDERED_METHODS))

    def test_required_payload_fields_are_fixed(self) -> None:
        self.assertEqual(
            REQUIRED_PAYLOAD_FIELDS,
            {
                "product_id",
                "keyword",
                "method",
                "execution_mode",
                "provider",
                "model",
                "prompt_version",
                "runtime_seconds",
                "estimated_cost_usd",
                "results",
            },
        )

    def test_required_result_fields_are_fixed(self) -> None:
        self.assertEqual(
            REQUIRED_RESULT_FIELDS,
            {
                "domain",
                "url",
                "title",
                "snippet",
                "predicted_relevant",
                "relevance_score",
            },
        )


class ComparisonFlowTests(unittest.TestCase):
    """Freeze how one keyword travels through all four methods."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.state = run_comparison_langgraph(
            product_id="P001",
            keyword="Apple iPhone 16 Pro Max 256 GB fiyat",
            execution_mode="fake",
        )
        cls.output = cls.state["output"]

    def test_all_four_methods_complete(self) -> None:
        self.assertTrue(self.state["completed"])
        self.assertEqual(self.output["requested_method_count"], 4)
        self.assertEqual(self.output["successful_method_count"], 4)
        self.assertEqual(self.output["failed_method_count"], 0)
        self.assertEqual(self.output["errors"], [])

    def test_method_payloads_keep_a_fixed_order(self) -> None:
        self.assertEqual(
            [payload["method"] for payload in self.output["method_outputs"]],
            list(ORDERED_METHODS),
        )

    def test_the_same_keyword_reaches_every_method_unchanged(self) -> None:
        self.assertTrue(self.output["all_methods_used_same_keyword"])
        self.assertEqual(
            {payload["keyword"] for payload in self.output["method_outputs"]},
            {"Apple iPhone 16 Pro Max 256 GB fiyat"},
        )

    def test_every_payload_satisfies_the_shared_result_contract(self) -> None:
        for payload in self.output["method_outputs"]:
            with self.subTest(method=payload["method"]):
                validate_result_payload(payload, source=payload["method"])

    def test_fake_mode_is_recorded_and_costs_nothing(self) -> None:
        self.assertEqual(self.output["execution_mode"], "fake")
        self.assertEqual(self.output["total_estimated_cost_usd"], 0.0)
        for payload in self.output["method_outputs"]:
            with self.subTest(method=payload["method"]):
                self.assertEqual(payload["execution_mode"], "fake")

    def test_a_missing_keyword_stops_every_method(self) -> None:
        state = run_comparison_langgraph(
            product_id="P001",
            keyword="   ",
            execution_mode="fake",
        )

        self.assertFalse(state["completed"])
        self.assertEqual(state["output"]["successful_method_count"], 0)


class EndToEndFlowTests(unittest.TestCase):
    """Freeze the deterministic product-to-ranked-results workflow."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.state = run_end_to_end_langgraph(
            product_id="P001",
            keyword_provider="fake",
            execution_mode="fake",
        )
        cls.output = cls.state["output"]

    def test_workflow_completes_without_error(self) -> None:
        self.assertTrue(self.state["completed"])
        self.assertIsNone(self.output["error"])

    def test_product_data_is_loaded_from_the_processed_dataset(self) -> None:
        # CHANGED during the ten-category revision: the workflow state now
        # also carries category_group and attributes, so an attribute-driven
        # product keeps its variant all the way to keyword generation. Both
        # are empty for the smartphone dataset, which has no such columns.
        self.assertEqual(
            self.output["product"],
            {
                "product_id": "P001",
                "product_name": "Apple iPhone 16 Pro Max 256 GB",
                "brand": "Apple",
                "model": "iPhone 16 Pro Max",
                "category": "Smartphone",
                "storage_gb": 256,
                "ram_gb": 8,
                "color": "Black Titanium",
                "category_group": "",
                "attributes": {},
            },
        )

    def test_fake_provider_generates_a_deterministic_keyword(self) -> None:
        self.assertEqual(
            self.output["keyword_generation"]["keyword"],
            "Apple iPhone 16 Pro Max 256 GB fiyat",
        )
        self.assertEqual(
            self.output["keyword_generation"]["model"],
            "deterministic-fake-keyword-generator",
        )
        self.assertEqual(
            self.output["keyword_generation"]["prompt_version"],
            "keyword-generation-v1",
        )

    def test_every_method_is_ranked_by_descending_relevance_score(
        self,
    ) -> None:
        self.assertEqual(
            [ranking["method"] for ranking in self.output["rankings"]],
            list(ORDERED_METHODS),
        )
        for ranking in self.output["rankings"]:
            with self.subTest(method=ranking["method"]):
                scores = [
                    result["relevance_score"]
                    for result in ranking["ranked_results"]
                ]
                self.assertEqual(scores, sorted(scores, reverse=True))
                self.assertEqual(
                    [result["rank"] for result in ranking["ranked_results"]],
                    list(range(1, len(scores) + 1)),
                )

    def test_ranking_does_not_alter_the_stored_method_payloads(self) -> None:
        for payload in self.output["comparison"]["method_outputs"]:
            with self.subTest(method=payload["method"]):
                for result in payload["results"]:
                    self.assertNotIn("rank", result)

    def test_an_unknown_product_id_fails_before_any_method_runs(self) -> None:
        state = run_end_to_end_langgraph(
            product_id="P999",
            keyword_provider="fake",
            execution_mode="fake",
        )

        self.assertFalse(state["completed"])
        self.assertIn("load_product", state["output"]["error"])
        self.assertEqual(state["output"]["comparison"], {})


if __name__ == "__main__":
    unittest.main()
