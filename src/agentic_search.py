"""Minimal agentic web-search planner built on top of Tavily."""

from __future__ import annotations

from tavily_client import make_tavily_client


class AgenticSearch:
    """Plan two intent-focused searches, merge them, and keep five results."""

    def __init__(self, provider: str = "tavily", max_results: int = 5) -> None:
        self.client = make_tavily_client(provider, max_results=max_results)
        self.last_cost_usd = 0.0

    def plan_queries(self, keyword: str) -> list[str]:
        return [keyword, f"{keyword} satın al fiyat karşılaştırma"]

    def search(self, keyword: str) -> list[dict[str, str]]:
        merged: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        search_count = 0
        for query in self.plan_queries(keyword):
            search_count += 1
            for result in self.client.search(query):
                if result["url"] in seen_urls:
                    continue
                seen_urls.add(result["url"])
                merged.append(result)
                if len(merged) >= 5:
                    self.last_cost_usd = float(getattr(self.client, "last_cost_usd", 0.0)) * search_count
                    return merged
        self.last_cost_usd = float(getattr(self.client, "last_cost_usd", 0.0)) * search_count
        return merged[:5]
