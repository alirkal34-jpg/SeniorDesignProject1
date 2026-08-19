"""LangGraph orchestration for agentic and four-method comparison flows.

The agentic graph has plan, search, evaluate, and aggregate nodes. The
comparison graph has shared input, one node for each of the four methods, and a
final result aggregation node. Both flows support deterministic API-free tests.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Any, TypedDict

from agentic_search import (
    AGENTIC_PLANNER_PROMPT_VERSION,
    AgenticSearch,
)
from keyword_generator import (
    DEFAULT_INPUT_PATH,
    KEYWORD_PROMPT_VERSION,
    Product,
    load_products,
    make_client,
)
from nano_llm_evaluator import (
    METHOD_AGENTIC_SEARCH,
    NANO_LLM_PROMPT_VERSION,
    make_nano_llm_evaluator,
)
from result_storage import create_run_id, create_unique_result_path
from run_agentic_search import run_agentic_search
from run_selenium_nano_llm import run_selenium_nano_llm
from run_selenium_rule_based import run_selenium_rule_based
from run_tavily_llm import run_tavily_llm


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LANGGRAPH_RUNS_DIRECTORY = PROJECT_ROOT / "reports" / "langgraph_runs"
LANGGRAPH_METHOD_RESULTS_DIRECTORY = (
    LANGGRAPH_RUNS_DIRECTORY / "method_results"
)


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


class EndToEndState(TypedDict, total=False):
    product_id: str
    products_file: str
    keyword_provider: str
    execution_mode: str
    max_results: int
    product: dict[str, Any]
    keyword: str
    keyword_model: str
    keyword_runtime_seconds: float
    keyword_estimated_cost_usd: float
    comparison_output: dict[str, Any]
    rankings: list[dict[str, Any]]
    save_outputs: bool
    workflow_output_directory: str
    saved_result_files: list[str]
    workflow_output_path: str
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


def _end_to_end_error(
    state: EndToEndState,
    stage: str,
    exc: Exception,
) -> EndToEndState:
    new_state = dict(state)
    new_state["error"] = f"{stage}: {exc}"
    new_state["completed"] = False
    logger.error("End-to-end stage %s failed: %s", stage, exc)
    return new_state


def load_product_node(
    state: EndToEndState,
) -> EndToEndState:
    """Load one processed product as the workflow input."""

    new_state = dict(state)
    try:
        product_id = state.get("product_id", "").strip()
        if not product_id:
            raise ValueError("product_id is required.")
        products = load_products(
            Path(
                state.get(
                    "products_file",
                    str(DEFAULT_INPUT_PATH),
                )
            )
        )
        selected = next(
            (
                product
                for product in products
                if product.product_id == product_id
            ),
            None,
        )
        if selected is None:
            raise ValueError(
                f"Product {product_id} was not found in the processed dataset."
            )
        new_state["product"] = {
            "product_id": selected.product_id,
            "product_name": selected.product_name,
            "brand": selected.brand,
            "model": selected.model,
            "category": selected.category,
            "storage_gb": selected.storage_gb,
            "ram_gb": selected.ram_gb,
            "color": selected.color,
            "category_group": selected.category_group,
            "attributes": selected.attributes,
        }
    except Exception as exc:
        return _end_to_end_error(new_state, "load_product", exc)
    return new_state


def generate_keyword_node(
    state: EndToEndState,
) -> EndToEndState:
    """Generate one structured transactional keyword from product data."""

    new_state = dict(state)
    if state.get("error"):
        return new_state
    started_at = perf_counter()
    try:
        product_data = state["product"]
        product = Product(
            product_id=str(product_data["product_id"]),
            product_name=str(product_data["product_name"]),
            brand=str(product_data["brand"]),
            model=str(product_data["model"]),
            category=str(product_data["category"]),
            storage_gb=product_data.get("storage_gb"),
            ram_gb=product_data.get("ram_gb"),
            color=product_data.get("color"),
            category_group=str(product_data.get("category_group") or ""),
            attributes=product_data.get("attributes") or {},
        )
        provider = state.get("keyword_provider", "fake")
        client = make_client(provider)
        generated = client.generate_keywords([product])
        if len(generated) != 1:
            raise ValueError("Keyword generator must return exactly one keyword.")
        new_state["keyword"] = generated[0].keyword
        new_state["keyword_model"] = str(
            getattr(client, "model", provider)
        )
        new_state["keyword_runtime_seconds"] = round(
            perf_counter() - started_at,
            4,
        )
        new_state["keyword_estimated_cost_usd"] = round(
            float(getattr(client, "last_cost_usd", 0.0)),
            8,
        )
    except Exception as exc:
        return _end_to_end_error(new_state, "generate_keyword", exc)
    return new_state


def compare_methods_node(
    state: EndToEndState,
) -> EndToEndState:
    """Pass the generated keyword unchanged through all four methods."""

    new_state = dict(state)
    if state.get("error"):
        return new_state
    try:
        comparison_state = run_comparison_langgraph(
            product_id=state["product_id"],
            keyword=state["keyword"],
            execution_mode=state.get("execution_mode", "fake"),
            max_results=state.get("max_results", 5),
        )
        new_state["comparison_output"] = comparison_state.get(
            "output",
            {},
        )
        if not comparison_state.get("completed", False):
            errors = new_state["comparison_output"].get("errors", [])
            raise RuntimeError(
                f"One or more comparison methods failed: {errors}"
            )
    except Exception as exc:
        return _end_to_end_error(new_state, "compare_methods", exc)
    return new_state


def rank_results_node(
    state: EndToEndState,
) -> EndToEndState:
    """Rank each method's results by relevance decision and score.

    The original standardized method payloads remain unchanged. Rankings are
    stored separately in the workflow record so those payloads can still be
    validated with the shared result contract.
    """

    new_state = dict(state)
    if state.get("error"):
        new_state["rankings"] = []
        return new_state

    rankings: list[dict[str, Any]] = []
    comparison = state.get("comparison_output", {})
    for method_output in comparison.get("method_outputs", []):
        sorted_results = sorted(
            method_output.get("results", []),
            key=lambda item: float(item.get("relevance_score", 0.0)),
            reverse=True,
        )
        rankings.append(
            {
                "method": method_output.get("method", ""),
                "ranked_results": [
                    {
                        "rank": rank,
                        **dict(result),
                    }
                    for rank, result in enumerate(sorted_results, start=1)
                ],
            }
        )
    new_state["rankings"] = rankings
    return new_state


def end_to_end_aggregate_node(
    state: EndToEndState,
) -> EndToEndState:
    """Create the final product-to-comparison workflow record."""

    new_state = dict(state)
    comparison = state.get("comparison_output", {})
    total_runtime = round(
        max(
            0.0,
            perf_counter()
            - state.get("started_at", perf_counter()),
        ),
        4,
    )
    total_cost = round(
        float(state.get("keyword_estimated_cost_usd", 0.0))
        + float(comparison.get("total_estimated_cost_usd", 0.0)),
        8,
    )
    new_state["output"] = {
        "product": state.get("product", {}),
        "keyword_generation": {
            "provider": state.get("keyword_provider", "fake"),
            "model": state.get("keyword_model", ""),
            "prompt_version": KEYWORD_PROMPT_VERSION,
            "keyword": state.get("keyword", ""),
            "runtime_seconds": state.get(
                "keyword_runtime_seconds",
                0.0,
            ),
            "estimated_cost_usd": state.get(
                "keyword_estimated_cost_usd",
                0.0,
            ),
        },
        "comparison": comparison,
        "rankings": state.get("rankings", []),
        "total_runtime_seconds": total_runtime,
        "total_estimated_cost_usd": total_cost,
        "error": state.get("error"),
    }
    new_state["completed"] = (
        not state.get("error")
        and comparison.get("successful_method_count") == 4
        and comparison.get("all_methods_used_same_keyword") is True
    )
    return new_state


def _project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def save_task1_workflow_output(
    output: dict[str, Any],
    output_directory: Path = LANGGRAPH_RUNS_DIRECTORY,
) -> Path:
    """Persist one complete Task 1 LangGraph execution record."""

    output_directory.mkdir(parents=True, exist_ok=True)
    product_id = str(output.get("product", {}).get("product_id", "product"))
    execution_mode = str(
        output.get("comparison", {}).get("execution_mode", "unknown")
    )
    path = output_directory / (
        f"{product_id}_task1_langgraph_{execution_mode}_{create_run_id()}.json"
    )
    persisted_output = dict(output)
    persisted_output["workflow_output_path"] = _project_relative(path)
    path.write_text(
        json.dumps(persisted_output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def save_task1_method_output(
    output: dict[str, Any],
    output_directory: Path = LANGGRAPH_METHOD_RESULTS_DIRECTORY,
) -> Path:
    """Save one standard method payload outside the frozen result baseline."""

    method = str(output.get("method", "")).strip()
    if method not in {
        "selenium_rule_based",
        "selenium_nano_llm",
        "tavily_llm",
        "agentic_search",
    }:
        raise ValueError(f"Unsupported Task 1 method payload: {method!r}.")
    method_directory = output_directory / method
    method_directory.mkdir(parents=True, exist_ok=True)
    keyword_digest = hashlib.sha256(
        str(output.get("keyword", "")).encode("utf-8")
    ).hexdigest()[:8]
    path = create_unique_result_path(
        directory=method_directory,
        product_id=str(output.get("product_id", "product")),
        method=method,
        keyword_digest=keyword_digest,
        execution_mode=str(output.get("execution_mode", "unknown")),
    )
    path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def persist_output_node(
    state: EndToEndState,
) -> EndToEndState:
    """Save standard method payloads and the complete workflow evidence."""

    new_state = dict(state)
    if not state.get("save_outputs", False):
        return new_state

    output = dict(state.get("output", {}))
    saved_result_files: list[str] = []
    try:
        comparison = output.get("comparison", {})
        output_directory = Path(
            state.get(
                "workflow_output_directory",
                str(LANGGRAPH_RUNS_DIRECTORY),
            )
        )
        method_output_directory = output_directory / "method_results"
        for method_output in comparison.get("method_outputs", []):
            saved_result_files.append(
                _project_relative(
                    save_task1_method_output(
                        method_output,
                        method_output_directory,
                    )
                )
            )

        output["saved_result_files"] = saved_result_files
        workflow_path = save_task1_workflow_output(output, output_directory)
        output["workflow_output_path"] = _project_relative(workflow_path)
        new_state["saved_result_files"] = saved_result_files
        new_state["workflow_output_path"] = output["workflow_output_path"]
        new_state["output"] = output
    except Exception as exc:
        new_state = _end_to_end_error(new_state, "persist_output", exc)
        output["saved_result_files"] = saved_result_files
        output["error"] = new_state.get("error")
        new_state["output"] = output
    return new_state


def end_to_end_initial_state(
    product_id: str,
    products_file: Path = DEFAULT_INPUT_PATH,
    keyword_provider: str = "fake",
    execution_mode: str = "fake",
    max_results: int = 5,
    save_outputs: bool = False,
    workflow_output_directory: Path = LANGGRAPH_RUNS_DIRECTORY,
) -> EndToEndState:
    return {
        "product_id": product_id,
        "products_file": str(products_file),
        "keyword_provider": keyword_provider,
        "execution_mode": execution_mode,
        "max_results": min(max(1, max_results), 5),
        "keyword_runtime_seconds": 0.0,
        "keyword_estimated_cost_usd": 0.0,
        "comparison_output": {},
        "rankings": [],
        "save_outputs": save_outputs,
        "workflow_output_directory": str(workflow_output_directory),
        "saved_result_files": [],
        "started_at": perf_counter(),
        "error": None,
        "completed": False,
    }


def build_end_to_end_langgraph():
    """Compile the complete product-to-ranked-results Task 1 graph."""

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "Install the requirements, including langgraph, to build the graph flow."
        ) from exc

    graph = StateGraph(EndToEndState)
    graph.add_node("load_product", load_product_node)
    graph.add_node("generate_keyword", generate_keyword_node)
    graph.add_node("compare_methods", compare_methods_node)
    graph.add_node("rank_results", rank_results_node)
    graph.add_node("aggregate", end_to_end_aggregate_node)
    graph.add_node("persist_output", persist_output_node)
    graph.add_edge(START, "load_product")
    graph.add_edge("load_product", "generate_keyword")
    graph.add_edge("generate_keyword", "compare_methods")
    graph.add_edge("compare_methods", "rank_results")
    graph.add_edge("rank_results", "aggregate")
    graph.add_edge("aggregate", "persist_output")
    graph.add_edge("persist_output", END)
    return graph.compile()


def run_end_to_end_langgraph(
    product_id: str,
    products_file: Path = DEFAULT_INPUT_PATH,
    keyword_provider: str = "fake",
    execution_mode: str = "fake",
    max_results: int = 5,
    save_outputs: bool = False,
    workflow_output_directory: Path = LANGGRAPH_RUNS_DIRECTORY,
) -> EndToEndState:
    """Run product data through generation, four methods, and ranking."""

    graph = build_end_to_end_langgraph()
    return graph.invoke(
        end_to_end_initial_state(
            product_id=product_id,
            products_file=products_file,
            keyword_provider=keyword_provider,
            execution_mode=execution_mode,
            max_results=max_results,
            save_outputs=save_outputs,
            workflow_output_directory=workflow_output_directory,
        )
    )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Run the Task 1 LangGraph orchestration pipeline."
    )
    parser.add_argument(
        "--flow",
        choices=["agentic", "comparison", "end-to-end"],
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
    parser.add_argument(
        "--products",
        type=Path,
        default=DEFAULT_INPUT_PATH,
    )
    parser.add_argument(
        "--keyword-provider",
        choices=["fake", "openrouter"],
        default="fake",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help=(
            "Save standard method JSON files and the complete end-to-end "
            "workflow record. Supported by --flow end-to-end."
        ),
    )
    parser.add_argument(
        "--workflow-output-directory",
        type=Path,
        default=LANGGRAPH_RUNS_DIRECTORY,
    )
    args = parser.parse_args()

    if args.save and args.flow != "end-to-end":
        parser.error("--save is supported only with --flow end-to-end.")

    if args.flow == "end-to-end":
        result = run_end_to_end_langgraph(
            product_id=args.product_id,
            products_file=args.products,
            keyword_provider=args.keyword_provider,
            execution_mode=args.execution_mode,
            max_results=args.max_results,
            save_outputs=args.save,
            workflow_output_directory=args.workflow_output_directory,
        )
    elif args.flow == "comparison":
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
    if not result.get("completed", False):
        raise SystemExit(1)
