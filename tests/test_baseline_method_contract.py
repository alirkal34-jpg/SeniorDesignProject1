"""Characterization tests that lock the current scoring and keyword behavior.

Like `test_baseline_data_contract`, these tests record today's behavior rather
than the desired behavior. They cover the three places where the pipeline
currently encodes single-category assumptions:

- the trusted-domain table, which only lists consumer-electronics sellers,
- the deterministic fake NanoLLM scorer and its hard-coded domain keywords,
- the deterministic fake keyword generator, which always appends a storage
  capacity and the Turkish buying-intent word "fiyat".

The Selenium URL helpers are locked as well. They are category-independent, so
those tests are expected to keep passing unchanged through the revision and act
as a control group.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import keyword_generator
import rule_based_evaluator
import selenium_collector
from keyword_generator import (
    FakeKeywordClient,
    KeywordGenerationError,
    OpenRouterKeywordClient,
    Product,
    load_api_keys,
    looks_like_daily_limit,
    validate_keyword_output,
)
from nano_llm_evaluator import (
    FakeNanoLLMEvaluator,
    coerce_relevance_flag,
    validate_evaluation_output,
)
from rule_based_evaluator import (
    DOMAIN_RULES_FILE,
    evaluate_result,
    evaluate_results,
    load_domain_rules,
)
from selenium_collector import extract_domain, normalize_result_url


KEYWORDS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "generated_keywords.json"
)


def make_product(**overrides: object) -> Product:
    """Build one product so each test can vary a single field."""

    values = {
        "product_id": "P001",
        "product_name": "Apple iPhone 16 Pro Max 256 GB",
        "brand": "Apple",
        "model": "iPhone 16 Pro Max",
        "category": "Smartphone",
        "storage_gb": 256,
        "ram_gb": 8,
        "color": "Black Titanium",
    }
    values.update(overrides)
    return Product(**values)


class TrustedDomainTableTests(unittest.TestCase):
    """Freeze the reference table the Rule-Based method depends on."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_domain_rules(DOMAIN_RULES_FILE)

    def test_threshold_is_fixed_at_point_six(self) -> None:
        self.assertEqual(
            rule_based_evaluator.RELEVANCE_THRESHOLD,
            0.60,
        )

    def test_the_committed_domain_table_covers_every_category(self) -> None:
        # CHANGED during the ten-category revision. The table previously held
        # 17 consumer-electronics sellers, which could only score smartphone
        # searches. It now carries 44 domains covering all ten category
        # groups. Re-approve this list before changing it again.
        self.assertEqual(
            {domain: rule["relevance_score"] for domain, rule in self.rules.items()},
            {
                # Category-independent marketplaces and price comparison
                "trendyol.com": 1.0,
                "hepsiburada.com": 1.0,
                "n11.com": 1.0,
                "amazon.com.tr": 1.0,
                "pazarama.com": 1.0,
                "idefix.com": 1.0,
                "ciceksepeti.com": 1.0,
                "akakce.com": 0.85,
                "cimri.com": 0.85,
                "sahibinden.com": 0.9,
                # Elektronik, Cep Telefonu
                "mediamarkt.com.tr": 1.0,
                "teknosa.com": 1.0,
                "vatanbilgisayar.com": 1.0,
                "turkcell.com.tr": 0.9,
                "vodafone.com.tr": 0.9,
                "apple.com": 0.9,
                "samsung.com": 0.9,
                "mi.com": 0.9,
                # Kitap, Müzik, Hobi
                "kitapyurdu.com": 1.0,
                "dr.com.tr": 1.0,
                "bkmkitap.com": 1.0,
                # Sağlık, Bakım, Kozmetik
                "gratis.com": 1.0,
                "watsons.com.tr": 1.0,
                "rossmann.com.tr": 1.0,
                # Süpermarket
                "migros.com.tr": 1.0,
                "carrefoursa.com": 1.0,
                "a101.com.tr": 1.0,
                "sokmarket.com.tr": 1.0,
                "getir.com": 0.9,
                # Saat, Moda, Takı, Ayakkabı
                "boyner.com.tr": 1.0,
                "lcw.com": 1.0,
                "defacto.com.tr": 1.0,
                "flo.com.tr": 1.0,
                "koton.com": 1.0,
                # Anne, Bebek, Oyuncak
                "ebebek.com": 1.0,
                "toyzzshop.com": 1.0,
                # Ev, Yaşam, Ofis / Oto, Bahçe, Yapı Market
                "koctas.com.tr": 1.0,
                "ikea.com.tr": 1.0,
                "bauhaus.com.tr": 1.0,
                "tekzen.com.tr": 1.0,
                "englishhome.com": 0.9,
                "karaca.com": 0.9,
                # Petshop / Spor, Outdoor
                "petlebi.com": 1.0,
                "decathlon.com.tr": 1.0,
            },
        )

    def test_domain_types_are_a_closed_vocabulary(self) -> None:
        self.assertEqual(
            {rule["domain_type"] for rule in self.rules.values()},
            {
                "marketplace",
                "retailer",
                "manufacturer_store",
                "price_comparison",
                "classified_marketplace",
            },
        )

    def test_every_listed_domain_currently_scores_above_the_threshold(
        self,
    ) -> None:
        # No trusted domain can be predicted irrelevant today. Adding a
        # low-confidence domain during the expansion would break this.
        self.assertTrue(
            all(
                rule["relevance_score"]
                >= rule_based_evaluator.RELEVANCE_THRESHOLD
                for rule in self.rules.values()
            )
        )


class RuleBasedScoringTests(unittest.TestCase):
    """Freeze how a single search result is scored against the table."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_domain_rules(DOMAIN_RULES_FILE)

    def test_listed_domain_takes_its_table_score(self) -> None:
        scored = evaluate_result({"domain": "trendyol.com"}, self.rules)

        self.assertEqual(scored["relevance_score"], 1.0)
        self.assertIs(scored["predicted_relevant"], True)

    def test_unlisted_domain_scores_zero(self) -> None:
        scored = evaluate_result({"domain": "teknoseyir.com"}, self.rules)

        self.assertEqual(scored["relevance_score"], 0.0)
        self.assertIs(scored["predicted_relevant"], False)

    def test_domain_lookup_ignores_case_and_surrounding_space(self) -> None:
        scored = evaluate_result({"domain": "  TRENDYOL.com  "}, self.rules)

        self.assertEqual(scored["relevance_score"], 1.0)

    def test_www_prefix_is_not_stripped_during_lookup(self) -> None:
        # The collector is responsible for removing "www."; the evaluator is
        # not. A result that keeps the prefix silently scores zero.
        scored = evaluate_result({"domain": "www.trendyol.com"}, self.rules)

        self.assertEqual(scored["relevance_score"], 0.0)

    def test_missing_domain_key_scores_zero_instead_of_raising(self) -> None:
        scored = evaluate_result({}, self.rules)

        self.assertEqual(scored["relevance_score"], 0.0)
        self.assertIs(scored["predicted_relevant"], False)

    def test_threshold_comparison_is_inclusive(self) -> None:
        synthetic_rules = {
            "exactly-at.example": {
                "domain_type": "retailer",
                "relevance_score": 0.60,
            },
            "just-below.example": {
                "domain_type": "retailer",
                "relevance_score": 0.5999,
            },
        }

        at_threshold = evaluate_result(
            {"domain": "exactly-at.example"},
            synthetic_rules,
        )
        below_threshold = evaluate_result(
            {"domain": "just-below.example"},
            synthetic_rules,
        )

        self.assertIs(at_threshold["predicted_relevant"], True)
        self.assertIs(below_threshold["predicted_relevant"], False)

    def test_scoring_never_mutates_the_incoming_result(self) -> None:
        original = {
            "domain": "trendyol.com",
            "url": "https://www.trendyol.com/p",
            "title": "t",
            "snippet": "s",
        }
        snapshot = dict(original)

        evaluate_result(original, self.rules)

        self.assertEqual(original, snapshot)

    def test_evaluate_results_preserves_input_order(self) -> None:
        scored = evaluate_results(
            [
                {"domain": "teknoseyir.com"},
                {"domain": "trendyol.com"},
                {"domain": "akakce.com"},
            ],
            self.rules,
        )

        self.assertEqual(
            [item["relevance_score"] for item in scored],
            [0.0, 1.0, 0.85],
        )


class DomainRuleLoadingTests(unittest.TestCase):
    """Freeze the guardrails applied when the reference table is loaded."""

    def test_missing_file_is_rejected(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_domain_rules(PROJECT_ROOT / "data" / "reference" / "nope.csv")

    def test_duplicate_domain_is_rejected(self) -> None:
        table = self._write_table(
            "domain,domain_type,relevance_score\n"
            "a.example,retailer,1.0\n"
            "a.example,retailer,0.9\n"
        )

        with self.assertRaises(ValueError):
            load_domain_rules(table)

    def test_score_outside_zero_to_one_is_rejected(self) -> None:
        table = self._write_table(
            "domain,domain_type,relevance_score\n"
            "a.example,retailer,1.5\n"
        )

        with self.assertRaises(ValueError):
            load_domain_rules(table)

    def test_missing_column_is_rejected(self) -> None:
        table = self._write_table("domain,domain_type\na.example,retailer\n")

        with self.assertRaises(ValueError):
            load_domain_rules(table)

    def _write_table(self, content: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "domains.csv"
        path.write_text(content, encoding="utf-8")
        return path


class FakeNanoLlmScoringTests(unittest.TestCase):
    """Freeze the deterministic scorer used by every API-free test."""

    def setUp(self) -> None:
        self.evaluator = FakeNanoLLMEvaluator()

    def test_ecommerce_keyword_list_is_fixed(self) -> None:
        # CHANGED during the ten-category revision. The list previously held
        # nine electronics retailers, so a book or grocery result could never
        # be recognised as e-commerce by the deterministic scorer.
        self.assertEqual(
            self.evaluator.ecommerce_domains,
            (
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
            ),
        )

    def test_ambiguous_brand_names_are_written_as_full_domains(self) -> None:
        # Matching is a plain substring test over domain + title + snippet, so
        # a bare "flo" would fire on "flower" and a bare "dr" on almost any
        # Turkish sentence, inventing e-commerce intent that is not there.
        for bare_name in ("dr", "flo", "lcw"):
            with self.subTest(bare_name=bare_name):
                self.assertNotIn(bare_name, self.evaluator.ecommerce_domains)

        for full_domain in ("dr.com.tr", "flo.com.tr", "lcw.com"):
            with self.subTest(full_domain=full_domain):
                self.assertIn(full_domain, self.evaluator.ecommerce_domains)

    def test_base_score_without_ecommerce_hint_or_overlap(self) -> None:
        score = self._score("zzzz yyyy xxxx", domain="example.com")

        self.assertEqual(score, 0.25)

    def test_ecommerce_hint_raises_the_base_score(self) -> None:
        score = self._score("zzzz yyyy xxxx", domain="trendyol.com")

        self.assertEqual(score, 0.82)

    def test_each_matching_keyword_token_adds_three_hundredths(self) -> None:
        score = self._score(
            "aaa bbb ccc ddd eee fff ggg",
            domain="example.com",
            title="aaa",
        )

        self.assertEqual(score, 0.28)

    def test_only_the_first_five_keyword_tokens_are_counted(self) -> None:
        score = self._score(
            "aaa bbb ccc ddd eee fff ggg",
            domain="example.com",
            title="fff ggg",
        )

        self.assertEqual(score, 0.25)

    def test_tokens_shorter_than_three_characters_are_ignored(self) -> None:
        score = self._score("ab cd ef", domain="example.com", title="ab cd ef")

        self.assertEqual(score, 0.25)

    def test_highest_reachable_score_is_point_nine_seven(self) -> None:
        score = self._score(
            "aaa bbb ccc ddd eee",
            domain="trendyol.com",
            title="aaa bbb ccc ddd eee",
        )

        self.assertEqual(score, 0.97)

    def test_ecommerce_hint_is_matched_anywhere_in_the_result_text(
        self,
    ) -> None:
        # A review page that merely mentions a retailer in its snippet is
        # scored as if it were the retailer. This is a known false-positive
        # source in the reported NanoLLM accuracy.
        score = self._score("aaa", domain="teknoseyir.com", snippet="hepsiburada")

        self.assertEqual(score, 0.82)

    def test_relevance_decision_uses_the_same_point_six_threshold(self) -> None:
        relevant = self.evaluator.evaluate_result(
            "zzzz", {"domain": "trendyol.com", "title": "", "snippet": ""}
        )
        irrelevant = self.evaluator.evaluate_result(
            "zzzz", {"domain": "example.com", "title": "", "snippet": ""}
        )

        self.assertIs(relevant.predicted_relevant, True)
        self.assertIs(irrelevant.predicted_relevant, False)

    def test_evaluation_never_mutates_the_incoming_result(self) -> None:
        original = {"domain": "trendyol.com", "title": "t", "snippet": "s"}
        snapshot = dict(original)

        evaluated = self.evaluator.evaluate_results("aaa", [original])

        self.assertEqual(original, snapshot)
        self.assertEqual(
            sorted(evaluated[0]),
            ["domain", "predicted_relevant", "relevance_score", "snippet", "title"],
        )

    def _score(
        self,
        keyword: str,
        domain: str = "",
        title: str = "",
        snippet: str = "",
    ) -> float:
        return self.evaluator.evaluate_result(
            keyword,
            {"domain": domain, "title": title, "snippet": snippet},
        ).relevance_score


class ApiKeyRotationTests(unittest.TestCase):
    """Spreading a run across several OpenRouter keys.

    The free tier allows 50 model requests per key per day, and one 20-product
    evaluation needs about 80. A second key doubles what fits into a session,
    so a key whose daily allowance is spent is set aside and the next one is
    used instead of failing the experiment.
    """

    def setUp(self) -> None:
        self.daily_limit_body = json.dumps(
            {
                "error": {
                    "message": "Rate limit exceeded: free-models-per-day.",
                    "code": 429,
                    "metadata": {"limit_source": "openrouter_free_tier_daily"},
                }
            }
        )

    def _http_error(self, body: str) -> HTTPError:
        return HTTPError(
            "https://openrouter.ai",
            429,
            "Too Many Requests",
            {"Retry-After": "0"},
            io.BytesIO(body.encode("utf-8")),
        )

    def test_keys_are_read_in_priority_order(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "first",
                "OPENROUTER_API_KEY_2": "second",
                "OPENROUTER_API_KEY_3": "third",
            },
            clear=False,
        ):
            self.assertEqual(load_api_keys(), ["first", "second", "third"])

    def test_numbering_stops_at_the_first_gap(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "first",
                "OPENROUTER_API_KEY_2": "second",
                "OPENROUTER_API_KEY_4": "fourth",
            },
            clear=False,
        ):
            self.assertEqual(load_api_keys(), ["first", "second"])

    def test_duplicate_keys_are_listed_once(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "same",
                "OPENROUTER_API_KEY_2": "same",
            },
            clear=False,
        ):
            self.assertEqual(load_api_keys(), ["same"])

    def test_a_daily_limit_is_told_apart_from_a_transient_one(self) -> None:
        self.assertTrue(looks_like_daily_limit(self.daily_limit_body))
        self.assertFalse(
            looks_like_daily_limit("Rate limit exceeded: requests per minute")
        )

    def test_an_exhausted_key_hands_over_to_the_next_one(self) -> None:
        client = OpenRouterKeywordClient(
            api_keys=["key-a", "key-b"],
            model="test-model",
        )
        used: list[str] = []

        def fake_send(body: bytes) -> dict[str, object]:
            used.append(client.api_key)

            if client.api_key == "key-a":
                raise self._http_error(self.daily_limit_body)

            return {"ok": True}

        client._send = fake_send

        self.assertEqual(client._post_json({"x": 1}), {"ok": True})
        self.assertEqual(used, ["key-a", "key-b"])
        self.assertEqual(client.exhausted_keys, {"key-a"})

    def test_every_key_exhausted_reports_the_rate_limit(self) -> None:
        client = OpenRouterKeywordClient(
            api_keys=["key-a", "key-b"],
            model="test-model",
        )

        def always_limited(body: bytes) -> dict[str, object]:
            raise self._http_error(self.daily_limit_body)

        client._send = always_limited

        with mock.patch.object(keyword_generator, "sleep", lambda _: None):
            with self.assertRaises(KeywordGenerationError) as caught:
                client._post_json({"x": 1})

        self.assertIn("429", str(caught.exception))
        self.assertEqual(client.exhausted_keys, {"key-a", "key-b"})

    def test_a_non_rate_limit_error_is_not_retried_on_another_key(
        self,
    ) -> None:
        client = OpenRouterKeywordClient(
            api_keys=["key-a", "key-b"],
            model="test-model",
        )
        used: list[str] = []

        def server_error(body: bytes) -> dict[str, object]:
            used.append(client.api_key)
            raise HTTPError(
                "https://openrouter.ai",
                500,
                "Server Error",
                {},
                io.BytesIO(b"boom"),
            )

        client._send = server_error

        with self.assertRaises(KeywordGenerationError):
            client._post_json({"x": 1})

        self.assertEqual(used, ["key-a"])

    def test_a_single_key_still_works(self) -> None:
        client = OpenRouterKeywordClient(api_key="only", model="test-model")

        self.assertEqual(client.api_keys, ["only"])
        self.assertEqual(client.api_key, "only")

    def test_no_key_at_all_is_rejected(self) -> None:
        with self.assertRaises(KeywordGenerationError):
            OpenRouterKeywordClient(api_keys=[], model="test-model")


class RelevanceFlagCoercionTests(unittest.TestCase):
    """Normalizing a relevance flag the model spelled differently.

    Added after a live run failed with "predicted_relevant at row 0 must be
    boolean": the configured free model answers with the string "true" or the
    integer 1 often enough to lose experiments, even though its JSON schema
    declares a boolean.
    """

    def test_unambiguous_spellings_are_accepted(self) -> None:
        for value, expected in (
            (True, True),
            (False, False),
            ("true", True),
            ("TRUE", True),
            (" false ", False),
            (1, True),
            (0, False),
            ("1", True),
            ("0", False),
        ):
            with self.subTest(value=value):
                self.assertIs(coerce_relevance_flag(value), expected)

    def test_ambiguous_values_are_still_rejected(self) -> None:
        # Coercion must not become a way of accepting a non-answer.
        for value in ("maybe", "evet", "", None, 0.5, 2, [], {}):
            with self.subTest(value=value):
                self.assertIsNone(coerce_relevance_flag(value))

    def test_validation_accepts_a_string_flag(self) -> None:
        evaluations = validate_evaluation_output(
            {"results": [{"predicted_relevant": "true", "relevance_score": 0.9}]},
            expected_count=1,
        )

        self.assertIs(evaluations[0].predicted_relevant, True)

    def test_validation_rejects_an_ambiguous_flag_and_names_it(self) -> None:
        with self.assertRaises(KeywordGenerationError) as caught:
            validate_evaluation_output(
                {
                    "results": [
                        {"predicted_relevant": "maybe", "relevance_score": 0.9}
                    ]
                },
                expected_count=1,
            )

        self.assertIn("maybe", str(caught.exception))


class FakeKeywordGenerationTests(unittest.TestCase):
    """Freeze the deterministic keyword strings used as pipeline input."""

    def setUp(self) -> None:
        self.client = FakeKeywordClient()

    def test_keyword_is_brand_model_storage_and_the_word_fiyat(self) -> None:
        self.assertEqual(
            self._keyword(),
            "Apple iPhone 16 Pro Max 256 GB fiyat",
        )

    def test_brand_is_not_repeated_when_the_model_already_starts_with_it(
        self,
    ) -> None:
        self.assertEqual(
            self._keyword(brand="Samsung", model="Samsung Galaxy Z Fold"),
            "Samsung Galaxy Z Fold 256 GB fiyat",
        )

    def test_brand_prefix_check_ignores_case(self) -> None:
        self.assertEqual(
            self._keyword(brand="apple", model="Apple Watch", storage_gb=None),
            "Apple Watch fiyat",
        )

    def test_storage_segment_is_dropped_when_capacity_is_missing(self) -> None:
        # Every non-electronics category will hit this path, because only
        # phones and computers carry a storage capacity.
        self.assertEqual(
            self._keyword(
                brand="Xiaomi",
                model="Redmi Note 14",
                storage_gb=None,
            ),
            "Xiaomi Redmi Note 14 fiyat",
        )

    def test_plus_sign_in_the_model_becomes_the_word_plus(self) -> None:
        self.assertEqual(
            self._keyword(model="iPhone 16+", storage_gb=128),
            "Apple iPhone 16 Plus 128 GB fiyat",
        )

    def test_generation_returns_one_keyword_per_product_in_order(self) -> None:
        items = self.client.generate_keywords(
            [
                make_product(product_id="P001"),
                make_product(product_id="P002", model="Galaxy S25", brand="Samsung"),
            ]
        )

        self.assertEqual(
            [item.product_id for item in items],
            ["P001", "P002"],
        )

    def test_committed_keyword_file_covers_p001_to_p100(self) -> None:
        records = json.loads(KEYWORDS_FILE.read_text(encoding="utf-8"))

        self.assertEqual(len(records), 100)
        self.assertEqual(
            [record["product_id"] for record in records],
            [f"P{number:03d}" for number in range(1, 101)],
        )
        self.assertTrue(
            all(
                record["keyword"].endswith("fiyat")
                for record in records
            )
        )

    def _keyword(self, **overrides: object) -> str:
        return self.client.generate_keywords(
            [make_product(**overrides)]
        )[0].keyword


class KeywordValidationTests(unittest.TestCase):
    """Freeze the structured-output guardrails applied to LLM keywords."""

    def test_valid_output_is_accepted(self) -> None:
        items = validate_keyword_output(
            [{"product_id": "P001", "keyword": "Apple iPhone fiyat"}],
            {"P001"},
        )

        self.assertEqual(items[0].keyword, "Apple iPhone fiyat")

    def test_wrapper_object_with_a_keywords_field_is_unwrapped(self) -> None:
        items = validate_keyword_output(
            {"keywords": [{"product_id": "P001", "keyword": "Apple iPhone fiyat"}]},
            {"P001"},
        )

        self.assertEqual(len(items), 1)

    def test_informational_intent_words_are_rejected(self) -> None:
        for banned in ("nasıl", "nedir", "yorum", "blog"):
            with self.subTest(banned=banned):
                with self.assertRaises(KeywordGenerationError):
                    validate_keyword_output(
                        [{"product_id": "P001", "keyword": f"iPhone {banned}"}],
                        {"P001"},
                    )

    def test_keyword_shorter_than_five_characters_is_rejected(self) -> None:
        with self.assertRaises(KeywordGenerationError):
            validate_keyword_output(
                [{"product_id": "P001", "keyword": "abcd"}],
                {"P001"},
            )

    def test_unexpected_duplicate_and_missing_ids_are_rejected(self) -> None:
        with self.assertRaises(KeywordGenerationError):
            validate_keyword_output(
                [{"product_id": "P999", "keyword": "Apple iPhone fiyat"}],
                {"P001"},
            )

        with self.assertRaises(KeywordGenerationError):
            validate_keyword_output(
                [
                    {"product_id": "P001", "keyword": "Apple iPhone fiyat"},
                    {"product_id": "P001", "keyword": "Apple iPhone fiyat"},
                ],
                {"P001"},
            )

        with self.assertRaises(KeywordGenerationError):
            validate_keyword_output(
                [{"product_id": "P001", "keyword": "Apple iPhone fiyat"}],
                {"P001", "P002"},
            )


class SearchResultUrlTests(unittest.TestCase):
    """Freeze the category-independent URL handling of the collector."""

    def test_supported_search_engines_are_google_and_bing(self) -> None:
        self.assertEqual(
            selenium_collector.SUPPORTED_SEARCH_ENGINES,
            ("google", "bing"),
        )

    def test_google_redirect_is_unwrapped(self) -> None:
        self.assertEqual(
            normalize_result_url(
                "https://www.google.com/url"
                "?q=https://www.trendyol.com/p&sa=U"
            ),
            "https://www.trendyol.com/p",
        )

    def test_bing_redirect_is_base64_decoded(self) -> None:
        self.assertEqual(
            normalize_result_url(
                "https://www.bing.com/ck/a?!&&"
                "u=a1aHR0cHM6Ly93d3cudHJlbmR5b2wuY29tL3A&ntb=1"
            ),
            "https://www.trendyol.com/p",
        )

    def test_direct_url_is_returned_unchanged(self) -> None:
        self.assertEqual(
            normalize_result_url("https://www.trendyol.com/apple"),
            "https://www.trendyol.com/apple",
        )

    def test_non_redirect_engine_url_is_returned_unchanged(self) -> None:
        self.assertEqual(
            normalize_result_url("https://www.google.com/search?q=test"),
            "https://www.google.com/search?q=test",
        )

    def test_domain_extraction_lowercases_and_drops_only_the_www_prefix(
        self,
    ) -> None:
        for url, expected in (
            ("https://www.trendyol.com/p", "trendyol.com"),
            ("https://TRENDYOL.com/p", "trendyol.com"),
            ("https://shop.trendyol.com/p", "shop.trendyol.com"),
            ("https://www.trendyol.com:8443/p", "trendyol.com:8443"),
            ("not-a-url", ""),
        ):
            with self.subTest(url=url):
                self.assertEqual(extract_domain(url), expected)


if __name__ == "__main__":
    unittest.main()
