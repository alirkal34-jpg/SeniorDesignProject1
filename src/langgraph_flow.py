"""LangGraph orchestration for agentic and four-method comparison flows.

The agentic graph has plan, search, evaluate, and aggregate nodes. The
comparison graph has shared input, one node for each of the four methods, and a
final result aggregation node. Both flows support deterministic API-free tests.
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, TypedDict

from agentic_search import (
    AGENTIC_PLANNER_PROMPT_VERSION,
    AgenticSearch,
)
from nano_llm_evaluator import (
    METHOD_AGENTIC_SEARCH,
    NANO_LLM_PROMPT_VERSION,
    make_nano_llm_evaluator,
)
from run_agentic_search import run_agentic_search
from run_selenium_nano_llm import run_selenium_nano_llm
from run_selenium_rule_based import run_selenium_rule_based
from run_tavily_llm import run_tavily_llm


logger = logging.getLogger(__name__)


class AgenticState(TypedDict, total=False):
    product_id: str
    keyword: str
    planner_provider: str
    search_provider: str
    evaluator_provider: str
    max_results: int
    queries: list[str]
    raw_results: list[dict[str, Any]]
    evaluated_results: list[dict[str, Any]]
    planner_model: str
    evaluator_model: str
    runtime_seconds: float
    estimated_cost_usd: float
    started_at: float
    output: dict[str, Any]
    error: str | None
    completed: bool


class ComparisonState(TypedDict, total=False):
    product_id: str
    keyword: str
    execution_mode: str
    max_results: int
    method_outputs: dict[str, dict[str, Any]]
    method_errors: list[dict[str, str]]
    output: dict[str, Any]
    completed: bool


def _append_error(state: AgenticState, stage: str, exc: Exception) -> AgenticState:
    new_state = dict(state)
    message = f"{stage}: {exc}"
    logger.error(message)
    previous = state.get("error")
    new_state["error"] = f"{previous}; {message}" if previous else message
    new_state["completed"] = False
    return new_state


def plan_node(state: AgenticState) -> AgenticState:
    """Ask the configured planner to select transactional search queries."""

    new_state = dict(state)
    try:
        keyword = state.get("keyword", "").strip()
        if not keyword:
            raise ValueError("Keyword is missing.")
        searcher = AgenticSearch(
            search_provider=state.get("search_provider", "fake"),
            planner_provider=state.get("planner_provider", "fake"),
            max_results=state.get("max_results", 5),
        )
        new_state["queries"] = searcher.plan_queries(keyword)
        new_state["planner_model"] = searcher.planner_model
        new_state["estimated_cost_usd"] = round(
            float(state.get("estimated_cost_usd", 0.0))
            + searcher.last_planning_cost_usd,
            8,
        )
    except Exception as exc:
        new_state = _append_error(new_state, "plan", exc)
        new_state["queries"] = []
    return new_state


def search_node(state: AgenticState) -> AgenticState:
    """Execute the planned queries with the configured web-search tool."""

    new_state = dict(state)
    if state.get("error"):
        new_state["raw_results"] = []
        return new_state
    try:
        searcher = AgenticSearch(
            search_provider=state.get("search_provider", "fake"),
            planner_provider="fake",
            max_results=state.get("max_results", 5),
        )
        raw_results = searcher.search_queries(state.get("queries", []))
        new_state["raw_results"] = raw_results
        new_state["estimated_cost_usd"] = round(
            float(state.get("estimated_cost_usd", 0.0))
            + searcher.last_search_cost_usd,
            8,
        )
    except Exception as exc:
        new_state = _append_error(new_state, "search", exc)
        new_state["raw_results"] = []
    return new_state


def evaluate_node(state: AgenticState) -> AgenticState:
    """Evaluate search results with the configured NanoLLM provider."""

    new_state = dict(state)
    if state.get("error"):
        new_state["evaluated_results"] = []
        return new_state
    try:
        raw_results = state.get("raw_results", [])
        if not raw_results:
            raise ValueError("Search returned no results.")
        evaluator = make_nano_llm_evaluator(
            provider=state.get("evaluator_provider", "fake")
        )
        evaluated_results = evaluator.evaluate_results(
            state.get("keyword", ""),
            raw_results,
        )
        new_state["evaluated_results"] = evaluated_results[
            : state.get("max_results", 5)
        ]
        new_state["evaluator_model"] = getattr(
            evaluator,
            "model",
            state.get("evaluator_provider", "fake"),
        )
        new_state["estimated_cost_usd"] = round(
            float(state.get("estimated_cost_usd", 0.0))
            + float(getattr(evaluator, "last_cost_usd", 0.0)),
            8,
        )
    except Exception as exc:
        new_state = _append_error(new_state, "evaluate", exc)
        new_state["evaluated_results"] = []
    return new_state


def aggregate_node(state: AgenticState) -> AgenticState:
    """Build the shared experiment payload and mark the graph complete."""

    new_state = dict(state)
    runtime = max(0.0, perf_counter() - state.get("started_at", perf_counter()))
    new_state["runtime_seconds"] = round(runtime, 2)
    if state.get("error"):
        new_state["completed"] = False
        return new_state

    planner_provider = state.get("planner_provider", "fake")
    search_provider = state.get("search_provider", "fake")
    evaluator_provider = state.get("evaluator_provider", "fake")
    execution_mode = (
        "fake"
        if "fake" in {planner_provider, search_provider, evaluator_provider}
        else "live"
    )
    new_state["output"] = {
        "product_id": state.get("product_id", ""),
        "keyword": state.get("keyword", ""),
        "method": METHOD_AGENTIC_SEARCH,
        "execution_mode": execution_mode,
        "provider": f"{planner_provider}+{search_provider}+{evaluator_provider}",
        "model": state.get("evaluator_model", evaluator_provider),
        "planner_model": state.get("planner_model", planner_provider),
        "prompt_version": (
            f"{AGENTIC_PLANNER_PROMPT_VERSION}+{NANO_LLM_PROMPT_VERSION}"
        ),
        "search_queries": state.get("queries", []),
        "runtime_seconds": new_state["runtime_seconds"],
        "estimated_cost_usd": round(
            float(state.get("estimated_cost_usd", 0.0)),
            8,
        ),
        "results": state.get("evaluated_results", []),
    }
    new_state["completed"] = True
    return new_state


def initial_state(
    product_id: str,
    keyword: str,
    planner_provider: str = "fake",
    search_provider: str = "fake",
    evaluator_provider: str = "fake",
    max_results: int = 5,
) -> AgenticState:
    return {
        "product_id": product_id,
        "keyword": keyword,
        "planner_provider": planner_provider,
        "search_provider": search_provider,
        "evaluator_provider": evaluator_provider,
        "max_results": min(max(1, max_results), 5),
        "queries": [],
        "raw_results": [],
        "evaluated_results": [],
        "runtime_seconds": 0.0,
        "estimated_cost_usd": 0.0,
        "started_at": perf_counter(),
        "error": None,
        "completed": False,
    }


def run_pipeline_step_by_step(
    product_id: str,
    keyword: str,
    search_provider: str = "fake",
    evaluator_provider: str = "fake",
    planner_provider: str = "fake",
    max_results: int = 5,
) -> AgenticState:
    """Run the same four graph nodes sequentially for debugging/tests."""

    state = initial_state(
        product_id=product_id,
        keyword=keyword,
        planner_provider=planner_provider,
        search_provider=search_provider,
        evaluator_provider=evaluator_provider,
        max_results=max_results,
    )
    state = plan_node(state)
    state = search_node(state)
    state = evaluate_node(state)
    return aggregate_node(state)


def build_langgraph_flow():
    """Build and compile the four-node LangGraph StateGraph."""

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "Install the requirements, including langgraph, to build the graph flow."
        ) from exc

    graph = StateGraph(AgenticState)
    graph.add_node("plan", plan_node)
    graph.add_node("search", search_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("aggregate", aggregate_node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "evaluate")
    graph.add_edge("evaluate", "aggregate")
    graph.add_edge("aggregate", END)
    return graph.compile()


def run_langgraph_pipeline(
    product_id: str,
    keyword: str,
    planner_provider: str = "fake",
    search_provider: str = "fake",
    evaluator_provider: str = "fake",
    max_results: int = 5,
) -> AgenticState:
    """Invoke the compiled LangGraph flow."""

    graph = build_langgraph_flow()
    return graph.invoke(
        initial_state(
            product_id=product_id,
            keyword=keyword,
            planner_provider=planner_provider,
            search_provider=search_provider,
            evaluator_provider=evaluator_provider,
            max_results=max_results,
        )
    )


def comparison_input_node(
    state: ComparisonState,
) -> ComparisonState:
    """Validate the shared product/keyword input for all methods."""

    new_state = dict(state)
    errors = list(state.get("method_errors", []))
    product_id = state.get("product_id", "").strip()
    keyword = state.get("keyword", "").strip()
    execution_mode = state.get("execution_mode", "fake")
    if not product_id:
        errors.append(
            {
                "method": "input",
                "error": "product_id is required.",
            }
        )
    if not keyword:
        errors.append(
            {
                "method": "input",
                "error": "keyword is required.",
            }
        )
    if execution_mode not in {"fake", "live"}:
        errors.append(
            {
                "method": "input",
                "error": "execution_mode must be 'fake' or 'live'.",
            }
        )
    new_state["product_id"] = product_id
    new_state["keyword"] = keyword
    new_state["execution_mode"] = execution_mode
    new_state["max_results"] = min(
        max(1, int(state.get("max_results", 5))),
        5,
    )
    new_state["method_outputs"] = dict(
        state.get("method_outputs", {})
    )
    new_state["method_errors"] = errors
    new_state["completed"] = False
    return new_state


def _comparison_method_node(
    state: ComparisonState,
    method: str,
) -> ComparisonState:
    new_state = dict(state)
    outputs = dict(state.get("method_outputs", {}))
    errors = list(state.get("method_errors", []))
    if any(error.get("method") == "input" for error in errors):
        new_state["method_outputs"] = outputs
        new_state["method_errors"] = errors
        return new_state

    product_id = state.get("product_id", "")
    keyword = state.get("keyword", "")
    max_results = state.get("max_results", 5)
    is_fake = state.get("execution_mode", "fake") == "fake"

    try:
        if method == "selenium_rule_based":
            payload = run_selenium_rule_based(
                product_id=product_id,
                keyword=keyword,
                max_results=max_results,
                search_provider="fake" if is_fake else "selenium",
            )
        elif method == "selenium_nano_llm":
            payload = run_selenium_nano_llm(
                product_id=product_id,
                keyword=keyword,
                max_results=max_results,
                provider="fake" if is_fake else "openrouter",
                search_provider="fake" if is_fake else "selenium",
            )
        elif method == "tavily_llm":
            payload = run_tavily_llm(
                product_id=product_id,
                keyword=keyword,
                search_provider="fake" if is_fake else "tavily",
                evaluator_provider="fake" if is_fake else "openrouter",
                max_results=max_results,
            )
        elif method == "agentic_search":
            payload = run_agentic_search(
                product_id=product_id,
                keyword=keyword,
                planner_provider="fake" if is_fake else "openrouter",
                search_provider="fake" if is_fake else "selenium",
                evaluator_provider="fake" if is_fake else "openrouter",
                max_results=max_results,
            )
        else:
            raise ValueError(f"Unsupported comparison method: {method}")
        outputs[method] = payload
    except Exception as exc:
        logger.error("Comparison method %s failed: %s", method, exc)
        errors.append(
            {
                "method": method,
                "error": str(exc),
            }
        )

    new_state["method_outputs"] = outputs
    new_state["method_errors"] = errors
    return new_state


def selenium_rule_based_node(
    state: ComparisonState,
) -> ComparisonState:
    """Run Selenium + Rule-Based with the shared input."""

    return _comparison_method_node(
        state,
        "selenium_rule_based",
    )


def selenium_nano_llm_node(
    state: ComparisonState,
) -> ComparisonState:
    """Run Selenium + NanoLLM with the shared input."""

    return _comparison_method_node(
        state,
        "selenium_nano_llm",
    )


def tavily_llm_node(
    state: ComparisonState,
) -> ComparisonState:
    """Run Tavily + NanoLLM with the shared input."""

    return _comparison_method_node(
        state,
        "tavily_llm",
    )


def agentic_search_node(
    state: ComparisonState,
) -> ComparisonState:
    """Run LLM-planned Agentic Search with the shared input."""

    return _comparison_method_node(
        state,
        "agentic_search",
    )


def comparison_aggregate_node(
    state: ComparisonState,
) -> ComparisonState:
    """Aggregate method payloads and preserve per-method errors."""

    new_state = dict(state)
    method_outputs = dict(state.get("method_outputs", {}))
    method_errors = list(state.get("method_errors", []))
    ordered_methods = (
        "selenium_rule_based",
        "selenium_nano_llm",
        "tavily_llm",
        "agentic_search",
    )
    outputs = [
        method_outputs[method]
        for method in ordered_methods
        if method in method_outputs
    ]
    keywords = {
        payload.get("keyword")
        for payload in outputs
    }
    new_state["output"] = {
        "product_id": state.get("product_id", ""),
        "keyword": state.get("keyword", ""),
        "execution_mode": state.get("execution_mode", "fake"),
        "requested_method_count": len(ordered_methods),
        "successful_method_count": len(outputs),
        "failed_method_count": len(method_errors),
        "all_methods_used_same_keyword": (
            len(keywords) == 1
            and state.get("keyword") in keywords
        ),
        "total_runtime_seconds": round(
            sum(
                float(payload.get("runtime_seconds", 0.0))
                for payload in outputs
            ),
            4,
        ),
        "total_estimated_cost_usd": round(
            sum(
                float(payload.get("estimated_cost_usd", 0.0))
                for payload in outputs
            ),
            8,
        ),
        "method_outputs": outputs,
        "errors": method_errors,
    }
    new_state["completed"] = (
        len(outputs) == len(ordered_methods)
        and not method_errors
    )
    return new_state


def comparison_initial_state(
    product_id: str,
    keyword: str,
    execution_mode: str = "fake",
    max_results: int = 5,
) -> ComparisonState:
    return {
        "product_id": product_id,
        "keyword": keyword,
        "execution_mode": execution_mode,
        "max_results": max_results,
        "method_outputs": {},
        "method_errors": [],
        "completed": False,
    }


def build_comparison_langgraph():
    """Compile the six-node, four-method comparison graph."""

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "Install the requirements, including langgraph, to build the graph flow."
        ) from exc

    graph = StateGraph(ComparisonState)
    graph.add_node("input", comparison_input_node)
    graph.add_node(
        "selenium_rule_based",
        selenium_rule_based_node,
    )
    graph.add_node(
        "selenium_nano_llm",
        selenium_nano_llm_node,
    )
    graph.add_node("tavily_llm", tavily_llm_node)
    graph.add_node(
        "agentic_search",
        agentic_search_node,
    )
    graph.add_node(
        "result_aggregation",
        comparison_aggregate_node,
    )
    graph.add_edge(START, "input")
    graph.add_edge("input", "selenium_rule_based")
    graph.add_edge(
        "selenium_rule_based",
        "selenium_nano_llm",
    )
    graph.add_edge("selenium_nano_llm", "tavily_llm")
    graph.add_edge("tavily_llm", "agentic_search")
    graph.add_edge(
        "agentic_search",
        "result_aggregation",
    )
    graph.add_edge("result_aggregation", END)
    return graph.compile()


def run_comparison_langgraph(
    product_id: str,
    keyword: str,
    execution_mode: str = "fake",
    max_results: int = 5,
) -> ComparisonState:
    """Run one product through all four methods using the same keyword."""

    graph = build_comparison_langgraph()
    return graph.invoke(
        comparison_initial_state(
            product_id=product_id,
            keyword=keyword,
            execution_mode=execution_mode,
            max_results=max_results,
        )
    )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Run an API-free LangGraph demonstration."
    )
    parser.add_argument(
        "--flow",
        choices=["agentic", "comparison"],
        default="comparison",
    )
    parser.add_argument("--product-id", default="P001")
    parser.add_argument(
        "--keyword",
        default="Apple iPhone 16 Pro Max 256 GB fiyat",
    )
    parser.add_argument(
        "--execution-mode",
        choices=["fake", "live"],
        default="fake",
    )
    parser.add_argument("--max-results", type=int, default=5)
    args = parser.parse_args()

    if args.flow == "comparison":
        result = run_comparison_langgraph(
            product_id=args.product_id,
            keyword=args.keyword,
            execution_mode=args.execution_mode,
            max_results=args.max_results,
        )
    else:
        provider = (
            "fake"
            if args.execution_mode == "fake"
            else "openrouter"
        )
        result = run_langgraph_pipeline(
            product_id=args.product_id,
            keyword=args.keyword,
            planner_provider=provider,
            search_provider=(
                "fake"
                if args.execution_mode == "fake"
                else "tavily"
            ),
            evaluator_provider=provider,
            max_results=args.max_results,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
