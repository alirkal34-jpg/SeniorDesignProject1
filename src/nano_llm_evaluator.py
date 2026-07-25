"""Nano LLM evaluator for search-result relevance.

The real provider is OpenRouter. A deterministic fake provider is included so
the evaluator can be tested without API calls.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keyword_generator import KeywordGenerationError, OpenRouterKeywordClient, load_env_file


METHOD_TAVILY_LLM = "tavily_llm"
METHOD_AGENTIC_SEARCH = "agentic_search"
METHOD_SELENIUM_NANO_LLM = "selenium_nano_llm"
METHOD_SELENIUM_RULE_BASED = "selenium_rule_based"
NANO_LLM_PROMPT_VERSION = "relevance-v1"


@dataclass(frozen=True)
class NanoLLMEvaluation:
    predicted_relevant: bool
    relevance_score: float


class FakeNanoLLMEvaluator:
    ecommerce_domains = (
        "akakce",
        "amazon",
        "cimri",
        "hepsiburada",
        "mediamarkt",
        "n11",
        "teknosa",
        "trendyol",
        "vatan",
    )

    def evaluate_result(self, keyword: str, result: dict[str, Any]) -> NanoLLMEvaluation:
        text = " ".join(
            [
                str(result.get("domain", "")),
                str(result.get("title", "")),
                str(result.get("snippet", "")),
            ]
        ).lower()
        score = 0.25
        if any(domain in text for domain in self.ecommerce_domains):
            score = 0.82
        keyword_tokens = [token.lower() for token in keyword.split() if len(token) >= 3]
        overlap = sum(1 for token in keyword_tokens[:5] if token in text)
        score = min(1.0, score + (overlap * 0.03))
        return NanoLLMEvaluation(
            predicted_relevant=score >= 0.60,
            relevance_score=round(score, 4),
        )

    def evaluate_results(self, keyword: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        evaluated_results = []
        for result in results:
            evaluation = self.evaluate_result(keyword, result)
            evaluated = result.copy()
            evaluated["predicted_relevant"] = evaluation.predicted_relevant
            evaluated["relevance_score"] = evaluation.relevance_score
            evaluated_results.append(evaluated)
        return evaluated_results


class OpenRouterNanoLLMEvaluator(OpenRouterKeywordClient):
    """OpenRouter evaluator returning strict predicted_relevant/relevance_score data."""

    def evaluate_results(self, keyword: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Evaluate whether each Google search result is relevant for a Turkish "
                        "transactional e-commerce product keyword. Relevant means product, "
                        "category, marketplace, retailer, or price-comparison intent. Return JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "keyword": keyword,
                            "results": [
                                {
                                    "domain": result.get("domain", ""),
                                    "url": result.get("url", ""),
                                    "title": result.get("title", ""),
                                    "snippet": result.get("snippet", ""),
                                }
                                for result in results
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "nano_llm_relevance_evaluation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "results": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "predicted_relevant": {"type": "boolean"},
                                        "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
                                    },
                                    "required": ["predicted_relevant", "relevance_score"],
                                },
                            }
                        },
                        "required": ["results"],
                    },
                },
            },
        }

        response_data = self._post_json(payload)
        try:
            content = response_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            evaluations = validate_evaluation_output(parsed, expected_count=len(results))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise KeywordGenerationError(f"Could not parse NanoLLM evaluator response: {exc}") from exc

        evaluated_results = []
        for result, evaluation in zip(results, evaluations):
            evaluated = result.copy()
            evaluated["predicted_relevant"] = evaluation.predicted_relevant
            evaluated["relevance_score"] = evaluation.relevance_score
            evaluated_results.append(evaluated)
        return evaluated_results


def validate_evaluation_output(raw_output: Any, expected_count: int) -> list[NanoLLMEvaluation]:
    if isinstance(raw_output, dict) and "results" in raw_output:
        raw_output = raw_output["results"]
    if not isinstance(raw_output, list):
        raise KeywordGenerationError("NanoLLM evaluator output must be a JSON list.")
    if len(raw_output) != expected_count:
        raise KeywordGenerationError(f"Expected {expected_count} evaluation rows, got {len(raw_output)}.")

    evaluations = []
    for index, item in enumerate(raw_output):
        if not isinstance(item, dict):
            raise KeywordGenerationError(f"Evaluation row {index} must be an object.")
        predicted_relevant = item.get("predicted_relevant")
        relevance_score = item.get("relevance_score")
        if not isinstance(predicted_relevant, bool):
            raise KeywordGenerationError(f"predicted_relevant at row {index} must be boolean.")
        if not isinstance(relevance_score, (int, float)) or not 0 <= float(relevance_score) <= 1:
            raise KeywordGenerationError(f"relevance_score at row {index} must be between 0 and 1.")
        evaluations.append(
            NanoLLMEvaluation(
                predicted_relevant=predicted_relevant,
                relevance_score=round(float(relevance_score), 4),
            )
        )
    return evaluations


def make_nano_llm_evaluator(provider: str = "fake"):
    load_env_file()
    if provider == "fake":
        return FakeNanoLLMEvaluator()
    if provider == "openrouter":
        import os

        return OpenRouterNanoLLMEvaluator(
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            model=os.environ.get("NANO_LLM_MODEL", "google/gemini-2.5-flash-lite"),
        )
    raise ValueError(f"Unsupported provider: {provider}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test NanoLLM relevance evaluation with 3 sample results.")
    parser.add_argument("--provider", choices=["fake", "openrouter"], default="fake")
    args = parser.parse_args()

    sample_results = [
        {
            "domain": "trendyol.com",
            "url": "https://www.trendyol.com/apple-iphone-16-pro-max",
            "title": "Apple iPhone 16 Pro Max 256 GB fiyatları",
            "snippet": "Kampanyalı fiyatlar ve satın alma seçenekleri.",
        },
        {
            "domain": "teknoseyir.com",
            "url": "https://teknoseyir.com/iphone-16-pro-max-inceleme",
            "title": "iPhone 16 Pro Max inceleme",
            "snippet": "Kamera, pil ve performans değerlendirmesi.",
        },
        {
            "domain": "akakce.com",
            "url": "https://www.akakce.com/cep-telefonu/apple-iphone-16-pro-max",
            "title": "iPhone 16 Pro Max fiyat karşılaştırması",
            "snippet": "Mağaza fiyatlarını karşılaştırın.",
        },
    ]
    evaluator = make_nano_llm_evaluator(provider=args.provider)
    evaluated = evaluator.evaluate_results("Apple iPhone 16 Pro Max 256 GB fiyat", sample_results)
    print(json.dumps(evaluated, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
