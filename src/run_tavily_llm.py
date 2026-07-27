"""Run Tavily search followed by NanoLLM relevance evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from nano_llm_evaluator import METHOD_TAVILY_LLM, NANO_LLM_PROMPT_VERSION, make_nano_llm_evaluator
from result_storage import create_unique_result_path
from tavily_client import make_tavily_client


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIRECTORY = PROJECT_ROOT / "results" / "tavily_llm"


def run_tavily_llm(
    product_id: str,
    keyword: str,
    search_provider: str = "tavily",
    evaluator_provider: str = "openrouter",
    max_results: int = 5,
) -> dict:
    start_time = perf_counter()
    search_client = make_tavily_client(search_provider, max_results=max_results)
    raw_results = search_client.search(keyword)
    evaluator = make_nano_llm_evaluator(provider=evaluator_provider)
    evaluated_results = evaluator.evaluate_results(keyword, raw_results)
    runtime_seconds = perf_counter() - start_time
    execution_mode = (
        "fake"
        if "fake" in {search_provider, evaluator_provider}
        else "live"
    )
    return {
        "product_id": product_id,
        "keyword": keyword,
        "method": METHOD_TAVILY_LLM,
        "execution_mode": execution_mode,
        "provider": f"{search_provider}+{evaluator_provider}",
        "model": getattr(evaluator, "model", evaluator_provider),
        "prompt_version": NANO_LLM_PROMPT_VERSION,
        "runtime_seconds": round(runtime_seconds, 2),
        "estimated_cost_usd": round(
            float(getattr(search_client, "last_cost_usd", 0.0))
            + float(getattr(evaluator, "last_cost_usd", 0.0)),
            8,
        ),
        "results": evaluated_results[:5],
    }


def save_result(output: dict) -> Path:
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(output["keyword"].encode("utf-8")).hexdigest()[:8]
    mode = output.get("execution_mode", "unknown")
    path = create_unique_result_path(
        directory=RESULTS_DIRECTORY,
        product_id=output["product_id"],
        method=METHOD_TAVILY_LLM,
        keyword_digest=digest,
        execution_mode=mode,
    )
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Tavily + NanoLLM for one keyword.")
    parser.add_argument("--product-id", default="P001")
    parser.add_argument("--keyword", default="Apple iPhone 16 Pro Max 256 GB fiyat")
    parser.add_argument("--search-provider", choices=["tavily", "fake"], default="tavily")
    parser.add_argument("--evaluator-provider", choices=["openrouter", "fake"], default="openrouter")
    parser.add_argument("--max-results", type=int, default=5)
    args = parser.parse_args()
    output = run_tavily_llm(
        product_id=args.product_id,
        keyword=args.keyword,
        search_provider=args.search_provider,
        evaluator_provider=args.evaluator_provider,
        max_results=args.max_results,
    )
    path = save_result(output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Result file saved: {path}")


if __name__ == "__main__":
    main()
