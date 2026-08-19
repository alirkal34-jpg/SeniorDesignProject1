"""Generate transactional e-commerce keywords for processed products.

The module is import-safe: no API call is made unless ``main`` or one of the
generation functions is called explicitly.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter, sleep
from typing import Any, Iterable, Protocol
from urllib import error, request


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = ROOT_DIR / "data" / "processed" / "processed_products.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "generated_keywords.json"
DEFAULT_MODEL = "google/gemma-4-26b-a4b-it:free"
OPENROUTER_BATCH_SIZE = 3
OPENROUTER_MAX_ATTEMPTS = 4
KEYWORD_PROMPT_VERSION = "keyword-generation-v1"


class KeywordGenerationError(RuntimeError):
    """Raised when the LLM response cannot be used safely."""


@dataclass(frozen=True)
class Product:
    product_id: str
    product_name: str
    brand: str
    category: str
    # Structured smartphone datasets carry an explicit model column. The
    # ten-category dataset does not: its product_name already contains brand,
    # model and variant, and the remaining specs live in ``attributes``.
    model: str = ""
    storage_gb: int | None = None
    ram_gb: int | None = None
    color: str | None = None
    category_group: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    def variant_label(self) -> str:
        """Return the shopping-relevant variant, whichever dataset supplied it."""

        label = str(self.attributes.get("variant_label", "") or "").strip()

        if label:
            return label

        if self.storage_gb:
            return f"{self.storage_gb} GB"

        return ""


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
                category_group=str(item.get("category_group") or ""),
                attributes=parse_attributes(item.get("attributes")),
            )
        )
    return products


def parse_attributes(raw_attributes: Any) -> dict[str, Any]:
    """Read the attributes column, which may be a JSON string or a mapping."""

    if isinstance(raw_attributes, dict):
        return raw_attributes

    if isinstance(raw_attributes, str) and raw_attributes.strip():
        try:
            parsed = json.loads(raw_attributes)
        except ValueError:
            return {}

        if isinstance(parsed, dict):
            return parsed

    return {}


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

    model = "deterministic-fake-keyword-generator"
    last_cost_usd = 0.0

    def generate_keywords(self, products: list[Product]) -> list[KeywordItem]:
        raw_items = []
        for product in products:
            raw_items.append(
                {
                    "product_id": product.product_id,
                    "keyword": f"{self.build_name(product)} fiyat",
                }
            )
        return validate_keyword_output(raw_items, {product.product_id for product in products})

    @staticmethod
    def build_name(product: Product) -> str:
        """Assemble the searchable product name for one product.

        Datasets with an explicit model column are composed from brand, model
        and variant, avoiding a repeated brand. Attribute-driven datasets keep
        their product_name, which already contains all three parts.
        """

        model = product.model.strip()

        if not model:
            return product.product_name.strip().replace("+", " Plus")

        variant = product.variant_label()
        variant_segment = f" {variant}" if variant else ""

        if model.casefold().startswith(product.brand.strip().casefold()):
            name = f"{model}{variant_segment}"
        else:
            name = f"{product.brand} {model}{variant_segment}"

        return name.replace("+", " Plus")


def load_api_keys(
    prefix: str = "OPENROUTER_API_KEY",
) -> list[str]:
    """Collect every configured OpenRouter key, in priority order.

    ``OPENROUTER_API_KEY`` is used first, then ``OPENROUTER_API_KEY_2``,
    ``_3`` and so on. Each key carries its own free-tier daily allowance, so
    a second key doubles how much of an experiment fits into one session.
    """

    keys: list[str] = []
    primary = os.environ.get(prefix, "").strip()

    if primary:
        keys.append(primary)

    index = 2

    while True:
        value = os.environ.get(f"{prefix}_{index}", "").strip()

        if not value:
            break

        if value not in keys:
            keys.append(value)

        index += 1

    return keys


def looks_like_daily_limit(detail: str) -> bool:
    """Return True when a 429 means the key's daily allowance is spent.

    A per-minute limit clears by waiting; a daily one does not, so the key is
    set aside for the rest of the run instead of being retried.
    """

    lowered = detail.casefold()

    return any(
        marker in lowered
        for marker in (
            "free-models-per-day",
            "openrouter_free_tier_daily",
            "per-day",
            "daily limit",
        )
    )


class OpenRouterKeywordClient:
    """OpenRouter chat-completions client using JSON-schema structured output."""

    api_url = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        api_keys: list[str] | None = None,
    ) -> None:
        keys: list[str] = []

        if api_key and api_key.strip():
            keys.append(api_key.strip())

        for value in api_keys or []:
            cleaned = str(value).strip()

            if cleaned and cleaned not in keys:
                keys.append(cleaned)

        if not keys:
            raise KeywordGenerationError("OPENROUTER_API_KEY is not set.")

        self.api_keys = keys
        self.api_key = keys[0]
        self._key_index = 0
        # Keys whose daily allowance ran out during this run.
        self.exhausted_keys: set[str] = set()
        self.model = model
        self.last_usage: dict[str, Any] = {}
        self.last_cost_usd = 0.0

    def _switch_to_unused_key(self, tried: set[str]) -> bool:
        """Move to a key not yet tried for this request. False when none left."""

        for _ in range(len(self.api_keys)):
            self._key_index = (self._key_index + 1) % len(self.api_keys)
            candidate = self.api_keys[self._key_index]

            if candidate not in tried and candidate not in self.exhausted_keys:
                self.api_key = candidate
                return True

        return False

    def generate_keywords(self, products: list[Product]) -> list[KeywordItem]:
        expected_ids = {product.product_id for product in products}
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate Turkish transactional e-commerce SEO keywords. "
                        f"Return exactly one keyword object for each of these product IDs: {sorted(expected_ids)}. "
                        "Use every product ID exactly once; never duplicate or omit an ID. "
                        "Return only valid JSON matching the schema. Each keyword must include "
                        "the brand, the product name, the distinguishing variant supplied in "
                        "variant_label (storage, volume, weight, size or edition, depending on the "
                        "category), and buying intent such as fiyat."
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
                                "category": p.category,
                                "category_group": p.category_group,
                                "variant_label": p.variant_label(),
                                "attributes": p.attributes,
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
                                "minItems": len(products),
                                "maxItems": len(products),
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "product_id": {"type": "string", "enum": sorted(expected_ids)},
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

        last_error: KeywordGenerationError | None = None
        for attempt in range(3):
            response_data = self._post_json(payload)
            try:
                content = response_data["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    finish_reason = response_data.get("choices", [{}])[0].get("finish_reason")
                    raise KeywordGenerationError(
                        f"OpenRouter returned empty structured content (finish_reason={finish_reason}, model={self.model})."
                    )
                parsed = json.loads(content)
                return validate_keyword_output(parsed, expected_ids)
            except KeywordGenerationError as exc:
                last_error = exc
            except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                last_error = KeywordGenerationError(f"Could not parse OpenRouter structured response: {exc}")
            if attempt < 2:
                continue
        raise last_error or KeywordGenerationError("OpenRouter returned no usable keyword response.")

    def _send(self, body: bytes) -> dict[str, Any]:
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

        with request.urlopen(req, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            usage = response_data.get("usage", {})
            self.last_usage = usage if isinstance(usage, dict) else {}
            raw_cost = self.last_usage.get(
                "cost",
                self.last_usage.get("total_cost", 0.0),
            )
            try:
                self.last_cost_usd = float(raw_cost or 0.0)
            except (TypeError, ValueError):
                self.last_cost_usd = 0.0
            return response_data

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send one request, rotating keys and backing off on rate limits.

        A 429 is answered by switching to a key that has not been tried for
        this request. Waiting only helps a per-minute limit, whereas another
        key has its own allowance, so rotation is attempted first.
        """

        body = json.dumps(payload).encode("utf-8")
        tried: set[str] = set()
        backoff_attempt = 0

        while True:
            tried.add(self.api_key)

            try:
                return self._send(body)
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")

                if exc.code != 429:
                    raise KeywordGenerationError(
                        f"OpenRouter API error {exc.code}: {detail}"
                    ) from exc

                if looks_like_daily_limit(detail):
                    self.exhausted_keys.add(self.api_key)

                if self._switch_to_unused_key(tried):
                    continue

                if backoff_attempt >= OPENROUTER_MAX_ATTEMPTS - 1:
                    raise KeywordGenerationError(
                        f"OpenRouter API error {exc.code}: {detail}"
                    ) from exc

                retry_after = exc.headers.get("Retry-After", "")

                try:
                    requested_delay = float(retry_after)
                except (TypeError, ValueError):
                    requested_delay = 0.0

                sleep(max(requested_delay, float(2**backoff_attempt)))
                backoff_attempt += 1
                # After waiting, a per-minute limit may have cleared, so keys
                # become eligible again unless their daily quota is spent.
                tried = set()
            except error.URLError as exc:
                raise KeywordGenerationError(
                    f"OpenRouter request failed: {exc.reason}"
                ) from exc


def make_client(provider: str) -> KeywordClient:
    load_env_file()
    if provider == "fake":
        return FakeKeywordClient()
    if provider == "openrouter":
        return OpenRouterKeywordClient(
            api_keys=load_api_keys(),
            model=os.environ.get("NANO_LLM_MODEL", DEFAULT_MODEL),
        )
    raise ValueError(f"Unsupported provider: {provider}")


def generate_keywords(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    limit: int = 3,
    provider: str = "openrouter",
) -> list[KeywordItem]:
    started_at = perf_counter()
    products = select_products(load_products(input_path), limit=limit)
    client = make_client(provider)
    total_cost_usd = 0.0
    if provider == "openrouter":
        # Google structured-output providers reject a single schema with a
        # large product_id enum, so keep each request at the verified size.
        keywords = []
        for start in range(0, len(products), OPENROUTER_BATCH_SIZE):
            batch = products[start : start + OPENROUTER_BATCH_SIZE]
            keywords.extend(client.generate_keywords(batch))
            total_cost_usd += float(getattr(client, "last_cost_usd", 0.0))
    else:
        keywords = client.generate_keywords(products)
        total_cost_usd = float(getattr(client, "last_cost_usd", 0.0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([item.to_dict() for item in keywords], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata_path = output_path.with_name(f"{output_path.stem}.metadata.json")
    metadata_path.write_text(
        json.dumps(
            {
                "execution_mode": "fake" if provider == "fake" else "live",
                "provider": provider,
                "model": getattr(client, "model", provider),
                "prompt_version": KEYWORD_PROMPT_VERSION,
                "product_count": len(keywords),
                "runtime_seconds": round(perf_counter() - started_at, 2),
                "estimated_cost_usd": round(total_cost_usd, 8),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
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
