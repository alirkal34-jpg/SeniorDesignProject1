"""Run the agentic web-search planner and NanoLLM evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from agentic_search import AGENTIC_PLANNER_PROMPT_VERSION, AgenticSearch
from nano_llm_evaluator import METHOD_AGENTIC_SEARCH, NANO_LLM_PROMPT_VERSION, make_nano_llm_evaluator
from result_storage import create_unique_result_path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIRECTORY = PROJECT_ROOT / "results" / "agentic_search"


def run_agentic_search(
    product_id: str,
    keyword: str,
    search_provider: str = "selenium",
    evaluator_provider: str = "openrouter",
    planner_provider: str = "openrouter",
    max_results: int = 5,
    search_engine: str = "bing",
) -> dict:
    started_at = perf_counter()
    searcher = AgenticSearch(
        search_provider=search_provider,
        planner_provider=planner_provider,
        max_results=max_results,
        search_engine=search_engine,
    )
    try:
        raw_results = searcher.search(keyword)
    finally:
        searcher.close()
    evaluator = make_nano_llm_evaluator(provider=evaluator_provider)
    evaluated_results = evaluator.evaluate_results(keyword, raw_results)
    execution_mode = (
        "fake"
        if "fake" in {planner_provider, search_provider, evaluator_provider}
        else "live"
    )
    return {
        "product_id": product_id,
        "keyword": keyword,
        "method": METHOD_AGENTIC_SEARCH,
        "execution_mode": execution_mode,
        "provider": f"{planner_provider}+{search_provider}+{evaluator_provider}",
        "search_engine": (
            search_engine
            if search_provider == "selenium"
            else search_provider
        ),
        "model": getattr(evaluator, "model", evaluator_provider),
        "planner_model": searcher.planner_model,
        "prompt_version": (
            f"{AGENTIC_PLANNER_PROMPT_VERSION}+{NANO_LLM_PROMPT_VERSION}"
        ),
        "search_queries": searcher.last_queries,
        "search_errors": searcher.search_errors,
        "runtime_seconds": round(perf_counter() - started_at, 2),
        "estimated_cost_usd": round(
            searcher.last_cost_usd + float(getattr(evaluator, "last_cost_usd", 0.0)),
            8,
        ),
        "results": evaluated_results[:max_results],
    }


def save_result(output: dict) -> Path:
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(output["keyword"].encode("utf-8")).hexdigest()[:8]
    mode = output.get("execution_mode", "unknown")
    path = create_unique_result_path(
        directory=RESULTS_DIRECTORY,
        product_id=output["product_id"],
        method=METHOD_AGENTIC_SEARCH,
        keyword_digest=digest,
        execution_mode=mode,
    )
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run agentic web search for one keyword.")
    parser.add_argument("--product-id", default="P001")
    parser.add_argument("--keyword", default="Apple iPhone 16 Pro Max 256 GB fiyat")
    parser.add_argument(
        "--search-provider",
        choices=["selenium", "tavily", "fake"],
        default="selenium",
    )
    parser.add_argument(
        "--search-engine",
        choices=["google", "bing"],
        default="bing",
    )
    parser.add_argument("--evaluator-provider", choices=["openrouter", "fake"], default="openrouter")
    parser.add_argument("--planner-provider", choices=["openrouter", "fake"], default="openrouter")
    parser.add_argument("--max-results", type=int, default=5)
    args = parser.parse_args()
    output = run_agentic_search(
        product_id=args.product_id,
        keyword=args.keyword,
        search_provider=args.search_provider,
        evaluator_provider=args.evaluator_provider,
        planner_provider=args.planner_provider,
        max_results=args.max_results,
        search_engine=args.search_engine,
    )
    path = save_result(output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Result file saved: {path}")


if __name__ == "__main__":
    main()
