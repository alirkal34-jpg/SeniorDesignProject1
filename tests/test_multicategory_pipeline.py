"""Tests for the ten-category revision requested by the project advisor.

The advisor asked for the pipeline to be validated against ten e-commerce
category groups instead of smartphones alone, with roughly fifty products per
group. These tests cover the parts that revision added:

- the category taxonomy that every module reads,
- the offline catalog and the BeautifulSoup4 listing parser,
- the committed 500-product snapshot and its provenance metadata,
- category-aware attribute validation in the DataProcessor,
- the dataset-level quality gate driven by the taxonomy,
- the 20-product labeled evaluation subset.

Everything runs offline.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import product_scraper
from category_taxonomy import (
    DEFAULT_TAXONOMY_FILE,
    TaxonomyError,
    UNIVERSAL_ATTRIBUTE,
    build_category_lookup,
    expected_dataset_size,
    load_category_groups,
)
from data_processor import (
    MULTICATEGORY_PROFILE,
    clean_data,
    describe_attribute_errors,
    validate_data,
)
from keyword_generator import FakeKeywordClient, load_products
from product_catalog import (
    CATEGORY_SPECS,
    CatalogProduct,
    generate_category_products,
)
from product_scraper import (
    SEARCH_TERMS,
    SITE_ADAPTERS,
    BotChallengeError,
    OfflineCatalogProvider,
    PartialDatasetError,
    ScraperError,
    build_dataset,
    check_resume_provenance,
    collect_with_headroom,
    derive_scraped_attributes,
    extract_variant_label,
    load_existing_rows,
    looks_like_bot_challenge,
    make_provider,
    parse_listing_html,
    save_dataset,
    select_category_groups,
)
from quality_check import build_multicategory_quality_profile, check_dataset_quality


ADVISOR_CATEGORY_GROUPS = (
    "elektronik_cep_telefonu",
    "ev_yasam_ofis_kirtasiye",
    "anne_bebek_oyuncak",
    "saat_moda_taki_ayakkabi",
    "kitap_muzik_hobi",
    "spor_outdoor",
    "saglik_bakim_kozmetik",
    "oto_bahce_yapi_market",
    "petshop",
    "supermarket",
)

RAW_DATASET_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "candidate_products_multicategory.csv"
)
RAW_METADATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "candidate_products_multicategory.metadata.json"
)
PROCESSED_DATASET_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "processed_products_multicategory.csv"
)
PROCESSED_JSON_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "processed_products_multicategory.json"
)
KEYWORDS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "generated_keywords_multicategory.json"
)
SUBSET_FILE = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "evaluation_subset_multicategory.csv"
)


TAXONOMY_HEADER = (
    "category_group,display_name_tr,product_id_prefix,"
    "expected_product_count,required_attributes,numeric_attribute_ranges\n"
)


class TaxonomyTests(unittest.TestCase):
    """The category list every other module depends on."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.groups = load_category_groups()

    def write_taxonomy(self, rows: str) -> Path:
        """Write a throwaway taxonomy file for the failure-path tests."""

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "categories.csv"
        path.write_text(TAXONOMY_HEADER + rows, encoding="utf-8")
        return path

    def test_all_ten_advisor_categories_are_defined_in_order(self) -> None:
        self.assertEqual(
            tuple(group.category_group for group in self.groups),
            ADVISOR_CATEGORY_GROUPS,
        )

    def test_each_category_targets_fifty_products(self) -> None:
        for group in self.groups:
            with self.subTest(group=group.category_group):
                self.assertEqual(group.expected_product_count, 50)

        self.assertEqual(expected_dataset_size(self.groups), 500)

    def test_identifier_prefixes_are_unique_and_zero_padded(self) -> None:
        prefixes = [group.product_id_prefix for group in self.groups]

        self.assertEqual(len(prefixes), len(set(prefixes)))
        self.assertEqual(self.groups[0].product_id(1), "ELK001")
        self.assertEqual(self.groups[0].product_id(50), "ELK050")

    def test_every_category_requires_the_universal_variant_attribute(
        self,
    ) -> None:
        for group in self.groups:
            with self.subTest(group=group.category_group):
                self.assertEqual(
                    group.all_required_attributes()[0],
                    UNIVERSAL_ATTRIBUTE,
                )

    def test_optional_attributes_are_separate_from_required_ones(self) -> None:
        for group in self.groups:
            with self.subTest(group=group.category_group):
                self.assertNotIn(
                    UNIVERSAL_ATTRIBUTE,
                    group.optional_attributes,
                )
                self.assertEqual(
                    set(group.all_known_attributes()),
                    {UNIVERSAL_ATTRIBUTE, *group.optional_attributes},
                )

    def test_missing_required_attributes_are_listed_by_name(self) -> None:
        group = build_category_lookup(self.groups)["petshop"]

        self.assertEqual(
            group.missing_required_attributes({"variant_label": "3 kg"}),
            (),
        )
        self.assertEqual(
            group.missing_required_attributes({"variant_label": "  "}),
            (UNIVERSAL_ATTRIBUTE,),
        )
        self.assertEqual(
            group.missing_required_attributes({}),
            (UNIVERSAL_ATTRIBUTE,),
        )

    def test_numeric_ranges_are_parsed_into_bounds(self) -> None:
        lookup = build_category_lookup(self.groups)

        self.assertEqual(
            lookup["elektronik_cep_telefonu"].numeric_attribute_ranges,
            {"storage_gb": (8.0, 2048.0), "ram_gb": (1.0, 64.0)},
        )
        self.assertEqual(
            lookup["petshop"].numeric_attribute_ranges,
            {"weight_kg": (0.05, 30.0)},
        )

    def test_sequence_numbers_below_one_are_rejected(self) -> None:
        with self.assertRaises(TaxonomyError):
            self.groups[0].product_id(0)

    def test_duplicate_prefix_is_rejected(self) -> None:
        path = self.write_taxonomy("one,One,AAA,5,,\ntwo,Two,AAA,5,,\n")

        with self.assertRaises(TaxonomyError):
            load_category_groups(path)

    def test_duplicate_category_name_is_rejected(self) -> None:
        path = self.write_taxonomy("one,One,AAA,5,,\none,One,BBB,5,,\n")

        with self.assertRaises(TaxonomyError):
            load_category_groups(path)

    def test_malformed_numeric_range_is_rejected(self) -> None:
        path = self.write_taxonomy("one,One,AAA,5,,weight_kg:1\n")

        with self.assertRaises(TaxonomyError):
            load_category_groups(path)

    def test_inverted_numeric_range_is_rejected(self) -> None:
        path = self.write_taxonomy("one,One,AAA,5,,weight_kg:30:1\n")

        with self.assertRaises(TaxonomyError):
            load_category_groups(path)

    def test_non_numeric_product_count_is_rejected(self) -> None:
        path = self.write_taxonomy("one,One,AAA,çok,,\n")

        with self.assertRaises(TaxonomyError):
            load_category_groups(path)

    def test_missing_file_is_rejected(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_category_groups(PROJECT_ROOT / "data" / "reference" / "no.csv")


class OfflineCatalogTests(unittest.TestCase):
    """The deterministic generator behind the committed snapshot."""

    def test_every_advisor_category_has_a_catalog(self) -> None:
        self.assertEqual(
            set(CATEGORY_SPECS),
            set(ADVISOR_CATEGORY_GROUPS),
        )

    def test_generation_is_deterministic(self) -> None:
        first = generate_category_products("petshop", 10)
        second = generate_category_products("petshop", 10)

        self.assertEqual(first, second)

    def test_generated_products_are_unique_within_a_category(self) -> None:
        for category_group in ADVISOR_CATEGORY_GROUPS:
            with self.subTest(category_group=category_group):
                products = generate_category_products(category_group, 50)

                self.assertEqual(len(products), 50)
                self.assertEqual(
                    len({product.product_name for product in products}),
                    50,
                )

    def test_generated_attributes_satisfy_the_category_rules(self) -> None:
        lookup = build_category_lookup(load_category_groups())

        for category_group in ADVISOR_CATEGORY_GROUPS:
            group = lookup[category_group]

            for product in generate_category_products(category_group, 50):
                with self.subTest(product=product.product_name):
                    errors = describe_attribute_errors(
                        raw_attributes=json.dumps(product.attributes),
                        category_group_name=category_group,
                        category_lookup=lookup,
                    )

                    self.assertEqual(errors, [], msg=str(group))

    def test_reference_urls_are_https_and_product_specific(self) -> None:
        products = generate_category_products("supermarket", 5)
        urls = [product.reference_url() for product in products]

        self.assertTrue(all(url.startswith("https://") for url in urls))
        self.assertEqual(len(set(urls)), len(urls))

    def test_requesting_more_products_than_available_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generate_category_products("petshop", 10_000)

    def test_unknown_category_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            generate_category_products("uzay_arastirmalari", 1)


class ListingParserTests(unittest.TestCase):
    """The BeautifulSoup4 half of the live scraping path."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.group = build_category_lookup(load_category_groups())[
            "elektronik_cep_telefonu"
        ]
        cls.adapter = SITE_ADAPTERS["trendyol"]

    def _listing_html(self, *names: str) -> str:
        cards = "".join(
            f'<div class="p-card-wrppr">'
            f'<a href="/urun/{index}">'
            f'<span class="prdct-desc-cntnr-ttl">Marka{index}</span>'
            f'<span class="prdct-desc-cntnr-name">{name}</span>'
            f"</a></div>"
            for index, name in enumerate(names, start=1)
        )
        return f"<html><body>{cards}</body></html>"

    def test_product_cards_are_extracted(self) -> None:
        products = parse_listing_html(
            html=self._listing_html("Apple iPhone 16", "Samsung Galaxy S25"),
            adapter=self.adapter,
            group=self.group,
            limit=5,
        )

        self.assertEqual(
            [product.product_name for product in products],
            ["Apple iPhone 16", "Samsung Galaxy S25"],
        )
        self.assertEqual(
            {product.category_group for product in products},
            {"elektronik_cep_telefonu"},
        )

    def test_brand_comes_from_the_configured_selector(self) -> None:
        products = parse_listing_html(
            html=self._listing_html("Apple iPhone 16"),
            adapter=self.adapter,
            group=self.group,
            limit=5,
        )

        self.assertEqual(products[0].brand, "Marka1")

    def test_repeated_titles_are_collected_once(self) -> None:
        products = parse_listing_html(
            html=self._listing_html("Apple iPhone 16", "apple iphone 16"),
            adapter=self.adapter,
            group=self.group,
            limit=5,
        )

        self.assertEqual(len(products), 1)

    def test_limit_is_respected(self) -> None:
        products = parse_listing_html(
            html=self._listing_html("A phone", "B phone", "C phone"),
            adapter=self.adapter,
            group=self.group,
            limit=2,
        )

        self.assertEqual(len(products), 2)

    def test_unparsable_markup_yields_no_products(self) -> None:
        # Sites change their markup often. Returning nothing lets the caller
        # raise a clear error instead of writing empty rows to the dataset.
        products = parse_listing_html(
            html="<html><body><div class='something-else'>x</div></body></html>",
            adapter=self.adapter,
            group=self.group,
            limit=5,
        )

        self.assertEqual(products, [])

    def test_the_listing_url_is_kept_as_the_source_url(self) -> None:
        # The scraper parses the product's own link and must keep it. It once
        # discarded it and generated a search URL instead, throwing away the
        # dataset's traceability evidence and the page a reviewer opens.
        products = parse_listing_html(
            html=self._listing_html("Apple iPhone 16"),
            adapter=self.adapter,
            group=self.group,
            limit=5,
        )

        self.assertEqual(
            products[0].reference_url(),
            "https://www.trendyol.com/urun/1",
        )

    def test_relative_links_are_resolved_against_the_site(self) -> None:
        html = (
            '<div class="p-card-wrppr"><a href="/urun/42">'
            '<span class="prdct-desc-cntnr-ttl">Marka</span>'
            '<span class="prdct-desc-cntnr-name">Bir Ürün</span>'
            "</a></div>"
        )

        products = parse_listing_html(
            html=html,
            adapter=self.adapter,
            group=self.group,
            limit=5,
        )

        self.assertEqual(
            products[0].reference_url(),
            "https://www.trendyol.com/urun/42",
        )

    def test_non_https_links_are_skipped(self) -> None:
        html = (
            '<div class="p-card-wrppr"><a href="http://insecure.example/x">'
            '<span class="prdct-desc-cntnr-name">Bir Ürün</span>'
            "</a></div>"
        )

        products = parse_listing_html(
            html=html,
            adapter=self.adapter,
            group=self.group,
            limit=5,
        )

        self.assertEqual(products, [])

    def test_generated_products_fall_back_to_a_search_url(self) -> None:
        product = generate_category_products("petshop", 1)[0]

        self.assertEqual(product.source_url, "")
        self.assertTrue(product.reference_url().startswith("https://"))
        self.assertIn("/arama", product.reference_url())

    def test_every_configured_site_has_the_required_selectors(self) -> None:
        for name, adapter in SITE_ADAPTERS.items():
            with self.subTest(site=name):
                self.assertTrue(adapter.card_selector)
                self.assertTrue(adapter.name_selectors)
                self.assertTrue(adapter.link_selector)
                self.assertTrue(
                    adapter.search_url("kedi maması").startswith("https://")
                )

    def test_name_selectors_are_tried_in_priority_order(self) -> None:
        # Trendyol renders the brand before the product name inside a card, so
        # a single comma-separated CSS list would return the brand. Selectors
        # are tried one at a time to keep the most specific one winning.
        products = parse_listing_html(
            html=self._listing_html("Apple iPhone 16"),
            adapter=self.adapter,
            group=self.group,
            limit=5,
        )

        self.assertEqual(products[0].product_name, "Apple iPhone 16")
        self.assertNotEqual(products[0].product_name, products[0].brand)


class VariantExtractionTests(unittest.TestCase):
    """Recovering the variant from a scraped listing title."""

    def test_common_turkish_units_are_recognised(self) -> None:
        for product_name, expected in (
            ("iPhone 17 256 GB Siyah", "256 GB"),
            ("Pro Plan Somonlu 10 kg Yetişkin Kedi Maması", "10 kg"),
            ("Nivea Nemlendirici Krem 400 ml", "400 ml"),
            ("Nike Air Max 42 Numara", "42 Numara"),
            ("Ülker Çikolatalı Gofret 500 g", "500 g"),
            ("Karaca Tencere Seti 6 Parça", "6 Parça"),
            ("Samsung SSD 1 TB", "1 TB"),
        ):
            with self.subTest(product_name=product_name):
                self.assertEqual(
                    extract_variant_label(product_name),
                    expected,
                )

    def test_trailing_zeros_of_whole_numbers_are_kept(self) -> None:
        # Trimming zeros unconditionally once turned "10 kg" into "1 kg" and
        # "500 g" into "5 g", silently corrupting every scraped weight.
        self.assertEqual(extract_variant_label("Mama 10 kg"), "10 kg")
        self.assertEqual(extract_variant_label("Gofret 500 g"), "500 g")
        self.assertEqual(extract_variant_label("Disk 100 GB"), "100 GB")

    def test_decimal_comma_is_normalised_and_tail_trimmed(self) -> None:
        self.assertEqual(extract_variant_label("Mama 1,5 kg"), "1.5 kg")
        self.assertEqual(extract_variant_label("Su 1.50 lt"), "1.5 lt")

    def test_title_without_a_measurement_yields_no_variant(self) -> None:
        # An empty label is reported by the DataProcessor as a missing
        # attribute rather than being quietly accepted.
        self.assertEqual(extract_variant_label("Tutunamayanlar Ciltli"), "")

    def test_numeric_attributes_are_derived_per_category(self) -> None:
        self.assertEqual(
            derive_scraped_attributes(
                "iPhone 17 256 GB Siyah",
                "elektronik_cep_telefonu",
            ),
            {"variant_label": "256 GB", "storage_gb": 256},
        )
        self.assertEqual(
            derive_scraped_attributes(
                "Nivea Krem 400 ml",
                "saglik_bakim_kozmetik",
            ),
            {"variant_label": "400 ml", "volume_ml": 400},
        )
        self.assertEqual(
            derive_scraped_attributes(
                "Ülker Gofret 500 g",
                "supermarket",
            ),
            {"variant_label": "500 g", "net_weight_g": 500},
        )

    def test_units_are_converted_to_the_taxonomy_unit(self) -> None:
        self.assertEqual(
            derive_scraped_attributes("SSD 1 TB", "elektronik_cep_telefonu")[
                "storage_gb"
            ],
            1024,
        )
        self.assertEqual(
            derive_scraped_attributes("Şampuan 1 lt", "saglik_bakim_kozmetik")[
                "volume_ml"
            ],
            1000,
        )
        self.assertEqual(
            derive_scraped_attributes("Mama 400 g", "petshop")["weight_kg"],
            0.4,
        )

    def test_animal_type_is_read_from_the_title(self) -> None:
        self.assertEqual(
            derive_scraped_attributes("Whiskas Kedi Maması 3 kg", "petshop")[
                "animal_type"
            ],
            "Kedi",
        )
        self.assertEqual(
            derive_scraped_attributes("Pedigree Köpek Maması 3 kg", "petshop")[
                "animal_type"
            ],
            "Köpek",
        )


class SearchTermTests(unittest.TestCase):
    """Several search terms per category are needed to reach fifty products."""

    def test_every_category_has_search_terms(self) -> None:
        self.assertEqual(
            set(SEARCH_TERMS),
            set(ADVISOR_CATEGORY_GROUPS),
        )

    def test_each_category_uses_more_than_one_term(self) -> None:
        # One listing page returns about thirty products, so a single term
        # cannot fill a fifty-product category.
        for category_group, terms in SEARCH_TERMS.items():
            with self.subTest(category_group=category_group):
                self.assertGreaterEqual(len(terms), 2)
                self.assertEqual(len(set(terms)), len(terms))


class BotChallengeDetectionTests(unittest.TestCase):
    """Telling a rate-limit interstitial apart from a markup change."""

    def test_the_real_akakce_challenge_page_is_recognised(self) -> None:
        # Wording taken from the page the scraper actually received on
        # 2026-08-18 after six rapid requests.
        html = (
            "<html><head><title>Bir dakika lütfen...</title></head><body>"
            "www.akakce.com Güvenlik doğrulaması yapılıyor. Bu web sitesi, "
            "kötü niyetli botlara karşı korunmak için bir güvenlik hizmeti "
            "kullanıyor. Enable JavaScript and cookies to continue"
            "</body></html>"
        )

        self.assertTrue(looks_like_bot_challenge(html))

    def test_the_cloudflare_block_page_is_recognised(self) -> None:
        html = (
            "<html><title>Attention Required! | Cloudflare</title>"
            "<body>Sorry, you have been blocked</body></html>"
        )

        self.assertTrue(looks_like_bot_challenge(html))

    def test_a_real_listing_page_is_not_flagged(self) -> None:
        html = (
            "<html><body><ul>"
            "<li class='w' data-mk='Apple'><a href='https://x'>"
            "<h3 class='pn_v8'>iPhone 17 256 GB</h3></a></li>"
            "</ul></body></html>"
        )

        self.assertFalse(looks_like_bot_challenge(html))


class ResumeTests(unittest.TestCase):
    """Finishing the dataset across several rate-limited sessions."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.dataset_path = Path(self.directory.name) / "dataset.csv"
        self.groups = load_category_groups()

    def _write_partial_dataset(self, category_groups: tuple[str, ...]) -> None:
        rows = build_dataset(
            provider=OfflineCatalogProvider(),
            groups=[
                group
                for group in self.groups
                if group.category_group in category_groups
            ],
            limit_per_category=5,
        )
        save_dataset(
            rows=rows,
            output_path=self.dataset_path,
            provider=OfflineCatalogProvider(),
            runtime_seconds=1.0,
        )

    def test_existing_rows_are_grouped_by_category(self) -> None:
        self._write_partial_dataset(("petshop", "supermarket"))

        existing = load_existing_rows(self.dataset_path)

        self.assertEqual(set(existing), {"petshop", "supermarket"})
        self.assertEqual(len(existing["petshop"]), 5)

    def test_missing_file_resumes_from_nothing(self) -> None:
        self.assertEqual(
            load_existing_rows(Path(self.directory.name) / "absent.csv"),
            {},
        )

    def test_complete_categories_are_kept_and_not_recollected(self) -> None:
        self._write_partial_dataset(("petshop",))
        existing = load_existing_rows(self.dataset_path)

        class RefusingProvider:
            """Fails if asked for a category that is already complete."""

            acquisition_mode = "scraped"
            source_name = "refusing"

            def __init__(self) -> None:
                self.requested: list[str] = []

            def collect(self, group, limit):
                self.requested.append(group.category_group)
                return generate_category_products(group.category_group, limit)

        provider = RefusingProvider()
        rows = build_dataset(
            provider=provider,
            groups=self.groups,
            limit_per_category=5,
            existing_rows=existing,
        )

        self.assertNotIn("petshop", provider.requested)
        self.assertEqual(len(provider.requested), len(self.groups) - 1)
        self.assertEqual(len(rows), len(self.groups) * 5)

    def test_a_short_category_is_topped_up_not_restarted(self) -> None:
        # Restarting a short category can shrink it: products shared with an
        # already-complete category are removed by the duplicate filter. A
        # resume once cut a 34-product category down to 9 this way.
        self._write_partial_dataset(("petshop",))
        existing = load_existing_rows(self.dataset_path)
        petshop_rows = existing["petshop"]
        self.assertEqual(len(petshop_rows), 5)

        group = build_category_lookup(self.groups)["petshop"]
        rows = build_dataset(
            provider=OfflineCatalogProvider(),
            groups=[group],
            limit_per_category=8,
            existing_rows=existing,
        )

        self.assertEqual(len(rows), 8)

        kept_names = [row["product_name"] for row in petshop_rows]
        result_names = [row["product_name"] for row in rows]

        # The five earlier products survive, in place, and three are added.
        self.assertEqual(result_names[:5], kept_names)
        self.assertEqual(len(set(result_names)), 8)

    def test_topping_up_continues_the_identifier_sequence(self) -> None:
        self._write_partial_dataset(("petshop",))
        group = build_category_lookup(self.groups)["petshop"]

        rows = build_dataset(
            provider=OfflineCatalogProvider(),
            groups=[group],
            limit_per_category=8,
            existing_rows=load_existing_rows(self.dataset_path),
        )

        self.assertEqual(
            [row["product_id"] for row in rows],
            [f"PET{number:03d}" for number in range(1, 9)],
        )

    def test_topping_up_counts_only_the_new_rows_as_collected(self) -> None:
        self._write_partial_dataset(("petshop",))
        group = build_category_lookup(self.groups)["petshop"]
        stats: dict[str, int] = {}

        build_dataset(
            provider=OfflineCatalogProvider(),
            groups=[group],
            limit_per_category=8,
            existing_rows=load_existing_rows(self.dataset_path),
            stats=stats,
        )

        self.assertEqual(stats["collected_this_run"], 3)

    def test_a_rate_limited_run_keeps_its_progress(self) -> None:
        class ChallengedProvider:
            """Serves two categories, then gets rate-limited."""

            acquisition_mode = "scraped"
            source_name = "challenged"

            def __init__(self) -> None:
                self.calls = 0

            def collect(self, group, limit):
                self.calls += 1

                if self.calls > 2:
                    raise BotChallengeError("rate limited")

                return generate_category_products(group.category_group, limit)

        with self.assertRaises(PartialDatasetError) as caught:
            build_dataset(
                provider=ChallengedProvider(),
                groups=self.groups,
                limit_per_category=5,
            )

        # The two completed categories survive so --resume can continue.
        self.assertEqual(len(caught.exception.rows), 10)
        self.assertIn("--resume", str(caught.exception))

    def test_resuming_a_synthetic_dataset_with_a_scraper_is_refused(
        self,
    ) -> None:
        # A resumed run once kept 500 synthetic rows and stamped them
        # "scraped", because the provider decided the label while the rows
        # came from an earlier file. Mixing provenance is now blocked.
        self._write_partial_dataset(("petshop",))

        class ScrapingProvider:
            acquisition_mode = "scraped"
            source_name = "akakce"

            def collect(self, group, limit):
                raise AssertionError("must not be reached")

        with self.assertRaises(ScraperError) as caught:
            check_resume_provenance(self.dataset_path, ScrapingProvider())

        message = str(caught.exception)
        self.assertIn("synthetic", message)
        self.assertIn("scraped", message)

    def test_resuming_the_same_acquisition_mode_is_allowed(self) -> None:
        self._write_partial_dataset(("petshop",))

        self.assertEqual(
            check_resume_provenance(
                self.dataset_path,
                OfflineCatalogProvider(),
            ),
            "synthetic",
        )

    def test_resuming_without_a_previous_run_is_allowed(self) -> None:
        class ScrapingProvider:
            acquisition_mode = "scraped"
            source_name = "akakce"

        self.assertEqual(
            check_resume_provenance(
                Path(self.directory.name) / "absent.csv",
                ScrapingProvider(),
            ),
            "",
        )

    def test_metadata_separates_new_rows_from_carried_over_rows(self) -> None:
        rows = build_dataset(
            provider=OfflineCatalogProvider(),
            groups=self.groups[:2],
            limit_per_category=5,
        )

        metadata_path = save_dataset(
            rows=rows,
            output_path=self.dataset_path,
            provider=OfflineCatalogProvider(),
            runtime_seconds=1.0,
            collected_row_count=4,
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertEqual(metadata["product_count"], 10)
        self.assertEqual(metadata["collected_this_run"], 4)
        self.assertEqual(metadata["carried_over_from_previous_run"], 6)

    def test_a_run_that_collected_nothing_says_so(self) -> None:
        # The failure mode that produced a false "scraped" label: a resumed
        # run where every category was already complete.
        class ScrapingProvider:
            acquisition_mode = "scraped"
            source_name = "akakce"

        rows = build_dataset(
            provider=OfflineCatalogProvider(),
            groups=self.groups[:1],
            limit_per_category=5,
        )

        metadata_path = save_dataset(
            rows=rows,
            output_path=self.dataset_path,
            provider=ScrapingProvider(),
            runtime_seconds=0.0,
            collected_row_count=0,
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertEqual(metadata["collected_this_run"], 0)
        self.assertEqual(metadata["carried_over_from_previous_run"], 5)
        self.assertIn("collected no new rows", metadata["warning"])

    def test_build_dataset_reports_how_many_rows_it_collected(self) -> None:
        self._write_partial_dataset(("petshop",))
        stats: dict[str, int] = {}

        build_dataset(
            provider=OfflineCatalogProvider(),
            groups=self.groups[:3],
            limit_per_category=5,
            existing_rows=load_existing_rows(self.dataset_path),
            stats=stats,
        )

        # petshop is not in the first three groups, so all fifteen are new.
        self.assertEqual(stats["collected_this_run"], 15)

    def test_a_short_category_reports_every_group_before_failing(self) -> None:
        class ThinProvider:
            acquisition_mode = "scraped"
            source_name = "thin"

            def collect(self, group, limit):
                return generate_category_products(group.category_group, 2)

        with self.assertRaises(PartialDatasetError) as caught:
            build_dataset(
                provider=ThinProvider(),
                groups=self.groups,
                limit_per_category=5,
            )

        message = str(caught.exception)

        for group in self.groups:
            with self.subTest(group=group.category_group):
                self.assertIn(group.category_group, message)


class ScraperAssemblyTests(unittest.TestCase):
    """Turning collected products into the dataset and its metadata."""

    def test_offline_provider_is_selected_by_name(self) -> None:
        self.assertIsInstance(make_provider("offline"), OfflineCatalogProvider)

    def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaises(ScraperError):
            make_provider("telepathy")

    def test_unknown_scraping_site_is_rejected(self) -> None:
        with self.assertRaises(ScraperError):
            make_provider("selenium", site="not-a-store")

    def test_dataset_rows_follow_taxonomy_order_and_identifiers(self) -> None:
        groups = load_category_groups()
        rows = build_dataset(
            provider=OfflineCatalogProvider(),
            groups=groups,
            limit_per_category=3,
        )

        self.assertEqual(len(rows), 30)
        self.assertEqual(
            [row["product_id"] for row in rows[:4]],
            ["ELK001", "ELK002", "ELK003", "EVY001"],
        )

    def test_one_product_cannot_appear_in_two_categories(self) -> None:
        # Listing sites return the same product under different searches, so
        # without global deduplication a product lands in the dataset twice
        # under two identifiers and then fails duplicate-name validation.
        class RepeatingProvider:
            """Returns the same product for every category."""

            acquisition_mode = "scraped"
            source_name = "repeating"

            def collect(self, group, limit):
                shared = CatalogProduct(
                    product_name="Aynı Ürün 1 kg",
                    brand="Marka",
                    category=group.display_name_tr,
                    category_group=group.category_group,
                    attributes={"variant_label": "1 kg"},
                    source_url="https://example.com/p",
                )
                unique = [
                    CatalogProduct(
                        product_name=f"{group.category_group} Ürün {index}",
                        brand="Marka",
                        category=group.display_name_tr,
                        category_group=group.category_group,
                        attributes={"variant_label": "1 kg"},
                        source_url=f"https://example.com/{group.category_group}/{index}",
                    )
                    for index in range(limit)
                ]
                return [shared, *unique]

        rows = build_dataset(
            provider=RepeatingProvider(),
            groups=load_category_groups()[:3],
            limit_per_category=4,
        )

        names = [row["product_name"] for row in rows]

        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(
            sum(1 for name in names if name == "Aynı Ürün 1 kg"),
            1,
        )

    def test_headroom_falls_back_when_the_catalog_is_fixed_size(self) -> None:
        # The offline catalog holds exactly as many combinations as it can
        # build, so asking for extra must not fail the run.
        group = build_category_lookup(load_category_groups())["petshop"]

        products = collect_with_headroom(
            provider=OfflineCatalogProvider(),
            group=group,
            limit=group.expected_product_count,
        )

        self.assertGreaterEqual(len(products), group.expected_product_count)

    def test_metadata_records_synthetic_provenance(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output_path = Path(directory.name) / "dataset.csv"
        provider = OfflineCatalogProvider()

        metadata_path = save_dataset(
            rows=build_dataset(
                provider=provider,
                groups=load_category_groups(),
                limit_per_category=2,
            ),
            output_path=output_path,
            provider=provider,
            runtime_seconds=1.0,
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertEqual(
            metadata["acquisition_mode"],
            product_scraper.ACQUISITION_MODE_SYNTHETIC,
        )
        self.assertEqual(metadata["product_count"], 20)
        self.assertEqual(metadata["category_group_count"], 10)
        self.assertIn("warning", metadata)
        self.assertIn("not measured market data", metadata["warning"])


def find_committed_dataset() -> tuple[Path, Path] | None:
    """Locate the dataset the experiments currently use.

    A real scrape is collected over several rate-limited sessions, so the
    scraped file and the offline snapshot can both exist. The scraped dataset
    wins when it is present; otherwise the synthetic one is used.
    """

    candidates = (
        (RAW_DATASET_FILE, RAW_METADATA_FILE),
        (
            RAW_DATASET_FILE.with_name(
                "candidate_products_multicategory.synthetic.csv"
            ),
            RAW_METADATA_FILE.with_name(
                "candidate_products_multicategory.synthetic.metadata.json"
            ),
        ),
    )

    for dataset_path, metadata_path in candidates:
        if dataset_path.is_file() and metadata_path.is_file():
            return dataset_path, metadata_path

    return None


class CommittedSnapshotTests(unittest.TestCase):
    """The 500-product dataset committed for reproducible experiments."""

    @classmethod
    def setUpClass(cls) -> None:
        located = find_committed_dataset()

        if located is None:
            raise unittest.SkipTest(
                "No multi-category dataset is present. Build one with "
                "product_scraper.py before running these tests."
            )

        dataset_path, metadata_path = located
        cls.dataset_path = dataset_path

        with dataset_path.open(
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            cls.rows = list(csv.DictReader(stream))

        cls.metadata = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )

    def category_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}

        for row in self.rows:
            counts[row["category_group"]] = (
                counts.get(row["category_group"], 0) + 1
            )

        return counts

    def test_every_advisor_category_is_represented(self) -> None:
        self.assertEqual(
            set(self.category_counts()),
            set(ADVISOR_CATEGORY_GROUPS),
        )

    def test_no_category_exceeds_its_taxonomy_target(self) -> None:
        targets = {
            group.category_group: group.expected_product_count
            for group in load_category_groups()
        }

        for category_group, count in self.category_counts().items():
            with self.subTest(category_group=category_group):
                self.assertLessEqual(count, targets[category_group])

    def test_at_most_one_category_falls_short_of_its_target(self) -> None:
        # Measured on the live scrape: fashion listings frequently state no
        # specification at all, so that group cannot reach fifty products
        # carrying a usable variant. Every other group does. A second short
        # group would mean something regressed in collection or parsing.
        targets = {
            group.category_group: group.expected_product_count
            for group in load_category_groups()
        }
        short = {
            category_group: count
            for category_group, count in self.category_counts().items()
            if count < targets[category_group]
        }

        self.assertLessEqual(len(short), 1, msg=str(short))

        for category_group, count in short.items():
            with self.subTest(category_group=category_group):
                self.assertGreaterEqual(count, 30)

    def test_identifiers_names_and_urls_are_unique(self) -> None:
        total = len(self.rows)

        self.assertEqual(
            len({row["product_id"] for row in self.rows}),
            total,
        )
        self.assertEqual(
            len({row["product_name"].casefold() for row in self.rows}),
            total,
        )
        self.assertEqual(
            len({row["source_url"] for row in self.rows}),
            total,
        )

    def test_every_source_url_uses_https(self) -> None:
        self.assertTrue(
            all(
                row["source_url"].startswith("https://")
                for row in self.rows
            )
        )

    def test_snapshot_declares_its_provenance_honestly(self) -> None:
        # The distinction between generated and measured data must never
        # quietly disappear from the report. A resumed run once kept synthetic
        # rows and labeled them "scraped"; this assertion caught it.
        mode = self.metadata["acquisition_mode"]

        self.assertIn(
            mode,
            {
                product_scraper.ACQUISITION_MODE_SYNTHETIC,
                product_scraper.ACQUISITION_MODE_SCRAPED,
            },
        )
        self.assertEqual(self.metadata["product_count"], len(self.rows))

        if mode == product_scraper.ACQUISITION_MODE_SYNTHETIC:
            self.assertIn("warning", self.metadata)
            self.assertIn(
                "not measured market data",
                self.metadata["warning"],
            )

    def test_row_counts_add_up_to_the_declared_total(self) -> None:
        # collected_this_run + carried_over must equal product_count, so a
        # resumed run cannot present carried-over rows as freshly collected.
        if "collected_this_run" not in self.metadata:
            self.skipTest("Dataset predates per-run provenance counters.")

        self.assertEqual(
            self.metadata["collected_this_run"]
            + self.metadata["carried_over_from_previous_run"],
            self.metadata["product_count"],
        )

    def test_a_synthetic_dataset_never_points_at_a_real_listing_page(
        self,
    ) -> None:
        # The offline catalog builds lookup URLs on a price-comparison search
        # endpoint. Confusing those with scraped product URLs is what made the
        # false "scraped" label hard to spot.
        if self.metadata["acquisition_mode"] != (
            product_scraper.ACQUISITION_MODE_SYNTHETIC
        ):
            self.skipTest("Only applies to the generated dataset.")

        self.assertTrue(
            all("/arama" in row["source_url"] for row in self.rows)
        )

    def test_snapshot_processes_without_a_single_invalid_row(self) -> None:
        with redirect_stdout(io.StringIO()):
            validated = validate_data(
                clean_data(
                    pd.read_csv(self.dataset_path),
                    MULTICATEGORY_PROFILE,
                ),
                MULTICATEGORY_PROFILE,
            )

        self.assertEqual(len(validated), len(self.rows))
        self.assertEqual(
            set(validated["validation_status"]),
            {"valid"},
        )

    def test_quality_gate_passes_at_the_datasets_own_floor(self) -> None:
        # The gate is run at the floor the source can actually fill. Its
        # report still shows every category against the taxonomy target, so
        # the shortfall stays visible rather than being defined away.
        products = pd.read_csv(PROCESSED_DATASET_FILE)
        floor = min(products["category_group"].value_counts())

        with redirect_stdout(io.StringIO()):
            passed = check_dataset_quality(
                products,
                build_multicategory_quality_profile(
                    minimum_per_category=int(floor),
                ),
            )

        self.assertTrue(passed)

    def test_quality_gate_reports_a_category_below_target(self) -> None:
        products = pd.read_csv(PROCESSED_DATASET_FILE)
        counts = products["category_group"].value_counts()
        targets = {
            group.category_group: group.expected_product_count
            for group in load_category_groups()
        }
        short = [
            name
            for name, count in counts.items()
            if count < targets[name]
        ]

        if not short:
            self.skipTest("Every category reached its target.")

        stream = io.StringIO()

        with redirect_stdout(stream):
            passed = check_dataset_quality(
                products,
                build_multicategory_quality_profile(),
            )

        self.assertFalse(passed)
        self.assertIn("below target", stream.getvalue())

    def test_quality_gate_fails_when_a_category_is_short(self) -> None:
        products = pd.read_csv(PROCESSED_DATASET_FILE)
        shortened = products[products["category_group"] != "petshop"]

        with redirect_stdout(io.StringIO()):
            passed = check_dataset_quality(
                shortened,
                build_multicategory_quality_profile(),
            )

        self.assertFalse(passed)

    def test_quality_gate_fails_on_a_category_outside_the_taxonomy(
        self,
    ) -> None:
        products = pd.read_csv(PROCESSED_DATASET_FILE)
        products.loc[0, "category_group"] = "uzay_arastirmalari"

        with redirect_stdout(io.StringIO()):
            passed = check_dataset_quality(
                products,
                build_multicategory_quality_profile(),
            )

        self.assertFalse(passed)


class CategoryAttributeValidationTests(unittest.TestCase):
    """Per-category rules applied to the attributes JSON column."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.lookup = build_category_lookup(load_category_groups())

    def _errors(self, attributes: str, category: str) -> list[str]:
        return describe_attribute_errors(
            raw_attributes=attributes,
            category_group_name=category,
            category_lookup=self.lookup,
        )

    def test_a_complete_row_has_no_errors(self) -> None:
        errors = self._errors(
            json.dumps(
                {"variant_label": "256 GB", "storage_gb": 256, "ram_gb": 8}
            ),
            "elektronik_cep_telefonu",
        )

        self.assertEqual(errors, [])

    def test_unknown_category_is_reported(self) -> None:
        self.assertEqual(
            self._errors("{}", "uzay_arastirmalari"),
            ["unknown_category_group"],
        )

    def test_malformed_json_is_reported(self) -> None:
        self.assertEqual(
            self._errors("{not json", "petshop"),
            ["invalid_attributes_json"],
        )

    def test_json_that_is_not_an_object_is_reported(self) -> None:
        self.assertEqual(
            self._errors("[1, 2, 3]", "petshop"),
            ["invalid_attributes_json"],
        )

    def test_only_the_universal_variant_attribute_is_required(self) -> None:
        # CHANGED after the first real scrape. The taxonomy originally
        # required category-specific attributes such as creator, ram_gb and
        # age_range. Measured against real listings none of them appeared in
        # a single title, so they became optional and only variant_label
        # stayed mandatory. See the README for the numbers.
        for category_group, attributes in (
            ("kitap_muzik_hobi", {"variant_label": "Ciltli"}),
            ("elektronik_cep_telefonu", {"variant_label": "256 GB"}),
            ("anne_bebek_oyuncak", {"variant_label": "80'li"}),
            ("spor_outdoor", {"variant_label": "200x200"}),
        ):
            with self.subTest(category_group=category_group):
                self.assertEqual(
                    self._errors(json.dumps(attributes), category_group),
                    [],
                )

    def test_optional_attributes_are_still_range_checked_when_present(
        self,
    ) -> None:
        # Optional does not mean unchecked: a stated value must be sane.
        errors = self._errors(
            json.dumps({"variant_label": "9999 GB", "storage_gb": 9999}),
            "elektronik_cep_telefonu",
        )

        self.assertEqual(errors, ["invalid_attribute_storage_gb"])

    def test_a_missing_optional_attribute_is_not_an_error(self) -> None:
        errors = self._errors(
            json.dumps({"variant_label": "256 GB"}),
            "elektronik_cep_telefonu",
        )

        self.assertEqual(errors, [])

    def test_blank_required_attribute_counts_as_missing(self) -> None:
        errors = self._errors(
            json.dumps({"variant_label": "   ", "creator": "Can Yayınları"}),
            "kitap_muzik_hobi",
        )

        self.assertEqual(errors, ["missing_attribute_variant_label"])

    def test_every_category_requires_only_the_variant_label(self) -> None:
        for group in load_category_groups():
            with self.subTest(group=group.category_group):
                self.assertEqual(
                    group.all_required_attributes(),
                    (UNIVERSAL_ATTRIBUTE,),
                )
                self.assertTrue(group.optional_attributes)

    def test_out_of_range_numeric_attribute_is_reported(self) -> None:
        errors = self._errors(
            json.dumps(
                {
                    "variant_label": "99 kg",
                    "animal_type": "Kedi",
                    "weight_kg": 99,
                }
            ),
            "petshop",
        )

        self.assertEqual(errors, ["invalid_attribute_weight_kg"])

    def test_non_numeric_value_in_a_numeric_attribute_is_reported(
        self,
    ) -> None:
        errors = self._errors(
            json.dumps(
                {
                    "variant_label": "256 GB",
                    "storage_gb": 256,
                    "ram_gb": "sekiz",
                }
            ),
            "elektronik_cep_telefonu",
        )

        self.assertEqual(errors, ["invalid_attribute_ram_gb"])

    def test_range_bounds_are_inclusive(self) -> None:
        for weight in (0.05, 30):
            with self.subTest(weight=weight):
                errors = self._errors(
                    json.dumps(
                        {
                            "variant_label": f"{weight} kg",
                            "animal_type": "Kedi",
                            "weight_kg": weight,
                        }
                    ),
                    "petshop",
                )

                self.assertEqual(errors, [])

    def test_categories_without_numeric_rules_accept_free_text(self) -> None:
        errors = self._errors(
            json.dumps({"variant_label": "Tekli", "room_or_use": "Mutfak"}),
            "ev_yasam_ofis_kirtasiye",
        )

        self.assertEqual(errors, [])


class MultiCategoryKeywordTests(unittest.TestCase):
    """Keyword generation has to work for products without a storage spec."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.products = load_products(PROCESSED_JSON_FILE)
        cls.keywords = json.loads(
            KEYWORDS_FILE.read_text(encoding="utf-8")
        )

    def test_attributes_survive_loading(self) -> None:
        for product in self.products:
            with self.subTest(product_id=product.product_id):
                self.assertIn(product.category_group, ADVISOR_CATEGORY_GROUPS)
                self.assertTrue(product.attributes.get("variant_label"))

    def test_every_product_reports_a_variant_label(self) -> None:
        # Products without one are filtered out during collection, so anything
        # that reaches the processed dataset must carry it.
        for product in self.products:
            with self.subTest(product_id=product.product_id):
                self.assertTrue(product.variant_label())

    def test_keyword_is_the_product_name_plus_buying_intent(self) -> None:
        # These products have no separate model column: the listing title
        # already contains brand, model and variant, so the keyword is that
        # title with the Turkish buying-intent word appended.
        client = FakeKeywordClient()

        for product in self.products[:25]:
            with self.subTest(product_id=product.product_id):
                generated = client.generate_keywords([product])

                self.assertEqual(
                    generated[0].keyword,
                    f"{product.product_name} fiyat",
                )

    def test_committed_keyword_file_covers_every_product(self) -> None:
        self.assertEqual(len(self.keywords), len(self.products))
        self.assertEqual(
            {record["product_id"] for record in self.keywords},
            {product.product_id for product in self.products},
        )
        self.assertEqual(
            len({record["keyword"] for record in self.keywords}),
            len(self.products),
        )
        self.assertTrue(
            all(
                record["keyword"].endswith("fiyat")
                for record in self.keywords
            )
        )


class EvaluationSubsetTests(unittest.TestCase):
    """The 20-product subset used for human-labeled accuracy."""

    @classmethod
    def setUpClass(cls) -> None:
        with SUBSET_FILE.open(
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            cls.subset = list(csv.DictReader(stream))

        cls.processed = {
            row["product_id"]: row
            for row in json.loads(
                PROCESSED_JSON_FILE.read_text(encoding="utf-8")
            )
        }
        cls.keywords = {
            record["product_id"]
            for record in json.loads(
                KEYWORDS_FILE.read_text(encoding="utf-8")
            )
        }

    def test_subset_holds_two_products_from_every_category(self) -> None:
        counts: dict[str, int] = {}

        for row in self.subset:
            counts[row["category_group"]] = (
                counts.get(row["category_group"], 0) + 1
            )

        self.assertEqual(len(self.subset), 20)
        self.assertEqual(
            counts,
            {group: 2 for group in ADVISOR_CATEGORY_GROUPS},
        )

    def test_the_two_products_in_a_category_use_different_brands(
        self,
    ) -> None:
        brands: dict[str, set[str]] = {}

        for row in self.subset:
            brands.setdefault(row["category_group"], set()).add(row["brand"])

        for category_group, category_brands in brands.items():
            with self.subTest(category_group=category_group):
                self.assertEqual(len(category_brands), 2)

    def test_every_subset_product_exists_in_the_processed_dataset(
        self,
    ) -> None:
        for row in self.subset:
            with self.subTest(product_id=row["product_id"]):
                self.assertIn(row["product_id"], self.processed)

                processed_product = self.processed[row["product_id"]]

                self.assertEqual(
                    row["product_name"],
                    processed_product["product_name"],
                )
                self.assertEqual(
                    row["category_group"],
                    processed_product["category_group"],
                )

    def test_every_subset_product_has_a_fixed_keyword(self) -> None:
        for row in self.subset:
            with self.subTest(product_id=row["product_id"]):
                self.assertIn(row["product_id"], self.keywords)


if __name__ == "__main__":
    unittest.main()


class CategorySelectionTests(unittest.TestCase):
    """Locking the narrowed collection, which a short live run needs.

    A listing site rate-limits a long session, so a demonstration is better
    off covering three groups fully than ten partially. Narrowing must stay
    explicit: a name the taxonomy does not carry has to stop the run, because
    a dataset silently covering fewer categories than requested would be
    indistinguishable from one the site cut short.
    """

    def groups(self) -> list[CategoryGroup]:
        return load_category_groups()

    def test_no_names_keeps_every_group(self) -> None:
        groups = self.groups()
        self.assertEqual(select_category_groups(groups, []), groups)

    def test_named_groups_come_back_in_taxonomy_order(self) -> None:
        selected = select_category_groups(
            self.groups(), ["supermarket", "elektronik_cep_telefonu"]
        )
        self.assertEqual(
            [group.category_group for group in selected],
            ["elektronik_cep_telefonu", "supermarket"],
        )

    def test_an_unknown_group_is_refused(self) -> None:
        with self.assertRaises(ScraperError):
            select_category_groups(self.groups(), ["elektronik_cep_telefonu", "nope"])

    def test_the_named_groups_keep_their_own_contract(self) -> None:
        # Narrowing must not relax what a group requires; the product ID
        # prefix and the required attributes have to survive the filter.
        selected = select_category_groups(self.groups(), ["petshop"])
        original = next(
            group for group in self.groups() if group.category_group == "petshop"
        )
        self.assertEqual(selected, [original])
