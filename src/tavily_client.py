"""Small Tavily search client with a deterministic fake provider for tests."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error, request
from urllib.parse import urlparse

from keyword_generator import KeywordGenerationError, load_env_file


TAVILY_API_URL = "https://api.tavily.com/search"


@dataclass(frozen=True)
class TavilySearchResult:
    domain: str
    url: str
    title: str
    snippet: str

    def to_dict(self) -> dict[str, str]:
        return {
            "domain": self.domain,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
        }


def _domain_from_url(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    return domain[4:] if domain.startswith("www.") else domain


class TavilySearchClient:
    def __init__(self, api_key: str | None = None, max_results: int = 5) -> None:
        load_env_file()
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY", "")
        if not self.api_key:
            raise KeywordGenerationError("TAVILY_API_KEY is not set.")
        self.max_results = min(max(1, max_results), 5)
        self.last_cost_usd = 0.0

    def search(self, keyword: str) -> list[dict[str, str]]:
        payload = {
            "api_key": self.api_key,
            "query": keyword,
            "search_depth": "basic",
            "max_results": self.max_results,
            "include_answer": False,
            "include_raw_content": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            TAVILY_API_URL,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise KeywordGenerationError(f"Tavily API error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise KeywordGenerationError(f"Tavily request failed: {exc.reason}") from exc

        raw_results = data.get("results", [])
        if not isinstance(raw_results, list):
            raise KeywordGenerationError("Tavily response results must be a list.")
        # Unlike OpenRouter, Tavily's response has no per-call cost field, so
        # this is a configured per-search price (TAVILY_COST_PER_SEARCH_USD),
        # not a value read back from the API. Defaults to 0.0 if unset -- the
        # reported cost totals include Tavily runs only if this was set.
        try:
            self.last_cost_usd = float(os.environ.get("TAVILY_COST_PER_SEARCH_USD", "0"))
        except ValueError:
            self.last_cost_usd = 0.0
        normalized: list[dict[str, str]] = []
        for item in raw_results[: self.max_results]:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            result = TavilySearchResult(
                domain=_domain_from_url(str(item.get("url", ""))),
                url=str(item.get("url", "")),
                title=str(item.get("title", "")),
                snippet=str(item.get("content", item.get("snippet", ""))),
            )
            normalized.append(result.to_dict())
        return normalized


class FakeTavilySearchClient:
    last_cost_usd = 0.0

    def search(self, keyword: str) -> list[dict[str, str]]:
        encoded = keyword.replace(" ", "-")
        return [
            {
                "domain": "trendyol.com",
                "url": f"https://www.trendyol.com/{encoded}",
                "title": f"{keyword} fiyat ve satın alma",
                "snippet": f"{keyword} için mağaza fiyatları ve satın alma seçenekleri.",
            },
            {
                "domain": "teknoseyir.com",
                "url": f"https://teknoseyir.com/{encoded}",
                "title": f"{keyword} inceleme",
                "snippet": "Ürün özellikleri ve kullanıcı değerlendirmeleri.",
            },
        ]


def make_tavily_client(provider: str = "tavily", max_results: int = 5):
    if provider == "fake":
        return FakeTavilySearchClient()
    if provider == "tavily":
        return TavilySearchClient(max_results=max_results)
    raise ValueError(f"Unsupported Tavily provider: {provider}")
