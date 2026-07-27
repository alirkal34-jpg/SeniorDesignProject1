"""Run Selenium search collection and NanoLLM relevance evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from nano_llm_evaluator import METHOD_SELENIUM_NANO_LLM, NANO_LLM_PROMPT_VERSION, make_nano_llm_evaluator
from result_storage import create_unique_result_path
from selenium_collector import collect_search_results, create_browser


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIRECTORY = PROJECT_ROOT / "results" / "selenium_nano_llm"
ESTIMATED_COST_USD = 0.0


def run_selenium_nano_llm(
    product_id: str,
    keyword: str,
    max_results: int = 5,
    provider: str = "fake",
    search_provider: str = "selenium",
) -> dict:
    start_time = perf_counter()
    if search_provider == "fake":
        raw_results = [
            {
                "domain": "trendyol.com",
                "url": "https://www.trendyol.com/apple-iphone-16-pro-max",
                "title": f"{keyword} satın al",
                "snippet": "Mağaza fiyatları ve satın alma seçenekleri.",
            },
            {
                "domain": "teknoseyir.com",
                "url": "https://teknoseyir.com/iphone-16-pro-max-inceleme",
                "title": f"{keyword} inceleme",
                "snippet": "Kamera, pil ve performans değerlendirmesi.",
            },
        ][:max_results]
    else:
        browser = create_browser()
        try:
            raw_results = collect_search_results(
                browser=browser,
                keyword=keyword,
                max_results=max_results,
            )
        finally:
            browser.quit()

    evaluator = make_nano_llm_evaluator(provider=provider)
    evaluated_results = evaluator.evaluate_results(
        keyword=keyword,
        results=raw_results,
    )

    runtime_seconds = perf_counter() - start_time
    estimated_cost_usd = float(getattr(evaluator, "last_cost_usd", ESTIMATED_COST_USD))
    execution_mode = (
        "fake"
        if "fake" in {search_provider, provider}
        else "live"
    )

    return {
        "product_id": product_id,
        "keyword": keyword,
        "method": METHOD_SELENIUM_NANO_LLM,
        "execution_mode": execution_mode,
        "provider": f"{search_provider}+{provider}",
        "model": getattr(evaluator, "model", provider),
        "prompt_version": NANO_LLM_PROMPT_VERSION,
        "runtime_seconds": round(runtime_seconds, 2),
        "estimated_cost_usd": round(estimated_cost_usd, 8),
        "results": evaluated_results,
    }


def create_output_file_name(product_id: str, keyword: str) -> str:
    keyword_hash = hashlib.sha256(keyword.encode("utf-8")).hexdigest()[:8]
    return f"{product_id}_{METHOD_SELENIUM_NANO_LLM}_{keyword_hash}.json"


def save_result(output: dict) -> Path:
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    base_name = create_output_file_name(
        product_id=output["product_id"],
        keyword=output["keyword"],
    )
    mode = output.get("execution_mode", "unknown")
    keyword_digest = base_name.rsplit("_", 1)[-1].removesuffix(".json")
    output_file_path = create_unique_result_path(
        directory=RESULTS_DIRECTORY,
        product_id=output["product_id"],
        method=METHOD_SELENIUM_NANO_LLM,
        keyword_digest=keyword_digest,
        execution_mode=mode,
    )
    output_file_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_file_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Selenium + NanoLLM for one keyword.")
    parser.add_argument("--product-id", default="P001")
    parser.add_argument("--keyword", default="Apple iPhone 16 Pro Max 256 GB fiyat")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--provider", choices=["fake", "openrouter"], default="fake")
    parser.add_argument("--search-provider", choices=["selenium", "fake"], default="selenium")
    args = parser.parse_args()

    output = run_selenium_nano_llm(
        product_id=args.product_id,
        keyword=args.keyword,
        max_results=args.max_results,
        provider=args.provider,
        search_provider=args.search_provider,
    )
    output_file_path = save_result(output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Result file saved: {output_file_path}")


if __name__ == "__main__":
    main()
