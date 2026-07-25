"""Generate transactional e-commerce keywords for processed products.

The module is import-safe: no API call is made unless ``main`` or one of the
generation functions is called explicitly.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable, Protocol
from urllib import error, request


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = ROOT_DIR / "data" / "processed" / "processed_products.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "generated_keywords.json"
DEFAULT_MODEL = "google/gemini-2.5-flash-lite"


class KeywordGenerationError(RuntimeError):
    """Raised when the LLM response cannot be used safely."""


@dataclass(frozen=True)
class Product:
    product_id: str
    product_name: str
    brand: str
    model: str
    category: str
    storage_gb: int | None = None
    ram_gb: int | None = None
    color: str | None = None


@dataclass(frozen=True)
class KeywordItem:
    product_id: str
    keyword: str

    def to_dict(self) -> dict[str, str]:
        return {"product_id": self.product_id, "keyword": self.keyword}


class KeywordClient(Protocol):
    def generate_keywords(self, products: list[Product]) -> list[KeywordItem]:
        """Generate one keyword per product."""


def load_env_file(path: Path = ROOT_DIR / ".env") -> None:
    """Load simple KEY=VALUE pairs without requiring python-dotenv at runtime."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_products(path: Path = DEFAULT_INPUT_PATH) -> list[Product]:
    raw_products = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_products, list):
        raise ValueError(f"Expected a product list in {path}")

    products: list[Product] = []
    for item in raw_products:
        products.append(
            Product(
                product_id=str(item["product_id"]),
                product_name=str(item.get("product_name") or ""),
                brand=str(item.get("brand") or ""),
                model=str(item.get("model") or ""),
                category=str(item.get("category") or ""),
                storage_gb=item.get("storage_gb"),
                ram_gb=item.get("ram_gb"),
                color=item.get("color"),
            )
        )
    return products


def select_products(products: Iterable[Product], limit: int = 3) -> list[Product]:
    selected = []
    for product in products:
        selected.append(product)
        if len(selected) >= limit:
            break
    return selected


def validate_keyword_output(raw_output: Any, expected_ids: set[str]) -> list[KeywordItem]:
    """Validate structured keyword output with the same contract as Pydantic models."""
    if isinstance(raw_output, dict) and "keywords" in raw_output:
        raw_output = raw_output["keywords"]
    if not isinstance(raw_output, list):
        raise KeywordGenerationError("LLM output must be a JSON list of keyword objects.")

    items: list[KeywordItem] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_output):
        if not isinstance(item, dict):
            raise KeywordGenerationError(f"Keyword item at index {index} is not an object.")
        product_id = item.get("product_id")
        keyword = item.get("keyword")
        if not isinstance(product_id, str) or not product_id.strip():
            raise KeywordGenerationError(f"Keyword item at index {index} has an invalid product_id.")
        if product_id not in expected_ids:
            raise KeywordGenerationError(f"Unexpected product_id in LLM output: {product_id}")
        if product_id in seen_ids:
            raise KeywordGenerationError(f"Duplicate product_id in LLM output: {product_id}")
        if not isinstance(keyword, str) or len(keyword.strip()) < 5:
            raise KeywordGenerationError(f"Keyword for {product_id} is missing or too short.")
        if any(intent in keyword.lower() for intent in ("nasıl", "nedir", "yorum", "blog")):
            raise KeywordGenerationError(f"Keyword for {product_id} does not look transactional: {keyword}")
        seen_ids.add(product_id)
        items.append(KeywordItem(product_id=product_id, keyword=keyword.strip()))

    missing_ids = expected_ids - seen_ids
    if missing_ids:
        raise KeywordGenerationError(f"LLM output is missing product_id values: {sorted(missing_ids)}")
    return items


class FakeKeywordClient:
    """Deterministic local client for tests and zero-cost sample output."""

    def generate_keywords(self, products: list[Product]) -> list[KeywordItem]:
        raw_items = []
        for product in products:
            storage = f" {product.storage_gb} GB" if product.storage_gb else ""
            name = f"{product.brand} {product.model}{storage}".replace("+", " Plus")
            raw_items.append({"product_id": product.product_id, "keyword": f"{name} fiyat"})
        return validate_keyword_output(raw_items, {product.product_id for product in products})


class OpenRouterKeywordClient:
    """OpenRouter chat-completions client using JSON-schema structured output."""

    api_url = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise KeywordGenerationError("OPENROUTER_API_KEY is not set.")
        self.api_key = api_key
        self.model = model
        self.last_usage: dict[str, Any] = {}
        self.last_cost_usd = 0.0

    def generate_keywords(self, products: list[Product]) -> list[KeywordItem]:
        expected_ids = {product.product_id for product in products}
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate Turkish transactional e-commerce SEO keywords. "
                        "Return only valid JSON matching the schema. Each keyword must include "
                        "brand, model, important variant such as storage, and buying intent such as fiyat."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        [
                            {
                                "product_id": p.product_id,
                                "product_name": p.product_name,
                                "brand": p.brand,
                                "model": p.model,
                                "storage_gb": p.storage_gb,
                                "ram_gb": p.ram_gb,
                                "color": p.color,
                            }
                            for p in products
                        ],
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "keyword_generation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "keywords": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "product_id": {"type": "string"},
                                        "keyword": {"type": "string"},
                                    },
                                    "required": ["product_id", "keyword"],
                                },
                            }
                        },
                        "required": ["keywords"],
                    },
                },
            },
        }

        response_data = self._post_json(payload)
        try:
            content = response_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise KeywordGenerationError(f"Could not parse OpenRouter structured response: {exc}") from exc
        return validate_keyword_output(parsed, expected_ids)

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.api_url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/alirkal34-jpg/SeniorDesignProject1",
                "X-Title": "Senior Design Keyword Generator",
            },
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                usage = response_data.get("usage", {})
                self.last_usage = usage if isinstance(usage, dict) else {}
                raw_cost = self.last_usage.get("cost", self.last_usage.get("total_cost", 0.0))
                try:
                    self.last_cost_usd = float(raw_cost or 0.0)
                except (TypeError, ValueError):
                    self.last_cost_usd = 0.0
                return response_data
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise KeywordGenerationError(f"OpenRouter API error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise KeywordGenerationError(f"OpenRouter request failed: {exc.reason}") from exc


def make_client(provider: str) -> KeywordClient:
    load_env_file()
    if provider == "fake":
        return FakeKeywordClient()
    if provider == "openrouter":
        return OpenRouterKeywordClient(
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            model=os.environ.get("NANO_LLM_MODEL", DEFAULT_MODEL),
        )
    raise ValueError(f"Unsupported provider: {provider}")


def generate_keywords(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    limit: int = 3,
    provider: str = "openrouter",
) -> list[KeywordItem]:
    products = select_products(load_products(input_path), limit=limit)
    client = make_client(provider)
    keywords = client.generate_keywords(products)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([item.to_dict() for item in keywords], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return keywords


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate structured transactional product keywords.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--provider", choices=["openrouter", "fake"], default="openrouter")
    args = parser.parse_args()

    started_at = perf_counter()
    keywords = generate_keywords(
        input_path=args.input,
        output_path=args.output,
        limit=args.limit,
        provider=args.provider,
    )
    print(json.dumps([item.to_dict() for item in keywords], ensure_ascii=False, indent=2))
    elapsed = perf_counter() - started_at
    print(f"runtime_seconds={elapsed:.2f}")


if __name__ == "__main__":
    main()
