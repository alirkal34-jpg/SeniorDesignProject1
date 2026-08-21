"""Build the multi-category product dataset.

The advisor asked for roughly fifty products in each of ten e-commerce category
groups, collected from sites such as Cimri, Akakce, Hepsiburada and Trendyol.
This module provides two acquisition paths behind one interface:

``selenium``
    The real path. Selenium loads a category listing page and BeautifulSoup4
    parses the product cards. Listing markup changes often, so this path
    verifies what it extracted and fails loudly instead of writing empty rows.

``offline``
    The API-free path used by unit tests and by the committed snapshot. It
    produces deterministic **synthetic** products from ``product_catalog``.

Every dataset written here is accompanied by a metadata file recording which
path produced it. A dataset built with the offline path carries
``acquisition_mode: synthetic`` and must never be reported as scraped market
data.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, sleep
from typing import Any, Protocol, Sequence
from urllib.parse import quote_plus, urljoin

from category_taxonomy import (
    CategoryGroup,
    DEFAULT_TAXONOMY_FILE,
    load_category_groups,
)
from product_catalog import CatalogProduct, generate_category_products


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "candidate_products_multicategory.csv"
)

DATASET_COLUMNS = (
    "product_id",
    "product_name",
    "brand",
    "category",
    "category_group",
    "source_url",
    "attributes",
)

ACQUISITION_MODE_SYNTHETIC = "synthetic"
ACQUISITION_MODE_SCRAPED = "scraped"


class ScraperError(RuntimeError):
    """Raised when a category cannot be collected."""


class PartialDatasetError(ScraperError):
    """Raised when only some categories reached their target.

    Carries the rows that were collected so a resumable run can still save
    its progress instead of throwing away a session's work.
    """

    def __init__(
        self,
        message: str,
        rows: list[dict[str, Any]],
        collected_this_run: int = 0,
    ) -> None:
        super().__init__(message)
        self.rows = rows
        self.collected_this_run = collected_this_run


class BotChallengeError(ScraperError):
    """Raised when the site answers with a bot-protection interstitial.

    This is a rate limit, not a permanent block. The scraper slows down and
    retries a few times, then stops. No attempt is made to defeat the
    protection: that is a security control and working around it is out of
    scope for this project.
    """


# Text that only appears on a bot-protection interstitial. Checked against the
# page a challenged request actually returned, which is roughly 27 KB instead
# of the 900 KB of a real listing page.
BOT_CHALLENGE_MARKERS = (
    "güvenlik doğrulaması",
    "bir dakika lütfen",
    "checking your browser",
    "just a moment",
    "enable javascript and cookies to continue",
    "you have been blocked",
    "attention required",
    "cf-browser-verification",
)


def looks_like_bot_challenge(html: str) -> bool:
    """Return True when the response is a bot-protection page, not a listing."""

    lowered = html.casefold()

    return any(marker in lowered for marker in BOT_CHALLENGE_MARKERS)


class CatalogProvider(Protocol):
    """Supplies products for one category group."""

    acquisition_mode: str
    source_name: str

    def collect(
        self,
        group: CategoryGroup,
        limit: int,
    ) -> list[CatalogProduct]:
        """Return up to ``limit`` products for the category group."""


# ==================================================
# Offline provider
# ==================================================

class OfflineCatalogProvider:
    """Deterministic, network-free products for tests and the snapshot."""

    acquisition_mode = ACQUISITION_MODE_SYNTHETIC
    source_name = "offline-product-catalog"

    def collect(
        self,
        group: CategoryGroup,
        limit: int,
    ) -> list[CatalogProduct]:
        return generate_category_products(
            category_group=group.category_group,
            limit=limit,
        )


# ==================================================
# Live provider
# ==================================================

# Search terms per category group. Listing pages are reached by searching so
# the scraper does not depend on any site's category tree staying stable.
#
# Several terms per category are needed for two reasons: a listing page returns
# about thirty products, and one term cannot represent a group as broad as
# "Ev, Yaşam, Ofis, Kırtasiye". Results are merged and deduplicated.
SEARCH_TERMS: dict[str, tuple[str, ...]] = {
    "elektronik_cep_telefonu": (
        "cep telefonu",
        "tablet",
        "bluetooth kulaklık",
        "akıllı saat",
    ),
    "ev_yasam_ofis_kirtasiye": (
        "tencere seti",
        "nevresim takımı",
        "kalem seti",
        "ofis sandalyesi",
    ),
    "anne_bebek_oyuncak": (
        "bebek bezi",
        "biberon",
        "lego",
        "bebek arabası",
    ),
    # Fashion listings often state no measurable spec, so this group needs
    # extra terms whose products carry a model code or a size.
    "saat_moda_taki_ayakkabi": (
        "kol saati",
        "spor ayakkabı",
        "kadın çanta",
        "güneş gözlüğü",
        "akıllı bileklik",
        "erkek ayakkabı",
        "cüzdan",
        "altın kolye",
        "gümüş yüzük",
        "sırt çantası",
    ),
    "kitap_muzik_hobi": (
        "roman kitap",
        "puzzle",
        "gitar",
        "boya seti",
    ),
    "spor_outdoor": (
        "kamp çadırı",
        "koşu ayakkabısı",
        "dambıl",
        "bisiklet",
        "uyku tulumu",
        "yoga matı",
    ),
    "saglik_bakim_kozmetik": (
        "şampuan",
        "yüz kremi",
        "parfüm",
        "diş fırçası",
    ),
    "oto_bahce_yapi_market": (
        "akülü vidalama",
        "motor yağı",
        "çim biçme makinesi",
        "silecek",
    ),
    "petshop": (
        "kedi maması",
        "köpek maması",
        "kedi kumu",
        "köpek tasması",
    ),
    "supermarket": (
        "bisküvi",
        "çikolata",
        "deterjan",
        "kahve",
    ),
}

# Number + unit patterns that appear in Turkish listing titles, used to recover
# the variant label ("256 GB", "10 kg", "500 ml", "42 Numara") from a product
# name. Ordered so longer units are matched before their prefixes.
VARIANT_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(TB|GB|MB|ML|LT|L|KG|GR|G|CM|MM|V|W|"
    r"NUMARA|PARÇA|ADET|YAŞ|AY|KİŞİLİK|KISILIK|KİTAP|KITAP|AYAR|"
    r"'?L[İIıi]|'?LU|'?LÜ|'?LI)\b",
    re.IGNORECASE,
)

UNIT_DISPLAY = {
    "TB": "TB",
    "GB": "GB",
    "MB": "MB",
    "ML": "ml",
    "LT": "lt",
    "L": "L",
    "KG": "kg",
    "GR": "gr",
    "G": "g",
    "CM": "cm",
    "MM": "mm",
    "V": "V",
    "W": "W",
    "NUMARA": "Numara",
    "PARÇA": "Parça",
    "ADET": "Adet",
    "YAŞ": "Yaş",
    "AY": "Ay",
    "AYAR": "Ayar",
    "KİŞİLİK": "Kişilik",
    "KISILIK": "Kişilik",
    "KİTAP": "Kitap",
    "KITAP": "Kitap",
    # Turkish "-li" suffix counts: 5'li, 12'li, 3'lü ...
    "'Lİ": "'li",
    "'LI": "'li",
    "'LU": "'lu",
    "'LÜ": "'lü",
    "Lİ": "'li",
    "LI": "'li",
    "LU": "'lu",
    "LÜ": "'lü",
}


# A product can be distinguished by something other than a measurement. Tents
# and furniture state dimensions, and watches state a manufacturer model code,
# which is exactly the spec a shopper searches for.
DIMENSION_PATTERN = re.compile(
    r"\b(\d{1,4})\s*[x×]\s*(\d{1,4})(?:\s*[x×]\s*(\d{1,4}))?\b",
    re.IGNORECASE,
)

MODEL_CODE_PATTERN = re.compile(
    r"\b([A-Z]{1,5}-?\d{2,}[A-Z0-9]*(?:-[A-Z0-9]+)*)\b"
)


def extract_variant_label(product_name: str) -> str:
    """Recover the variant from a listing title, or return an empty string.

    Scraped titles carry the variant inline, but not always as a measurement.
    Three forms are recognised, in order of preference:

    1. a number with a unit  - "iPhone 17 256 GB Siyah"
    2. a dimension           - "Kamp Çadırı 200x200x145"
    3. a manufacturer code   - "Casio G-Shock GA-2100-1A1DR"

    A title with none of them yields an empty label, which the DataProcessor
    reports as a missing attribute rather than silently accepting.
    """

    match = VARIANT_PATTERN.search(product_name)

    if match is None:
        dimension = DIMENSION_PATTERN.search(product_name)

        if dimension is not None:
            return "x".join(
                part for part in dimension.groups() if part is not None
            )

        model_code = MODEL_CODE_PATTERN.search(product_name)

        if model_code is not None:
            return model_code.group(1)

        return ""

    amount = match.group(1).replace(",", ".")

    # Trim only a decimal tail ("1.50" -> "1.5"). Stripping zeros
    # unconditionally would turn "10" into "1" and "500" into "5".
    if "." in amount:
        amount = amount.rstrip("0").rstrip(".")

    unit = UNIT_DISPLAY.get(match.group(2).upper(), match.group(2))

    # The Turkish "-li" count suffix attaches to the number ("5'li"), unlike
    # unit words which are separated by a space ("256 GB").
    if unit.startswith("'"):
        return f"{amount}{unit}"

    return f"{amount} {unit}"


def derive_scraped_attributes(
    product_name: str,
    category_group: str,
) -> dict[str, Any]:
    """Best-effort attributes for a scraped product.

    Only what the listing title actually states is filled in. Attributes a
    listing page does not expose are left out on purpose so the quality report
    shows how complete the scraped data really is.
    """

    variant_label = extract_variant_label(product_name)
    attributes: dict[str, Any] = {"variant_label": variant_label}
    numeric_match = VARIANT_PATTERN.search(product_name)
    amount = (
        float(numeric_match.group(1).replace(",", "."))
        if numeric_match
        else None
    )
    unit = numeric_match.group(2).upper() if numeric_match else ""
    lowered = product_name.casefold()

    if category_group == "elektronik_cep_telefonu" and unit in {"GB", "TB"}:
        attributes["storage_gb"] = int(
            amount * 1024 if unit == "TB" else amount
        )
    elif category_group == "saglik_bakim_kozmetik" and unit in {"ML", "L", "LT"}:
        attributes["volume_ml"] = int(
            amount * 1000 if unit in {"L", "LT"} else amount
        )
    elif category_group == "petshop":
        if unit in {"KG", "G", "GR"}:
            attributes["weight_kg"] = round(
                amount / 1000 if unit in {"G", "GR"} else amount,
                3,
            )
        if "kedi" in lowered:
            attributes["animal_type"] = "Kedi"
        elif "köpek" in lowered or "kopek" in lowered:
            attributes["animal_type"] = "Köpek"
    elif category_group == "supermarket" and unit in {"G", "GR", "KG"}:
        attributes["net_weight_g"] = int(
            amount * 1000 if unit == "KG" else amount
        )
    elif category_group == "saat_moda_taki_ayakkabi" and variant_label:
        attributes["size_label"] = variant_label

    return attributes


@dataclass(frozen=True)
class SiteAdapter:
    """CSS selectors for one e-commerce listing page.

    Listing markup is owned by the site, not by this project. When a selector
    stops matching, the scraper raises instead of silently writing empty rows,
    which is the signal to re-check the selectors against the live page.
    """

    name: str
    search_url_template: str
    base_url: str
    card_selector: str
    # Tried in order, so the most specific selector wins. A single CSS list
    # would instead pick whichever element comes first in the document, which
    # on Trendyol is the brand rather than the product name.
    name_selectors: tuple[str, ...]
    link_selector: str
    brand_selectors: tuple[str, ...] = ()
    # Some listings expose the brand as an attribute on the card element,
    # which is more reliable than reading it out of the title text.
    brand_attribute: str = ""
    # Set when the site is known to reject automated access, so the error
    # message can say so instead of blaming the selectors.
    known_bot_protection: str = ""

    def search_url(self, term: str) -> str:
        return self.search_url_template.format(query=quote_plus(term))


SITE_ADAPTERS: dict[str, SiteAdapter] = {
    # Verified against the live listing markup on 2026-08-18: a product card is
    # <li class="w" data-mk="Brand"> holding <h3 class="pn_v8"> and an absolute
    # <a class="pw_v8" href>. One search returns about 32 products.
    "akakce": SiteAdapter(
        name="akakce",
        search_url_template="https://www.akakce.com/arama/?q={query}",
        base_url="https://www.akakce.com",
        card_selector="li.w",
        name_selectors=("h3.pn_v8", "h3"),
        link_selector="a[href]",
        brand_attribute="data-mk",
    ),
    "cimri": SiteAdapter(
        name="cimri",
        search_url_template="https://www.cimri.com/arama?q={query}",
        base_url="https://www.cimri.com",
        card_selector="div[class*='ProductCard'], li[class*='ProductCard']",
        name_selectors=("h3", "a[title]"),
        link_selector="a[href]",
        known_bot_protection=(
            "Cimri served a Cloudflare 'you have been blocked' page when this "
            "scraper was tested on 2026-08-18. Use --site akakce instead."
        ),
    ),
    "hepsiburada": SiteAdapter(
        name="hepsiburada",
        search_url_template="https://www.hepsiburada.com/ara?q={query}",
        base_url="https://www.hepsiburada.com",
        card_selector="li[class*='productListContent'], div[class*='productCard']",
        name_selectors=("h3", "span[class*='title']"),
        link_selector="a[href]",
    ),
    "trendyol": SiteAdapter(
        name="trendyol",
        search_url_template="https://www.trendyol.com/sr?q={query}",
        base_url="https://www.trendyol.com",
        card_selector="div.p-card-wrppr",
        name_selectors=("span.prdct-desc-cntnr-name",),
        link_selector="a[href]",
        brand_selectors=("span.prdct-desc-cntnr-ttl",),
    ),
}


def select_text(card: Any, selectors: tuple[str, ...]) -> str:
    """Return the text of the first selector that matches, else empty."""

    for selector in selectors:
        element = card.select_one(selector)

        if element is not None:
            text = " ".join(element.get_text(" ", strip=True).split())

            if text:
                return text

    return ""


def parse_listing_html(
    html: str,
    adapter: SiteAdapter,
    group: CategoryGroup,
    limit: int,
) -> list[CatalogProduct]:
    """Parse one listing page with BeautifulSoup4.

    Kept free of Selenium so it can be unit tested against saved HTML.
    """

    try:
        from bs4 import BeautifulSoup
    except ImportError as error:  # pragma: no cover - dependency guard
        raise ScraperError(
            "BeautifulSoup4 is required for live scraping. "
            "Install it with: pip install -r requirements.txt"
        ) from error

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(adapter.card_selector)

    products: list[CatalogProduct] = []
    seen_names: set[str] = set()

    for card in cards:
        link_element = card.select_one(adapter.link_selector)

        if link_element is None:
            continue

        product_name = select_text(card, adapter.name_selectors)
        href = link_element.get("href", "")

        if not product_name or not href:
            continue

        normalized_name = product_name.casefold()

        if normalized_name in seen_names:
            continue

        seen_names.add(normalized_name)

        brand = ""

        if adapter.brand_attribute:
            brand = str(card.get(adapter.brand_attribute) or "").strip()

        if not brand:
            brand = select_text(card, adapter.brand_selectors)

        if not brand:
            brand = product_name.split(" ", 1)[0]

        # Keep the listing's own URL: it is what a reviewer opens when the
        # results are labeled, and it is the dataset's traceability evidence.
        source_url = urljoin(adapter.base_url, str(href).strip())

        if not source_url.startswith("https://"):
            continue

        products.append(
            CatalogProduct(
                product_name=product_name,
                brand=brand,
                category=group.display_name_tr,
                category_group=group.category_group,
                attributes=derive_scraped_attributes(
                    product_name=product_name,
                    category_group=group.category_group,
                ),
                source_url=source_url,
            )
        )

        if len(products) >= limit:
            break

    return products


class SeleniumCatalogProvider:
    """Load listing pages with Selenium and parse them with BeautifulSoup4."""

    acquisition_mode = ACQUISITION_MODE_SCRAPED

    def __init__(
        self,
        site: str = "akakce",
        page_load_seconds: float = 15.0,
        request_delay_seconds: float = 8.0,
        challenge_retries: int = 2,
        challenge_backoff_seconds: float = 45.0,
        debug_directory: Path | None = None,
    ) -> None:
        if site not in SITE_ADAPTERS:
            raise ScraperError(
                f"Unsupported scraping site: {site}. "
                f"Supported: {sorted(SITE_ADAPTERS)}"
            )

        self.adapter = SITE_ADAPTERS[site]
        self.source_name = self.adapter.name
        self.page_load_seconds = page_load_seconds
        self.request_delay_seconds = request_delay_seconds
        self.challenge_retries = challenge_retries
        self.challenge_backoff_seconds = challenge_backoff_seconds
        self.debug_directory = debug_directory
        self._browser = None

    def collect(
        self,
        group: CategoryGroup,
        limit: int,
    ) -> list[CatalogProduct]:
        terms = SEARCH_TERMS.get(group.category_group, ())

        if not terms:
            raise ScraperError(
                f"No search term is configured for {group.category_group}."
            )

        collected: list[CatalogProduct] = []
        seen_names: set[str] = set()
        empty_terms: list[str] = []
        skipped_incomplete = 0

        for term_index, term in enumerate(terms):
            if len(collected) >= limit:
                break

            if term_index > 0:
                # Listing sites answer a burst of identical-looking requests
                # with a throttling page. A short pause keeps the run polite
                # and the responses parsable.
                sleep(self.request_delay_seconds)

            html = self._load_page(
                url=self.adapter.search_url(term),
                debug_name=f"{group.category_group}_{term}",
            )
            products = parse_listing_html(
                html=html,
                adapter=self.adapter,
                group=group,
                limit=limit,
            )
            added = 0

            for product in products:
                normalized = product.product_name.casefold()

                if normalized in seen_names:
                    continue

                seen_names.add(normalized)

                # Skip unusable products here rather than after collection.
                # Filtering afterwards let the loop stop on a full batch of
                # candidates that later shrank, so the remaining search terms
                # were never tried.
                if group.missing_required_attributes(product.attributes):
                    skipped_incomplete += 1
                    continue

                collected.append(product)
                added += 1

                if len(collected) >= limit:
                    break

            if not products:
                empty_terms.append(term)

            print(
                f"  {group.category_group}: '{term}' -> "
                f"{len(products)} parsed, {added} usable "
                f"(total {len(collected)}/{limit})",
                flush=True,
            )

        if skipped_incomplete:
            print(
                f"  {group.category_group}: skipped {skipped_incomplete} "
                "product(s) whose title stated no usable variant",
                flush=True,
            )

        if not collected:
            raise ScraperError(self._diagnose(group, empty_terms))

        return collected

    def _diagnose(
        self,
        group: CategoryGroup,
        empty_terms: list[str],
    ) -> str:
        """Explain a failure precisely instead of blaming the selectors."""

        message = (
            f"{self.adapter.name} returned no parsable product cards for "
            f"{group.category_group} (tried: {', '.join(empty_terms)}). "
        )

        if self.adapter.known_bot_protection:
            return message + self.adapter.known_bot_protection

        saved = ""

        if self.debug_directory is not None:
            saved = (
                f" The received HTML was saved under {self.debug_directory} "
                "so the cause can be checked."
            )

        return (
            message
            + "Either the listing markup changed and the selectors need "
            "updating, or the request was blocked. No CAPTCHA bypass is "
            "implemented." + saved
        )

    def _load_page(self, url: str, debug_name: str = "") -> str:
        """Load one listing page, backing off when the site rate-limits us."""

        for attempt in range(self.challenge_retries + 1):
            html = self._fetch(url, debug_name)

            if not looks_like_bot_challenge(html):
                return html

            if attempt == self.challenge_retries:
                raise BotChallengeError(
                    f"{self.adapter.name} answered with a bot-protection "
                    f"page after {attempt + 1} attempt(s) at {url}. "
                    "The site rate-limited this run. Wait a while, then "
                    "resume with --resume, or raise --delay. No bypass is "
                    "implemented."
                )

            wait_seconds = self.challenge_backoff_seconds * (attempt + 1)
            print(
                f"    bot protection hit, waiting {wait_seconds:.0f}s "
                f"before retry {attempt + 1}/{self.challenge_retries}",
                flush=True,
            )
            sleep(wait_seconds)

        raise BotChallengeError("Unreachable")

    def _fetch(self, url: str, debug_name: str = "") -> str:
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        browser = self._ensure_browser()
        browser.get(url)

        # Wait for the product cards themselves. implicitly_wait() only sets a
        # timeout for later element lookups and returns immediately, so
        # reading page_source straight after get() can capture the page before
        # the listing has rendered.
        try:
            WebDriverWait(browser, self.page_load_seconds).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, self.adapter.card_selector)
                )
            )
        except TimeoutException:
            # Fall through: the caller reports the empty result, and the saved
            # HTML shows whether this was a block page or a markup change.
            pass

        html = browser.page_source

        if self.debug_directory is not None:
            self.debug_directory.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r"[^\w.-]+", "_", debug_name or "page")
            (self.debug_directory / f"{safe_name}.html").write_text(
                html,
                encoding="utf-8",
            )

        return html

    def _ensure_browser(self):
        """Reuse one browser for the whole run instead of one per request."""

        if self._browser is None:
            from selenium_collector import create_browser

            self._browser = create_browser()

        return self._browser

    def close(self) -> None:
        if self._browser is not None:
            self._browser.quit()
            self._browser = None


def make_provider(
    provider: str,
    site: str = "akakce",
    debug_directory: Path | None = None,
    request_delay_seconds: float = 8.0,
) -> CatalogProvider:
    """Create the requested acquisition provider."""

    if provider == "offline":
        return OfflineCatalogProvider()

    if provider == "selenium":
        return SeleniumCatalogProvider(
            site=site,
            request_delay_seconds=request_delay_seconds,
            debug_directory=debug_directory,
        )

    raise ScraperError(f"Unsupported provider: {provider}")


# ==================================================
# Dataset assembly
# ==================================================

def metadata_path_for(dataset_path: Path) -> Path:
    """Return the metadata file that belongs to a dataset file."""

    return dataset_path.with_name(f"{dataset_path.stem}.metadata.json")


def load_existing_metadata(dataset_path: Path) -> dict[str, Any]:
    """Read the provenance metadata of an earlier run, if there is one."""

    path = metadata_path_for(dataset_path)

    if not path.exists():
        return {}

    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}

    return metadata if isinstance(metadata, dict) else {}


def check_resume_provenance(
    dataset_path: Path,
    provider: CatalogProvider,
) -> str:
    """Refuse to resume a dataset that was produced a different way.

    Carrying synthetic rows into a scraped run, or the other way round, would
    silently mix generated and measured data under one provenance label. That
    is the one mistake this project must never make, so it is blocked here
    rather than explained in the metadata afterwards.
    """

    previous_mode = str(
        load_existing_metadata(dataset_path).get("acquisition_mode", "")
    ).strip()

    if not previous_mode or previous_mode == provider.acquisition_mode:
        return previous_mode

    raise ScraperError(
        f"Cannot resume: {dataset_path.name} was produced with "
        f"acquisition_mode '{previous_mode}', but this run uses "
        f"'{provider.acquisition_mode}'. Mixing generated and scraped rows "
        "under one provenance label is not allowed. Move the existing "
        "dataset aside, or re-run without --resume."
    )


def load_existing_rows(dataset_path: Path) -> dict[str, list[dict[str, Any]]]:
    """Read an earlier run's dataset, grouped by category, for resuming."""

    if not dataset_path.exists():
        return {}

    with dataset_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        existing: dict[str, list[dict[str, Any]]] = {}

        for row in csv.DictReader(stream):
            category_group = (row.get("category_group") or "").strip()

            if category_group:
                existing.setdefault(category_group, []).append(dict(row))

    return existing


GLOBAL_DEDUPE_HEADROOM = 10


def collect_with_headroom(
    provider: CatalogProvider,
    group: CategoryGroup,
    limit: int,
    headroom: int = GLOBAL_DEDUPE_HEADROOM,
) -> list[CatalogProduct]:
    """Collect extra products so filtering still leaves a full category.

    Two filters run after collection: duplicates shared with another category
    are dropped, and products whose title states no usable variant are
    skipped. Without headroom those losses would leave the category short.
    """

    try:
        return provider.collect(group, limit + headroom)
    except ValueError:
        # The offline catalog holds a fixed number of combinations and says so
        # rather than inventing products.
        return provider.collect(group, limit)


def build_dataset(
    provider: CatalogProvider,
    groups: list[CategoryGroup],
    limit_per_category: int | None = None,
    minimum_per_category: int | None = None,
    existing_rows: dict[str, list[dict[str, Any]]] | None = None,
    stats: dict[str, int] | None = None,
    collection_headroom: int = GLOBAL_DEDUPE_HEADROOM,
) -> list[dict[str, Any]]:
    """Collect every category group into one dataset in taxonomy order.

    Every category is attempted before any shortfall is reported, so one run
    shows the state of all ten groups instead of stopping at the first thin
    one. ``minimum_per_category`` defaults to the taxonomy target.

    When ``existing_rows`` is supplied, categories that already reached the
    target are kept as they are and not requested again. Listing sites
    rate-limit long runs, so finishing the dataset across several sessions is
    the realistic path.
    """

    rows: list[dict[str, Any]] = []
    shortfalls: list[tuple[str, int, int]] = []
    existing_rows = existing_rows or {}
    interrupted_by: BotChallengeError | None = None
    collected_this_run = 0
    global_seen_names: set[str] = {
        str(row.get("product_name", "")).casefold()
        for rows_for_group in (existing_rows or {}).values()
        for row in rows_for_group
    }

    def record(count: int) -> None:
        nonlocal collected_this_run
        collected_this_run += count

        if stats is not None:
            stats["collected_this_run"] = collected_this_run

    record(0)

    for group in groups:
        limit = (
            group.expected_product_count
            if limit_per_category is None
            else limit_per_category
        )
        minimum = limit if minimum_per_category is None else minimum_per_category
        already_collected = existing_rows.get(group.category_group, [])

        # A category below the target is topped up, never restarted: throwing
        # away a partly collected category and re-collecting it can end up
        # smaller, because products shared with an already-complete category
        # are removed by the cross-category duplicate filter.
        kept_rows = already_collected[:limit]
        rows.extend(kept_rows)
        needed = limit - len(kept_rows)

        if needed <= 0:
            print(
                f"  {group.category_group}: keeping "
                f"{len(kept_rows)} product(s) from the previous run",
                flush=True,
            )
            continue

        if kept_rows:
            print(
                f"  {group.category_group}: topping up "
                f"{len(kept_rows)} product(s) from the previous run",
                flush=True,
            )

        if interrupted_by is not None:
            # The site is rate-limiting this session. Keep whatever earlier
            # runs produced instead of discarding it.
            shortfalls.append(
                (group.category_group, minimum, len(kept_rows))
            )
            continue

        try:
            products = collect_with_headroom(
                provider,
                group,
                needed,
                headroom=collection_headroom,
            )
        except BotChallengeError as error:
            interrupted_by = error
            shortfalls.append(
                (group.category_group, minimum, len(kept_rows))
            )
            print(f"  {group.category_group}: {error}", flush=True)
            continue

        # Two filters: drop products already used by an earlier category, and
        # skip products whose title states none of the required attributes.
        # Collecting with headroom above is what keeps the category full.
        unique_products = []
        skipped_incomplete = 0

        for product in products:
            normalized = product.product_name.casefold()

            if normalized in global_seen_names:
                continue

            if group.missing_required_attributes(product.attributes):
                skipped_incomplete += 1
                continue

            global_seen_names.add(normalized)
            unique_products.append(product)

            if len(unique_products) >= needed:
                break

        if skipped_incomplete:
            print(
                f"  {group.category_group}: skipped {skipped_incomplete} "
                "product(s) whose title stated no usable variant",
                flush=True,
            )

        products = unique_products[:needed]
        category_total = len(kept_rows) + len(products)

        if category_total < minimum:
            shortfalls.append(
                (group.category_group, minimum, category_total)
            )

        record(len(products))

        # New products continue the identifier sequence after the kept ones.
        for sequence_number, product in enumerate(
            products,
            start=len(kept_rows) + 1,
        ):
            rows.append(
                {
                    "product_id": group.product_id(sequence_number),
                    "product_name": product.product_name,
                    "brand": product.brand,
                    "category": product.category,
                    "category_group": product.category_group,
                    "source_url": product.reference_url(),
                    "attributes": json.dumps(
                        product.attributes,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                }
            )

    if shortfalls:
        details = "\n  ".join(
            f"{category_group}: wanted {minimum}, collected {actual}"
            for category_group, minimum, actual in shortfalls
        )
        advice = (
            "The site rate-limited this session. Wait a while and run again "
            "with --resume to continue from here."
            if interrupted_by is not None
            else "One listing page holds about 32 products, so a category "
            "needs at least two working search terms. Add terms to "
            "SEARCH_TERMS, or lower the target with --min-per-category."
        )
        raise PartialDatasetError(
            f"{len(shortfalls)} category group(s) came up short:\n  "
            f"{details}\n{advice}",
            rows=rows,
            collected_this_run=collected_this_run,
        )

    return rows


def save_dataset(
    rows: list[dict[str, Any]],
    output_path: Path,
    provider: CatalogProvider,
    runtime_seconds: float,
    collected_row_count: int | None = None,
) -> Path:
    """Write the dataset CSV plus a metadata file recording its provenance.

    ``collected_row_count`` is how many rows this run actually obtained from
    the provider. On a resumed run the rest were carried over from an earlier
    file, and the metadata says so instead of claiming the whole dataset was
    produced now.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(DATASET_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)

    category_counts: dict[str, int] = {}

    for row in rows:
        category_counts[row["category_group"]] = (
            category_counts.get(row["category_group"], 0) + 1
        )

    if collected_row_count is None:
        collected_row_count = len(rows)

    carried_over_row_count = max(0, len(rows) - collected_row_count)
    metadata_path = metadata_path_for(output_path)
    metadata: dict[str, Any] = {
        "acquisition_mode": provider.acquisition_mode,
        "source": provider.source_name,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "product_count": len(rows),
        "collected_this_run": collected_row_count,
        "carried_over_from_previous_run": carried_over_row_count,
        "category_group_count": len(category_counts),
        "products_per_category_group": category_counts,
        "runtime_seconds": round(runtime_seconds, 2),
    }

    if provider.acquisition_mode == ACQUISITION_MODE_SYNTHETIC:
        metadata["warning"] = (
            "Synthetic dataset generated offline. Realistic in structure but "
            "not measured market data. Do not report it as scraped results."
        )
    elif collected_row_count == 0:
        # A resumed run that requested nothing must not look like a fresh
        # collection just because a scraping provider was selected.
        metadata["warning"] = (
            "This run collected no new rows; every product was carried over "
            "from the previous dataset. The acquisition_mode describes that "
            "earlier data, not work done now."
        )

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return metadata_path


def rederive_attributes(dataset_path: Path) -> tuple[int, int]:
    """Recompute the attributes column of an existing dataset.

    Attribute derivation is a pure function of the product name and its
    category, so improving the title parser must not require scraping the
    listing pages again. Returns (rows, rows whose attributes changed).
    """

    if not dataset_path.exists():
        raise ScraperError(f"Dataset was not found: {dataset_path}")

    with dataset_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        rows = list(csv.DictReader(stream))

    changed = 0

    for row in rows:
        rebuilt = json.dumps(
            derive_scraped_attributes(
                product_name=row.get("product_name", ""),
                category_group=row.get("category_group", ""),
            ),
            ensure_ascii=False,
            sort_keys=True,
        )

        if rebuilt != row.get("attributes"):
            changed += 1

        row["attributes"] = rebuilt

    with dataset_path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(DATASET_COLUMNS))
        writer.writeheader()
        writer.writerows(
            {column: row.get(column, "") for column in DATASET_COLUMNS}
            for row in rows
        )

    return len(rows), changed


def select_category_groups(
    groups: list[CategoryGroup],
    wanted: Sequence[str],
) -> list[CategoryGroup]:
    """Narrow the taxonomy to the named groups, in taxonomy order.

    An unknown name is refused rather than ignored: silently collecting the
    groups that matched would produce a dataset covering fewer categories
    than the run was asked for, and nothing downstream would say so.
    """

    if not wanted:
        return groups

    known = {group.category_group for group in groups}
    unknown = [name for name in wanted if name not in known]

    if unknown:
        raise ScraperError(
            "Unknown category group(s): "
            + ", ".join(unknown)
            + ". Known: "
            + ", ".join(sorted(known))
        )

    selected = set(wanted)
    return [group for group in groups if group.category_group in selected]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build the ten-category product dataset offline or by scraping."
        )
    )
    parser.add_argument(
        "--rederive-attributes",
        action="store_true",
        help=(
            "Recompute the attributes column of an existing dataset from its "
            "product names, without any network access."
        ),
    )
    parser.add_argument(
        "--provider",
        choices=["offline", "selenium"],
        default="offline",
    )
    parser.add_argument(
        "--site",
        choices=sorted(SITE_ADAPTERS),
        default="akakce",
        help="Listing site used by the selenium provider.",
    )
    parser.add_argument(
        "--headroom",
        type=int,
        default=GLOBAL_DEDUPE_HEADROOM,
        help=(
            "Extra products to collect per category, covering the ones "
            "dropped as cross-category duplicates or as titles without a "
            "usable variant."
        ),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Keep categories already complete in the output file and only "
            "collect the missing ones. Listing sites rate-limit long runs, so "
            "the dataset is normally finished across several sessions."
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=8.0,
        help="Seconds to wait between listing requests (default 8).",
    )
    parser.add_argument(
        "--debug-html",
        type=Path,
        default=None,
        help=(
            "Save every received page here. Use it to tell a markup change "
            "apart from a blocked request."
        ),
    )
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY_FILE)
    parser.add_argument(
        "--categories",
        default="",
        help=(
            "Comma-separated category groups to collect, instead of all ten. "
            "A listing site rate-limits a long session, so a short "
            "demonstration run is better off covering a few groups fully "
            "than all ten partially."
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--limit-per-category",
        type=int,
        default=None,
        help="Override the per-category count from the taxonomy file.",
    )
    parser.add_argument(
        "--min-per-category",
        type=int,
        default=None,
        help=(
            "Fail only below this many products per category. Defaults to the "
            "taxonomy target."
        ),
    )
    args = parser.parse_args()

    if args.rederive_attributes:
        try:
            total, changed = rederive_attributes(args.output)
        except ScraperError as error:
            print(f"[ERROR] {error}")
            raise SystemExit(1) from error

        print("=== ATTRIBUTES REDERIVED ===")
        print(f"Rows:            {total}")
        print(f"Rows changed:    {changed}")
        print(f"Dataset:         {args.output}")
        print()
        print(
            "Provenance is unchanged: the product names and URLs still come "
            "from the original collection."
        )
        return

    started_at = perf_counter()

    try:
        groups = select_category_groups(
            load_category_groups(args.taxonomy),
            [value.strip() for value in args.categories.split(",") if value.strip()],
        )
    except ScraperError as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error
    provider = make_provider(
        args.provider,
        site=args.site,
        debug_directory=args.debug_html,
        request_delay_seconds=args.delay,
    )

    partial_error: PartialDatasetError | None = None
    stats: dict[str, int] = {}

    try:
        if args.resume:
            check_resume_provenance(args.output, provider)

        rows = build_dataset(
            provider=provider,
            groups=groups,
            limit_per_category=args.limit_per_category,
            minimum_per_category=args.min_per_category,
            existing_rows=(
                load_existing_rows(args.output) if args.resume else None
            ),
            stats=stats,
            collection_headroom=args.headroom,
        )
    except PartialDatasetError as error:
        # Keep the progress this session made so the next --resume run picks
        # up from here instead of starting over.
        partial_error = error
        rows = error.rows
        stats["collected_this_run"] = error.collected_this_run
    except (ScraperError, KeyError, ValueError) as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error
    finally:
        close = getattr(provider, "close", None)

        if callable(close):
            close()

    if not rows:
        print(f"[ERROR] {partial_error}")
        raise SystemExit(1)

    collected_this_run = stats.get("collected_this_run", len(rows))
    metadata_path = save_dataset(
        rows=rows,
        output_path=args.output,
        provider=provider,
        runtime_seconds=perf_counter() - started_at,
        collected_row_count=collected_this_run,
    )

    collected_groups = {row["category_group"] for row in rows}

    print()
    print("=== MULTI-CATEGORY DATASET ===")
    print(f"Acquisition mode: {provider.acquisition_mode}")
    print(f"Source:           {provider.source_name}")
    print(f"Products:         {len(rows)}")
    print(f"  collected now:  {collected_this_run}")
    print(f"  carried over:   {len(rows) - collected_this_run}")
    print(f"Category groups:  {len(collected_groups)}/{len(groups)}")
    print(f"Dataset:          {args.output}")
    print(f"Metadata:         {metadata_path}")

    if provider.acquisition_mode == ACQUISITION_MODE_SYNTHETIC:
        print()
        print(
            "NOTE: this dataset is synthetic. Re-run with "
            "--provider selenium to collect real listings."
        )

    if partial_error is not None:
        print()
        print(f"[INCOMPLETE] {partial_error}")
        print()
        print("Progress was saved. Continue later with:")
        print(
            "  python src/product_scraper.py --provider selenium "
            f"--site {args.site} --resume"
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
