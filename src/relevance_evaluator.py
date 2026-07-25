"""Nano LLM relevance evaluator for search results."""

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


@dataclass(frozen=True)
class SearchResult:
    domain: str
    url: str
    title: str
    snippet: str


@dataclass(frozen=True)
class RelevanceItem:
    domain: str
    url: str
    title: str
    snippet: str
    predicted_relevant: bool
    relevance_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "predicted_relevant": self.predicted_relevant,
            "relevance_score": self.relevance_score,
        }


def validate_relevance_output(raw_output: Any, expected_count: int) -> list[dict[str, Any]]:
    if isinstance(raw_output, dict) and "results" in raw_output:
        raw_output = raw_output["results"]
    if not isinstance(raw_output, list):
        raise KeywordGenerationError("Relevance output must be a JSON list.")
    if len(raw_output) != expected_count:
        raise KeywordGenerationError(f"Expected {expected_count} relevance rows, got {len(raw_output)}.")

    validated: list[dict[str, Any]] = []
    for index, item in enumerate(raw_output):
        if not isinstance(item, dict):
            raise KeywordGenerationError(f"Relevance row {index} is not an object.")
        predicted = item.get("predicted_relevant")
        score = item.get("relevance_score")
        if not isinstance(predicted, bool):
            raise KeywordGenerationError(f"predicted_relevant at row {index} must be boolean.")
        if not isinstance(score, (int, float)) or not 0 <= float(score) <= 1:
            raise KeywordGenerationError(f"relevance_score at row {index} must be between 0 and 1.")
        validated.append({"predicted_relevant": predicted, "relevance_score": round(float(score), 4)})
    return validated


class FakeRelevanceEvaluator:
    ecommerce_domains = ("trendyol", "hepsiburada", "n11", "amazon", "teknosa", "mediamarkt", "vatan")

    def evaluate(self, keyword: str, results: list[SearchResult]) -> list[RelevanceItem]:
        evaluated = []
        for result in results:
            haystack = " ".join([result.domain, result.title, result.snippet]).lower()
            score = 0.85 if any(domain in haystack for domain in self.ecommerce_domains) else 0.25
            if any(token.lower() in haystack for token in keyword.split()[:3]):
                score = min(1.0, score + 0.1)
            evaluated.append(
                RelevanceItem(
                    domain=result.domain,
                    url=result.url,
                    title=result.title,
                    snippet=result.snippet,
                    predicted_relevant=score >= 0.6,
                    relevance_score=score,
                )
            )
        return evaluated


class OpenRouterRelevanceEvaluator(OpenRouterKeywordClient):
    def evaluate(self, keyword: str, results: list[SearchResult]) -> list[RelevanceItem]:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Evaluate whether search results match a Turkish transactional e-commerce keyword. "
                        "Return JSON only. A relevant result should be a product, category, retailer, or marketplace page."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "keyword": keyword,
                            "results": [result.__dict__ for result in results],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "relevance_evaluation",
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
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise KeywordGenerationError(f"Could not parse relevance structured response: {exc}") from exc

        scores = validate_relevance_output(parsed, len(results))
        return [
            RelevanceItem(
                domain=result.domain,
                url=result.url,
                title=result.title,
                snippet=result.snippet,
                predicted_relevant=score["predicted_relevant"],
                relevance_score=score["relevance_score"],
            )
            for result, score in zip(results, scores)
        ]


def make_result_payload(
    product_id: str,
    keyword: str,
    results: list[SearchResult],
    provider: str = "fake",
    method: str = METHOD_SELENIUM_NANO_LLM,
) -> dict[str, Any]:
    load_env_file()
    if provider == "fake":
        evaluated = FakeRelevanceEvaluator().evaluate(keyword, results)
    elif provider == "openrouter":
        import os

        evaluator = OpenRouterRelevanceEvaluator(
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            model=os.environ.get("NANO_LLM_MODEL", "openrouter/free"),
        )
        evaluated = evaluator.evaluate(keyword, results)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    return {
        "product_id": product_id,
        "keyword": keyword,
        "method": method,
        "runtime_seconds": 0.0,
        "estimated_cost_usd": 0.0,
        "results": [item.to_dict() for item in evaluated],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate search-result relevance for a keyword.")
    parser.add_argument("--provider", choices=["fake", "openrouter"], default="fake")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = make_result_payload(
        product_id="P001",
        keyword="Apple iPhone 16 Pro Max 256 GB fiyat",
        provider=args.provider,
        results=[
            SearchResult(
                domain="trendyol.com",
                url="https://www.trendyol.com/",
                title="iPhone 16 Pro Max 256 GB fiyatları",
                snippet="Apple iPhone modelleri ve kampanyalı fiyat seçenekleri.",
            )
        ],
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
