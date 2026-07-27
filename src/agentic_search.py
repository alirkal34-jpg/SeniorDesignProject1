"""Agentic web-search planner supporting intent-guided multi-query search strategies."""

from __future__ import annotations

from typing import Any
from tavily_client import make_tavily_client


class AgenticSearch:
    """Plan intent-focused searches (base product, price comparison, retailer), merge, deduplicate, and keep 5 results."""

    def __init__(self, provider: str = "tavily", max_results: int = 5) -> None:
        self.provider = provider
        self.max_results = max_results
        self.client = make_tavily_client(provider, max_results=max_results)
        self.last_cost_usd = 0.0

    def plan_queries(self, keyword: str) -> list[str]:
        """Generate targeted search queries for transactional e-commerce discovery."""
        clean_keyword = keyword.strip()
        # Intent 1: Direct keyword search
        query1 = clean_keyword
        # Intent 2: Explicit transactional & comparison intent search
        if "fiyat" not in clean_keyword.lower():
            query2 = f"{clean_keyword} fiyat satın al"
        else:
            query2 = f"{clean_keyword} en ucuz fiyat karşılaştır"
        return [query1, query2]

    def search(self, keyword: str) -> list[dict[str, str]]:
        merged: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        search_count = 0

        queries = self.plan_queries(keyword)
        for query in queries:
            search_count += 1
            results = self.client.search(query)
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

        unit_cost = float(getattr(self.client, "last_cost_usd", 0.0))
        self.last_cost_usd = unit_cost * search_count
        return merged[: self.max_results]
