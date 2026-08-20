"""Nano LLM evaluator for search-result relevance.

The real provider is OpenRouter. A deterministic fake provider is included so
the evaluator can be tested without API calls.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keyword_generator import (
    DEFAULT_MODEL,
    KeywordGenerationError,
    OpenRouterKeywordClient,
    load_api_keys,
    load_env_file,
)


METHOD_TAVILY_LLM = "tavily_llm"
METHOD_AGENTIC_SEARCH = "agentic_search"
METHOD_SELENIUM_NANO_LLM = "selenium_nano_llm"
METHOD_SELENIUM_RULE_BASED = "selenium_rule_based"
NANO_LLM_PROMPT_VERSION = "relevance-v1"
NANO_LLM_PROMPT_VERSION_ALIGNED = "relevance-v2-aligned"


def build_relevance_prompt_v1(result_count: int) -> str:
    """The prompt every reported run was produced with.

    It calls a category page relevant, which the human labeling rule does
    not. Kept verbatim so the frozen results stay reproducible.
    """

    return (
        "Evaluate whether each Google search result is relevant for a Turkish "
        "transactional e-commerce product keyword. Relevant means product, "
        f"category, marketplace, retailer, or price-comparison intent. Return exactly {result_count} "
        "evaluation objects in the same order as the input results. Return JSON only."
    )


def build_relevance_prompt_v2_aligned(result_count: int) -> str:
    """The same criterion the human reviewers were given, in prompt form.

    Written once from the workbook's instruction sheet and not tuned against
    the labels: adjusting it until the score improves would be fitting the
    prompt to the test set and would void the comparison it exists to make.
    """

    return (
        "You judge Turkish e-commerce search results for a transactional "
        "product keyword.\n"
        "A result is RELEVANT only when BOTH conditions hold:\n"
        "  1. The page is the product named in the keyword, including the "
        "variant (storage, volume, weight, size, edition) when the keyword "
        "states one.\n"
        "  2. The page has transactional purpose: a retailer product page, a "
        "marketplace listing, a classified listing, or a price-comparison "
        "page.\n"
        "A result is IRRELEVANT when any of these hold:\n"
        "  - it is a different product or a different variant,\n"
        "  - it is an accessory for the product rather than the product,\n"
        "  - it is a news article, a blog post, a review, or a forum thread,\n"
        "  - it is a category or search page that does not reach the "
        "product.\n"
        "Being out of stock does NOT make a page irrelevant.\n"
        f"Return exactly {result_count} evaluation objects in the same order "
        "as the input results. Return JSON only."
    )
EVALUATION_MAX_ATTEMPTS = 3

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NanoLLMEvaluation:
    predicted_relevant: bool
    relevance_score: float


class FakeNanoLLMEvaluator:
    # Substrings that mark a result as e-commerce for the deterministic
    # scorer. The list covers every category group in the taxonomy, not only
    # consumer electronics. Ambiguous short names are written as full domains
    # so ordinary words cannot match them by accident.
    ecommerce_domains = (
        "a101",
        "akakce",
        "amazon",
        "bauhaus",
        "bkmkitap",
        "boyner",
        "carrefoursa",
        "ciceksepeti",
        "cimri",
        "decathlon",
        "defacto",
        "dr.com.tr",
        "ebebek",
        "flo.com.tr",
        "getir",
        "gratis",
        "hepsiburada",
        "idefix",
        "ikea",
        "kitapyurdu",
        "koctas",
        "koton",
        "lcw.com",
        "mediamarkt",
        "migros",
        "n11",
        "pazarama",
        "petlebi",
        "rossmann",
        "sokmarket",
        "teknosa",
        "tekzen",
        "toyzzshop",
        "trendyol",
        "vatan",
        "watsons",
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

    # Which criterion the model is asked to apply. The default reproduces
    # every reported run; an experiment can swap in another builder without
    # touching the evaluation path itself.
    prompt_builder = staticmethod(build_relevance_prompt_v1)
    prompt_version = NANO_LLM_PROMPT_VERSION

    # Optional OpenRouter provider routing, e.g. {"order": ["Google"],
    # "allow_fallbacks": False}. The default sends nothing, so the reported
    # runs keep their original routing. Pinning matters when a rerun has to
    # stay on the same provider as the results it will be compared against.
    provider_routing: dict[str, Any] | None = None

    # Optional cap on the answer length. Without one the provider reserves
    # credit for the model's whole context window, which can refuse a request
    # the actual answer would easily afford: five evaluation objects run well
    # under a thousand tokens. None keeps the reported runs' behaviour.
    max_output_tokens: int | None = None

    def evaluate_results(self, keyword: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": type(self).prompt_builder(len(results)),
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
                                "minItems": len(results),
                                "maxItems": len(results),
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

        if type(self).provider_routing is not None:
            payload["provider"] = type(self).provider_routing

        if type(self).max_output_tokens is not None:
            payload["max_tokens"] = type(self).max_output_tokens

        # The free model does not always honour its own JSON schema, so an
        # unusable answer is retried instead of failing the whole experiment.
        # This mirrors the retry the keyword client already performs.
        last_error: KeywordGenerationError | None = None
        evaluations: list[NanoLLMEvaluation] | None = None

        for attempt in range(EVALUATION_MAX_ATTEMPTS):
            response_data = self._post_json(payload)
            try:
                content = response_data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                evaluations = validate_evaluation_output(
                    parsed,
                    expected_count=len(results),
                )
                break
            except KeywordGenerationError as exc:
                last_error = exc
            except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                last_error = KeywordGenerationError(
                    f"Could not parse NanoLLM evaluator response: {exc}"
                )

            if attempt < EVALUATION_MAX_ATTEMPTS - 1:
                logger.warning(
                    "NanoLLM evaluator attempt %d/%d failed: %s",
                    attempt + 1,
                    EVALUATION_MAX_ATTEMPTS,
                    last_error,
                )

        if evaluations is None:
            raise last_error or KeywordGenerationError(
                "NanoLLM evaluator returned no usable response."
            )

        evaluated_results = []
        for result, evaluation in zip(results, evaluations):
            evaluated = result.copy()
            evaluated["predicted_relevant"] = evaluation.predicted_relevant
            evaluated["relevance_score"] = evaluation.relevance_score
            evaluated_results.append(evaluated)
        return evaluated_results


def coerce_relevance_flag(value: Any) -> bool | None:
    """Normalize a relevance flag, or return None when it is not a flag.

    The configured free model occasionally answers with the string "true" or
    the integer 1 even though the JSON schema declares a boolean. Those are
    unambiguous spellings of the same answer, so they are accepted. Anything
    genuinely ambiguous - "maybe", 0.5, null - is still rejected.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, int) and value in (0, 1):
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().casefold()

        if normalized in {"true", "1"}:
            return True

        if normalized in {"false", "0"}:
            return False

    return None


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
        predicted_relevant = coerce_relevance_flag(
            item.get("predicted_relevant")
        )
        relevance_score = item.get("relevance_score")
        if predicted_relevant is None:
            raise KeywordGenerationError(
                f"predicted_relevant at row {index} must be boolean, got "
                f"{item.get('predicted_relevant')!r}."
            )
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
            api_keys=load_api_keys(),
            model=os.environ.get("NANO_LLM_MODEL", DEFAULT_MODEL),
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
