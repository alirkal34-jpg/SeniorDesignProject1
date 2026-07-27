"""LangGraph orchestration for agentic product search and evaluation.

The graph has four explicit nodes: plan, search, evaluate, and aggregate. The
same nodes can also run sequentially for API-free tests and easier debugging.
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


if __name__ == "__main__":
    import json

    result = run_pipeline_step_by_step(
        "P001",
        "Apple iPhone 16 Pro Max 256 GB fiyat",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
