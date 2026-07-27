"""LangGraph orchestration flow for end-to-end product keyword search and evaluation.

This module provides functional state graph nodes for:
1. Planning search queries (plan_node)
2. Performing web search (search_node)
3. Evaluating result relevance (evaluate_node)
4. Aggregating results across methods (aggregate_node)
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Callable, TypedDict

from agentic_search import AgenticSearch
from nano_llm_evaluator import NANO_LLM_PROMPT_VERSION, make_nano_llm_evaluator

logger = logging.getLogger(__name__)


class AgenticState(TypedDict, total=False):
    product_id: str
    keyword: str
    search_provider: str
    evaluator_provider: str
    queries: list[str]
    raw_results: list[dict[str, Any]]
    evaluated_results: list[dict[str, Any]]
    runtime_seconds: float
    estimated_cost_usd: float
    error: str | None
    completed: bool


def plan_node(state: AgenticState) -> AgenticState:
    """Generate search queries for the target keyword."""
    new_state = dict(state)
    try:
        keyword = state.get("keyword", "")
        if not keyword:
            new_state["error"] = "Keyword is missing."
            new_state["queries"] = []
            return new_state

        searcher = AgenticSearch(provider=state.get("search_provider", "fake"))
        queries = searcher.plan_queries(keyword)
        new_state["queries"] = queries
    except Exception as exc:
        logger.error(f"Error in plan_node: {exc}")
        new_state["error"] = str(exc)
        new_state["queries"] = [state.get("keyword", "")]
    return new_state


def search_node(state: AgenticState) -> AgenticState:
    """Perform web search for planned queries and aggregate top-5 raw results."""
    new_state = dict(state)
    try:
        keyword = state.get("keyword", "")
        search_provider = state.get("search_provider", "fake")
        searcher = AgenticSearch(provider=search_provider, max_results=5)
        raw_results = searcher.search(keyword)
        new_state["raw_results"] = raw_results
        new_state["estimated_cost_usd"] = float(getattr(searcher, "last_cost_usd", 0.0))
    except Exception as exc:
        logger.error(f"Error in search_node: {exc}")
        new_state["error"] = str(exc)
        new_state["raw_results"] = []
    return new_state


def evaluate_node(state: AgenticState) -> AgenticState:
    """Evaluate raw search results for relevance using the designated evaluator."""
    new_state = dict(state)
    try:
        keyword = state.get("keyword", "")
        raw_results = state.get("raw_results", [])
        evaluator_provider = state.get("evaluator_provider", "fake")

        if not raw_results:
            new_state["evaluated_results"] = []
            return new_state

        evaluator = make_nano_llm_evaluator(provider=evaluator_provider)
        evaluated_results = evaluator.evaluate_results(keyword, raw_results)
        new_state["evaluated_results"] = evaluated_results[:5]

        eval_cost = float(getattr(evaluator, "last_cost_usd", 0.0))
        new_state["estimated_cost_usd"] = round(new_state.get("estimated_cost_usd", 0.0) + eval_cost, 8)
        new_state["completed"] = True
    except Exception as exc:
        logger.error(f"Error in evaluate_node: {exc}")
        new_state["error"] = str(exc)
        new_state["evaluated_results"] = []
    return new_state


def run_pipeline_step_by_step(
    product_id: str,
    keyword: str,
    search_provider: str = "fake",
    evaluator_provider: str = "fake",
) -> AgenticState:
    """Run the agentic search pipeline sequentially without requiring external dependencies."""
    start_time = perf_counter()
    initial_state: AgenticState = {
        "product_id": product_id,
        "keyword": keyword,
        "search_provider": search_provider,
        "evaluator_provider": evaluator_provider,
        "queries": [],
        "raw_results": [],
        "evaluated_results": [],
        "runtime_seconds": 0.0,
        "estimated_cost_usd": 0.0,
        "error": None,
        "completed": False,
    }

    state = plan_node(initial_state)
    state = search_node(state)
    state = evaluate_node(state)
    state["runtime_seconds"] = round(perf_counter() - start_time, 2)
    return state


def build_langgraph_flow():
    """Build and compile the LangGraph StateGraph if langgraph is available."""
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("Install langgraph to build the optional graph flow.") from exc

    graph = StateGraph(AgenticState)
    graph.add_node("plan", plan_node)
    graph.add_node("search", search_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "evaluate")
    graph.add_edge("evaluate", END)
    return graph.compile()


if __name__ == "__main__":
    import json

    state = run_pipeline_step_by_step("P001", "Apple iPhone 16 Pro Max 256 GB fiyat", "fake", "fake")
    print("=== LANGGRAPH SEQUENTIAL PIPELINE DEMO ===")
    print(json.dumps(state, ensure_ascii=False, indent=2))
