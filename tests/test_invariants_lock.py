"""Regression/invariant lock tests for behavior not pinned down elsewhere.

This suite is intentionally read-only with respect to production code, data,
and reports: every test exercises an existing pure function or fake test
double and asserts on values computed by hand from the current source, the
same way the rest of the suite locks the frozen phone experiment and the
multicategory metrics. Nothing here mutates ``src/``, ``results/``,
``reports/``, or ``reports_multicategory/``.

Scope was chosen after auditing the 23 existing test files for coverage
gaps rather than by guessing:

* ``src/product_scraper.py``'s pure regex-driven helpers
  (``extract_variant_label``, ``derive_scraped_attributes``,
  ``looks_like_bot_challenge``) had no dedicated test file.
* ``src/nano_llm_evaluator.py``'s ``FakeNanoLLMEvaluator`` -- the
  deterministic double every fake-mode pipeline test relies on -- had no
  dedicated test file either, despite being load-bearing for
  ``test_batch_runners.py`` and friends.
* ``result_validator.py``'s ``ALLOWED_METHODS`` set, ``is_number`` helper,
  and the ``execution_mode``/score-boundary edge cases were exercised only
  indirectly (via *some* bad value), never pinned to their exact contract.
* ``calculate_method_metrics`` had no test for the empty-payload-list
  failure mode.

Formula-level locks that already exist (score_predictions' confusion
matrix in test_category_metrics.py, calculate_method_metrics' grouping and
accuracy math in test_metrics.py, URL normalization and label matching in
test_ground_truth.py, most of the result_validator schema checks in
test_result_validator.py, describe_attribute_errors in
test_multicategory_pipeline.py) are deliberately NOT duplicated here.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nano_llm_evaluator import FakeNanoLLMEvaluator, NanoLLMEvaluation  # noqa: E402
from product_scraper import (  # noqa: E402
    derive_scraped_attributes,
    extract_variant_label,
    looks_like_bot_challenge,
)

from evaluation.metrics import MetricsError, calculate_method_metrics  # noqa: E402
from evaluation.result_validator import (  # noqa: E402
    ALLOWED_METHODS,
    REQUIRED_RESULT_FIELDS,
    ResultValidationError,
    is_number,
    validate_result_item,
    validate_result_payload,
)


def make_payload(execution_mode: str = "fake", **overrides) -> dict:
    """Build a minimally valid result payload for schema-boundary tests."""

    payload = {
        "product_id": "P001",
        "keyword": "test keyword",
        "method": "selenium_rule_based",
        "execution_mode": execution_mode,
        "provider": "fake",
        "model": "fake-model",
        "prompt_version": "not_applicable",
        "runtime_seconds": 1.0,
        "estimated_cost_usd": 0.0,
        "results": [
            {
                "domain": "example.com",
                "url": "https://example.com/product",
                "title": "Example product",
                "snippet": "Example snippet",
                "predicted_relevant": True,
                "relevance_score": 0.5,
            }
        ],
    }
    payload.update(overrides)
    return payload


class ExtractVariantLabelLock(unittest.TestCase):
    """Lock the three recognized variant forms and the no-match fallback."""

    def test_number_with_unit_is_recognized(self) -> None:
        self.assertEqual(
            extract_variant_label("iPhone 17 256 GB Siyah"),
            "256 GB",
        )

    def test_decimal_amount_trims_trailing_zero(self) -> None:
        self.assertEqual(
            extract_variant_label("Parfüm 1.50 LT Şişe"),
            "1.5 lt",
        )

    def test_whole_number_amount_is_not_mistakenly_trimmed(self) -> None:
        # A naive "strip trailing zeros" implementation would turn 500 into
        # 5. The code only trims when a decimal point is present.
        self.assertEqual(
            extract_variant_label("Kıyma 500 GR Paket"),
            "500 gr",
        )

    def test_turkish_count_suffix_attaches_without_space(self) -> None:
        self.assertEqual(
            extract_variant_label("5'li Kahve Fincanı Seti"),
            "5'li",
        )

    def test_dimension_form_is_recognized_when_no_unit_present(self) -> None:
        self.assertEqual(
            extract_variant_label("Kamp Çadırı 200x200x145"),
            "200x200x145",
        )

    def test_model_code_form_is_recognized_as_last_resort(self) -> None:
        self.assertEqual(
            extract_variant_label("Casio G-Shock GA-2100-1A1DR"),
            "GA-2100-1A1DR",
        )

    def test_title_with_no_recognizable_variant_yields_empty_string(self) -> None:
        self.assertEqual(
            extract_variant_label("Kırmızı Kalem"),
            "",
        )


class DeriveScrapedAttributesLock(unittest.TestCase):
    """Lock the per-category-group attribute derivation branches."""

    def test_phone_storage_in_gb_is_used_as_is(self) -> None:
        attributes = derive_scraped_attributes(
            "Telefon 256 GB Depolama",
            "elektronik_cep_telefonu",
        )
        self.assertEqual(
            attributes,
            {"variant_label": "256 GB", "storage_gb": 256},
        )

    def test_phone_storage_in_tb_is_converted_to_gb(self) -> None:
        attributes = derive_scraped_attributes(
            "Telefon 2 TB Depolama",
            "elektronik_cep_telefonu",
        )
        self.assertEqual(
            attributes,
            {"variant_label": "2 TB", "storage_gb": 2048},
        )

    def test_petshop_derives_weight_and_animal_type_together(self) -> None:
        attributes = derive_scraped_attributes(
            "Kedi Maması 2 KG Somonlu",
            "petshop",
        )
        self.assertEqual(
            attributes,
            {
                "variant_label": "2 kg",
                "weight_kg": 2.0,
                "animal_type": "Kedi",
            },
        )

    def test_category_with_no_matching_branch_only_gets_variant_label(self) -> None:
        # kitap_kirtasiye has no elif branch, so a present unit does not
        # produce extra attributes for it.
        attributes = derive_scraped_attributes(
            "Roman Kitabı 500 GR",
            "kitap_kirtasiye",
        )
        self.assertEqual(
            attributes,
            {"variant_label": "500 gr"},
        )


class BotChallengeDetectionLock(unittest.TestCase):
    """Lock the case-insensitive substring match against known markers."""

    def test_ascii_marker_matches_regardless_of_case(self) -> None:
        self.assertTrue(
            looks_like_bot_challenge(
                "Please wait -- CHECKING YOUR BROWSER before continuing"
            )
        )

    def test_turkish_marker_matches_as_written_in_source(self) -> None:
        self.assertTrue(
            looks_like_bot_challenge(
                "Sayfa yükleniyor... güvenlik doğrulaması bekleniyor"
            )
        )

    def test_ordinary_listing_html_is_not_a_challenge(self) -> None:
        self.assertFalse(
            looks_like_bot_challenge(
                "<div class='product'>iPhone 16 Pro Max 256 GB - 89.999 TL"
                "</div>"
            )
        )


class FakeNanoLLMEvaluatorLock(unittest.TestCase):
    """Lock the deterministic scoring formula every fake-mode test depends on.

    evaluate_result: score starts at 0.25, jumps to 0.82 if any e-commerce
    domain substring is present, then gains 0.03 per overlapping keyword
    token (checking only the first 5 tokens of length >= 3), capped at 1.0.
    predicted_relevant is score >= 0.60.
    """

    def setUp(self) -> None:
        self.evaluator = FakeNanoLLMEvaluator()

    def test_non_ecommerce_domain_scores_the_baseline(self) -> None:
        evaluation = self.evaluator.evaluate_result(
            keyword="test kelime",
            result={
                "domain": "somenews.com",
                "title": "Haberler",
                "snippet": "",
            },
        )
        self.assertEqual(
            evaluation,
            NanoLLMEvaluation(predicted_relevant=False, relevance_score=0.25),
        )

    def test_ecommerce_domain_scores_above_threshold_with_no_overlap(self) -> None:
        evaluation = self.evaluator.evaluate_result(
            keyword="test kelime",
            result={
                "domain": "akakce.com",
                "title": "Ürün",
                "snippet": "",
            },
        )
        self.assertEqual(
            evaluation,
            NanoLLMEvaluation(predicted_relevant=True, relevance_score=0.82),
        )

    def test_keyword_overlap_adds_a_fixed_increment_per_token(self) -> None:
        evaluation = self.evaluator.evaluate_result(
            keyword="iphone 16 pro max",
            result={
                "domain": "hepsiburada.com",
                "title": "iPhone 16 Pro Max 256 GB Titanyum",
                "snippet": "Apple akilli telefon",
            },
        )
        # "16" is dropped (length < 3); "iphone", "pro", "max" overlap.
        self.assertEqual(
            evaluation,
            NanoLLMEvaluation(predicted_relevant=True, relevance_score=0.91),
        )

    def test_overlap_bonus_only_checks_the_first_five_keyword_tokens(self) -> None:
        evaluation = self.evaluator.evaluate_result(
            keyword="iphone pro max titanyum apple ekstra fazladan",
            result={
                "domain": "hepsiburada.com",
                "title": "iPhone Pro Max Titanyum Apple Urunu",
                "snippet": "",
            },
        )
        # 7 eligible tokens exist but only the first 5 are checked, and all
        # 5 are present, so this is the highest score the formula can
        # produce in practice: 0.82 + 5 * 0.03 = 0.97. It never reaches the
        # 1.0 cap because the base score is only ever 0.25 or 0.82.
        self.assertEqual(
            evaluation,
            NanoLLMEvaluation(predicted_relevant=True, relevance_score=0.97),
        )

    def test_predicted_relevant_is_fully_decided_by_domain_membership(self) -> None:
        """Keyword overlap can never flip predicted_relevant either way.

        Non-ecommerce max score is 0.25 + 5*0.03 = 0.40 (< 0.60); ecommerce
        min score is 0.82 (>= 0.60). The overlap bonus only fine-tunes
        relevance_score within a domain-membership bucket. This is worth
        locking explicitly: a test that swaps in a "hard" keyword expecting
        FakeNanoLLMEvaluator to reject an ecommerce result based on keyword
        mismatch would be testing behavior the fake does not have.
        """

        non_ecommerce_max_overlap = self.evaluator.evaluate_result(
            keyword="urun model kod seri numara ekstra",
            result={
                "domain": "somenews.com",
                "title": "Urun Model Kod Seri Numara Bilgisi",
                "snippet": "",
            },
        )
        self.assertFalse(non_ecommerce_max_overlap.predicted_relevant)

        ecommerce_zero_overlap = self.evaluator.evaluate_result(
            keyword="alakasiz sorgu metni",
            result={
                "domain": "trendyol.com",
                "title": "Baska Bir Urun",
                "snippet": "",
            },
        )
        self.assertTrue(ecommerce_zero_overlap.predicted_relevant)

    def test_evaluate_results_extends_without_mutating_the_input(self) -> None:
        original_results = [
            {
                "domain": "akakce.com",
                "title": "Urun A",
                "snippet": "Fiyat bilgisi",
            },
            {
                "domain": "somenews.com",
                "title": "Haber B",
                "snippet": "",
            },
        ]
        snapshot = [dict(item) for item in original_results]

        evaluated = self.evaluator.evaluate_results(
            "test kelime",
            original_results,
        )

        self.assertEqual(original_results, snapshot)
        self.assertEqual(len(evaluated), 2)
        for item in evaluated:
            self.assertIsInstance(item["predicted_relevant"], bool)
            self.assertIsInstance(item["relevance_score"], float)
            self.assertTrue(0.0 <= item["relevance_score"] <= 1.0)

    def test_fake_evaluator_output_passes_the_real_schema_validator(self) -> None:
        """Structural-integrity lock: the fake's output is schema-valid.

        FakeNanoLLMEvaluator stands in for the real NanoLLM API in every
        fake-mode pipeline test. If its output shape ever drifted from what
        result_validator.validate_result_item enforces, those tests could
        keep passing against a double that no longer resembles a real
        result -- silently. This pins the two together directly.
        """

        raw_results = [
            {
                "domain": "trendyol.com",
                "url": "https://www.trendyol.com/urun/example",
                "title": "Ornek Urun",
                "snippet": "899 TL",
            },
        ]

        evaluated = self.evaluator.evaluate_results(
            "ornek urun",
            raw_results,
        )

        self.assertEqual(REQUIRED_RESULT_FIELDS - evaluated[0].keys(), set())
        validate_result_item(evaluated[0], index=0, source="<fake-evaluator>")


class ResultValidatorContractLock(unittest.TestCase):
    """Lock the parts of result_validator.py's contract not already pinned.

    test_result_validator.py already locks: valid-payload acceptance,
    missing required fields, unsupported method, negative runtime,
    out-of-range score, non-boolean predicted_relevant, empty/oversized
    results, invalid JSON, and live-with-fake-provider rejection. This
    class covers what was left: the ALLOWED_METHODS set's exact content,
    score-boundary inclusiveness, the is_number helper in isolation, and
    an invalid (neither fake nor live) execution_mode.
    """

    def test_allowed_methods_is_exactly_the_four_evaluation_methods(self) -> None:
        # A silent addition or removal here would change what
        # ground_truth.py accepts in its CSV 'method' column and what
        # category_metrics.py groups by, without any single obvious
        # failure pointing back at this set.
        self.assertEqual(
            ALLOWED_METHODS,
            {
                "tavily_llm",
                "agentic_search",
                "selenium_nano_llm",
                "selenium_rule_based",
            },
        )

    def test_relevance_score_boundary_values_are_accepted(self) -> None:
        for boundary_score in (0.0, 1.0):
            with self.subTest(score=boundary_score):
                item = {
                    "domain": "example.com",
                    "url": "https://example.com/x",
                    "title": "Title",
                    "snippet": "",
                    "predicted_relevant": True,
                    "relevance_score": boundary_score,
                }
                # Must not raise.
                validate_result_item(item, index=0, source="<test>")

    def test_execution_mode_outside_fake_or_live_is_rejected(self) -> None:
        payload = make_payload(execution_mode="mock")
        with self.assertRaises(ResultValidationError):
            validate_result_payload(payload)

    def test_is_number_rejects_booleans(self) -> None:
        # bool is a subclass of int in Python; is_number explicitly guards
        # against True/False being accepted as 1/0.
        self.assertFalse(is_number(True))
        self.assertFalse(is_number(False))

    def test_is_number_rejects_non_finite_values(self) -> None:
        self.assertFalse(is_number(float("nan")))
        self.assertFalse(is_number(float("inf")))
        self.assertFalse(is_number(float("-inf")))

    def test_is_number_accepts_ordinary_int_and_float(self) -> None:
        self.assertTrue(is_number(0))
        self.assertTrue(is_number(3.5))


class MetricsEdgeCaseLock(unittest.TestCase):
    """The one gap in test_metrics.py's coverage: an empty payload list."""

    def test_empty_payload_list_is_refused(self) -> None:
        with self.assertRaises(MetricsError):
            calculate_method_metrics([])


if __name__ == "__main__":
    unittest.main()
