"""Agentic web-search planning and tool execution.

The real planner uses an OpenRouter model to choose search queries before the
Tavily tool is called. A deterministic fake planner is kept for API-free tests.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Protocol

from keyword_generator import (
    DEFAULT_MODEL,
    KeywordGenerationError,
    OpenRouterKeywordClient,
    load_api_keys,
    load_env_file,
)
from selenium_collector import (
    collect_search_results,
    create_browser,
)
from tavily_client import make_tavily_client


AGENTIC_PLANNER_PROMPT_VERSION = "agentic-search-plan-v1"
MAX_AGENTIC_QUERIES = 3


logger = logging.getLogger(__name__)


class QueryPlanner(Protocol):
    model: str
    last_cost_usd: float

    def plan(self, keyword: str) -> list[str]:
        """Return search queries selected for the supplied product keyword."""


def _validate_queries(raw_output: Any, keyword: str) -> list[str]:
    if isinstance(raw_output, dict):
        raw_output = raw_output.get("queries")
    if not isinstance(raw_output, list):
        raise KeywordGenerationError("Agentic planner output must contain a queries list.")

    queries: list[str] = []
    seen: set[str] = set()
    for value in raw_output:
        if not isinstance(value, str) or not value.strip():
            raise KeywordGenerationError("Every agentic search query must be a non-empty string.")
        query = value.strip()
        normalized = query.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        queries.append(query)

    if not queries:
        raise KeywordGenerationError("Agentic planner returned no usable search query.")
    if len(queries) > MAX_AGENTIC_QUERIES:
        raise KeywordGenerationError(
            f"Agentic planner returned more than {MAX_AGENTIC_QUERIES} queries."
        )
    # Guard against a planner that "improves" the query into something
    # generic: at least one of the keyword's first two tokens (normally
    # brand + model) must survive into the queries it plans to run.
    if not any(token.casefold() in " ".join(queries).casefold() for token in keyword.split()[:2]):
        raise KeywordGenerationError("Agentic planner queries do not preserve the product identity.")
    return queries


class FakeQueryPlanner:
    """Deterministic planner for unit tests and zero-cost demonstrations."""

    model = "deterministic-fake-planner"
    last_cost_usd = 0.0

    def plan(self, keyword: str) -> list[str]:
        clean_keyword = keyword.strip()
        if not clean_keyword:
            raise KeywordGenerationError("Keyword is required for agentic planning.")
        if "fiyat" in clean_keyword.casefold():
            comparison_query = f"{clean_keyword} en ucuz karşılaştır"
        else:
            comparison_query = f"{clean_keyword} fiyat satın al"
        return [clean_keyword, comparison_query]


class OpenRouterQueryPlanner(OpenRouterKeywordClient):
    """LLM planner that selects transactional web-search queries."""

    def plan(self, keyword: str) -> list[str]:
        clean_keyword = keyword.strip()
        if not clean_keyword:
            raise KeywordGenerationError("Keyword is required for agentic planning.")

        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a web-search planning agent. Choose between one and three "
                        "Turkish search queries for finding the exact smartphone specified "
                        "by the user in retailer, marketplace, listing, or price-comparison "
                        "pages. Preserve the model and storage capacity. Return JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"keyword": clean_keyword}, ensure_ascii=False),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agentic_search_plan",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "queries": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": MAX_AGENTIC_QUERIES,
                                "items": {"type": "string"},
                            }
                        },
                        "required": ["queries"],
                    },
                },
            },
        }
        response_data = self._post_json(payload)
        try:
            content = response_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise KeywordGenerationError(
                f"Could not parse the agentic planner response: {exc}"
            ) from exc
        return _validate_queries(parsed, clean_keyword)


def make_query_planner(provider: str = "openrouter") -> QueryPlanner:
    load_env_file()
    if provider == "fake":
        return FakeQueryPlanner()
    if provider == "openrouter":
        return OpenRouterQueryPlanner(
            api_keys=load_api_keys(),
            model=os.environ.get("AGENTIC_PLANNER_MODEL", DEFAULT_MODEL),
        )
    raise ValueError(f"Unsupported agentic planner provider: {provider}")


class SeleniumSearchClient:
    """Expose Selenium collection as an agent-controlled search tool."""

    last_cost_usd = 0.0

    def __init__(
        self,
        max_results: int = 5,
        search_engine: str = "bing",
    ) -> None:
        self.max_results = min(
            max(1, max_results),
            5,
        )
        self.search_engine = search_engine
        self.browser = None

    def search(
        self,
        keyword: str,
    ) -> list[dict[str, str]]:
        if self.browser is None:
            self.browser = create_browser()

        return collect_search_results(
            browser=self.browser,
            keyword=keyword,
            max_results=self.max_results,
            search_engine=self.search_engine,
        )

    def close(self) -> None:
        if self.browser is not None:
            self.browser.quit()
            self.browser = None


def make_search_client(
    provider: str,
    max_results: int,
    search_engine: str,
):
    if provider == "selenium":
        return SeleniumSearchClient(
            max_results=max_results,
            search_engine=search_engine,
        )
    if provider in {"tavily", "fake"}:
        return make_tavily_client(
            provider,
            max_results=max_results,
        )
    raise ValueError(
        f"Unsupported agentic search provider: {provider}"
    )


class AgenticSearch:
    """Use a planner to choose queries, then execute them with a search tool.

    This is the plan -> search -> evaluate -> aggregate loop from the
    project's background (Yao et al., ReAct): plan_queries() below is the
    "plan" step, search_queries() is "search". The matching langgraph_flow.py
    graph nodes (plan_node/search_node/evaluate_node/aggregate_node) call
    straight into this class -- the "reasoning trace" is just this object's
    state across those four calls, not a separate mechanism.
    """

    def __init__(
        self,
        search_provider: str = "selenium",
        planner_provider: str = "openrouter",
        max_results: int = 5,
        search_engine: str = "bing",
    ) -> None:
        self.search_provider = search_provider
        self.planner_provider = planner_provider
        self.max_results = min(max(1, max_results), 5)
        self.search_engine = search_engine
        self.client = make_search_client(
            provider=search_provider,
            max_results=self.max_results,
            search_engine=search_engine,
        )
        self.planner = make_query_planner(planner_provider)
        self.planner_model = self.planner.model
        self.last_planning_cost_usd = 0.0
        self.last_search_cost_usd = 0.0
        self.last_cost_usd = 0.0
        self.last_queries: list[str] = []
        self.search_errors: list[dict[str, str]] = []

    def plan_queries(self, keyword: str) -> list[str]:
        queries = self.planner.plan(keyword)
        self.last_planning_cost_usd = float(
            getattr(self.planner, "last_cost_usd", 0.0)
        )
        self.last_queries = queries
        return queries

    def search_queries(self, queries: list[str]) -> list[dict[str, str]]:
        merged: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        search_cost = 0.0
        self.search_errors = []

        # One product can plan up to 3 queries; results are merged here and
        # deduplicated by URL (seen_urls) so a product page returned by two
        # different queries is only counted once in the final results list.
        for query in queries:
            try:
                results = self.client.search(query)
            except Exception as exc:
                logger.warning(
                    "Agentic search query failed: %s",
                    exc,
                )
                self.search_errors.append(
                    {
                        "query": query,
                        "error": str(exc),
                    }
                )
                continue
            search_cost += float(getattr(self.client, "last_cost_usd", 0.0))
            for result in results:
                url = result.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                merged.append(result)
                if len(merged) >= self.max_results:
                    break
            if len(merged) >= self.max_results:
                break

        self.last_search_cost_usd = search_cost
        self.last_cost_usd = self.last_planning_cost_usd + search_cost
        if not merged and self.search_errors:
            raise RuntimeError(
                "All agentic search queries failed."
            )
        return merged[: self.max_results]

    def search(self, keyword: str) -> list[dict[str, str]]:
        return self.search_queries(self.plan_queries(keyword))

    def close(self) -> None:
        close_client = getattr(
            self.client,
            "close",
            None,
        )
        if callable(close_client):
            close_client()
