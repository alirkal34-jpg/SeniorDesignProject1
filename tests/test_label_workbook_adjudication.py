"""Unit tests for importing review workbooks and settling unresolved rows.

The import is the only path from the reviewers' spreadsheets to the ground
truth every accuracy number is measured against, so these tests pin down both
halves of its contract: what a completed workbook turns into, and what happens
to a row the reviewer deliberately left open.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.export_label_workbook import review_url_key  # noqa: E402
from evaluation.ground_truth import normalize_url  # noqa: E402
from evaluation.import_label_workbook import (  # noqa: E402
    LabelImportError,
    build_ground_truth_records,
    load_adjudications,
    parse_label,
)


ADJUDICATION_HEADER = (
    "product_id,url,resolved_label,rule,adjudicated_by\n"
)


def workbook_row(
    product_id: str = "SPM001",
    keyword: str = "Eti Burçak Sütlü Çikolatalı Bisküvi 114 gr fiyat",
    domain: str = "trendyol.com",
    url: str = "https://www.trendyol.com/eti/burcak-114-gr-p-1",
    human_relevant: Any = "true",
    human_note: str = "",
    reviewer: str = "atahan",
    sheet_row: int = 2,
) -> dict[str, Any]:
    """Build one row in the shape ``read_workbook_rows`` produces."""

    return {
        "product_id": product_id,
        "keyword": keyword,
        "domain": domain,
        "url": url,
        "human_relevant": human_relevant,
        "human_note": human_note,
        "reviewer": reviewer,
        "_sheet_row": sheet_row,
    }


class ParseLabelTests(unittest.TestCase):
    """Pin down which reviewer answers count as an answer at all."""

    def test_accepts_turkish_and_english_true_values(self) -> None:
        for value in ("true", "TRUE", " Evet ", "1", "yes", "doğru"):
            with self.subTest(value=value):
                self.assertIs(parse_label(value), True)

    def test_accepts_turkish_and_english_false_values(self) -> None:
        for value in ("false", "hayır", "0", "no", "yanlış"):
            with self.subTest(value=value):
                self.assertIs(parse_label(value), False)

    def test_booleans_survive_openpyxl_type_coercion(self) -> None:
        self.assertIs(parse_label(True), True)
        self.assertIs(parse_label(False), False)

    def test_hedged_answer_is_not_a_label(self) -> None:
        # 'true?' is how a reviewer flags a row for adjudication. It must
        # never be read as agreement with 'true'.
        for value in ("true?", "false?", "", None, "belki", "?"):
            with self.subTest(value=value):
                self.assertIsNone(parse_label(value))


class ReviewUrlKeyTests(unittest.TestCase):
    """The workbook must count pages the same way the metrics do."""

    def test_key_matches_the_metrics_normalization(self) -> None:
        url = "https://www.tefal.com.tr/ingenio-11-parca-2100129672"

        # Any drift between these two is what puts one page in front of a
        # reviewer twice, so they are asserted equal rather than merely
        # similar.
        self.assertEqual(review_url_key(url), normalize_url(url))

    def test_trailing_slash_is_the_same_page(self) -> None:
        self.assertEqual(
            review_url_key("https://www.tefal.com.tr/ingenio-2100129672/"),
            review_url_key("https://www.tefal.com.tr/ingenio-2100129672"),
        )

    def test_host_casing_is_the_same_page(self) -> None:
        self.assertEqual(
            review_url_key("https://WWW.Trendyol.com/eti-p-1"),
            review_url_key("https://www.trendyol.com/eti-p-1"),
        )

    def test_query_string_still_separates_pages(self) -> None:
        # Marketplace variant filters live in the query string, so two URLs
        # that differ there are genuinely different listings.
        self.assertNotEqual(
            review_url_key("https://www.hepsiburada.com/molfix?beden=6"),
            review_url_key("https://www.hepsiburada.com/molfix?beden=5"),
        )

    def test_unnormalizable_url_is_kept_instead_of_dropped(self) -> None:
        self.assertEqual(
            review_url_key(" MAILTO:Shop@example.com "),
            "mailto:shop@example.com",
        )


class BuildGroundTruthRecordTests(unittest.TestCase):
    """Lock the conversion from reviewed rows to ground-truth records."""

    def test_label_is_shared_across_every_method(self) -> None:
        records = build_ground_truth_records([workbook_row()])

        self.assertEqual(len(records), 1)
        # A blank method is what makes the four methods comparable: each URL
        # carries one label no matter which method surfaced it.
        self.assertEqual(records[0]["method"], "")
        self.assertEqual(records[0]["human_relevant"], "true")

    def test_reviewer_name_is_kept_in_the_notes(self) -> None:
        records = build_ground_truth_records(
            [workbook_row(human_note="kategori sayfası")]
        )

        self.assertIn("kategori sayfası", records[0]["notes"])
        self.assertIn("[reviewer: atahan]", records[0]["notes"])

    def test_unreadable_label_fails_the_whole_import(self) -> None:
        rows = [
            workbook_row(),
            workbook_row(
                product_id="SPM003",
                url="https://www.trendyol.com/lotus-250-g-x10-p-2",
                human_relevant="true?",
                sheet_row=3,
            ),
        ]

        with self.assertRaises(LabelImportError) as error:
            build_ground_truth_records(rows)

        message = str(error.exception)
        self.assertIn("Row 3", message)
        self.assertIn("SPM003", message)
        self.assertIn("'true?'", message)

    def test_one_page_labeled_twice_the_same_way_becomes_one_record(
        self,
    ) -> None:
        # The exporter once deduplicated on the raw URL while the metrics
        # matched on the normalized one, so a trailing slash was enough to
        # send one page to the reviewer twice and then collide on import.
        rows = [
            workbook_row(),
            workbook_row(
                url="https://www.trendyol.com/eti/burcak-114-gr-p-1/",
                sheet_row=3,
            ),
        ]

        records = build_ground_truth_records(rows)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["human_relevant"], "true")

    def test_host_casing_does_not_split_one_page_in_two(self) -> None:
        rows = [
            workbook_row(),
            workbook_row(
                url="https://WWW.TRENDYOL.COM/eti/burcak-114-gr-p-1",
                sheet_row=3,
            ),
        ]

        self.assertEqual(len(build_ground_truth_records(rows)), 1)

    def test_contradictory_labels_for_one_page_stop_the_import(self) -> None:
        rows = [
            workbook_row(human_relevant="true"),
            workbook_row(
                url="https://www.trendyol.com/eti/burcak-114-gr-p-1/",
                human_relevant="false",
                sheet_row=3,
            ),
        ]

        with self.assertRaises(LabelImportError) as error:
            build_ground_truth_records(rows)

        message = str(error.exception)
        self.assertIn("contradictory", message)
        self.assertIn("Row 2", message)
        self.assertIn("Row 3", message)

    def test_different_pages_are_kept_apart(self) -> None:
        rows = [
            workbook_row(),
            workbook_row(
                url="https://www.trendyol.com/eti/burcak-114-gr-p-2",
                sheet_row=3,
            ),
        ]

        self.assertEqual(len(build_ground_truth_records(rows)), 2)

    def test_rows_from_several_workbooks_merge_into_one_file(self) -> None:
        first = workbook_row()
        first["_workbook"] = "label_review_session1.xlsx"
        second = workbook_row(
            product_id="SPM003",
            url="https://www.trendyol.com/lotus-250-g-p-2",
            human_relevant="false",
        )
        second["_workbook"] = "label_review_session2.xlsx"

        records = build_ground_truth_records([first, second])

        self.assertEqual(
            [record["human_relevant"] for record in records],
            ["true", "false"],
        )

    def test_workbook_name_appears_in_multi_session_errors(self) -> None:
        row = workbook_row(human_relevant="true?", sheet_row=41)
        row["_workbook"] = "label_review_session2.xlsx"

        with self.assertRaises(LabelImportError) as error:
            build_ground_truth_records([row])

        self.assertIn(
            "label_review_session2.xlsx row 41",
            str(error.exception),
        )


class AdjudicationTests(unittest.TestCase):
    """An unresolved row is settled by a traceable decision, or not at all."""

    def write_adjudication(self, content: str) -> Path:
        temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temp_directory.cleanup)
        file_path = Path(temp_directory.name) / "adjudications.csv"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def adjudication_for(
        self,
        product_id: str = "SPM001",
        url: str = "https://www.trendyol.com/eti/burcak-114-gr-p-1",
        resolved_label: str = "false",
        rule: str = "multipack listing",
        adjudicated_by: str = "claude",
    ) -> dict[tuple[str, str], dict[str, str]]:
        file_path = self.write_adjudication(
            ADJUDICATION_HEADER
            + f"{product_id},{url},{resolved_label},{rule},{adjudicated_by}\n"
        )
        return load_adjudications(file_path)

    def test_unresolved_row_takes_the_adjudicated_label(self) -> None:
        records = build_ground_truth_records(
            [workbook_row(human_relevant="true?", human_note="emin değilim")],
            self.adjudication_for(),
        )

        self.assertEqual(records[0]["human_relevant"], "false")

    def test_adjudicated_row_carries_its_reasoning(self) -> None:
        records = build_ground_truth_records(
            [workbook_row(human_relevant="true?")],
            self.adjudication_for(),
        )

        notes = records[0]["notes"]
        # The raw answer, the rule and the decider all have to survive into
        # the ground truth so the decision can be audited or reversed.
        self.assertIn("reviewer wrote 'true?'", notes)
        self.assertIn("resolved to false", notes)
        self.assertIn("multipack listing", notes)
        self.assertIn("by: claude", notes)

    def test_adjudication_cannot_overturn_an_answered_row(self) -> None:
        with self.assertRaises(LabelImportError) as error:
            build_ground_truth_records(
                [workbook_row(human_relevant="true")],
                self.adjudication_for(resolved_label="false"),
            )

        message = str(error.exception)
        self.assertIn("must not be adjudicated", message)
        self.assertIn("'true'", message)

    def test_adjudication_matching_no_row_fails_the_import(self) -> None:
        with self.assertRaises(LabelImportError) as error:
            build_ground_truth_records(
                [workbook_row(human_relevant="true")],
                self.adjudication_for(
                    product_id="SPM009",
                    url="https://www.trendyol.com/gone-p-9",
                ),
            )

        message = str(error.exception)
        self.assertIn("matched no workbook row", message)
        self.assertIn("SPM009", message)

    def test_matching_ignores_case_and_padding(self) -> None:
        records = build_ground_truth_records(
            [workbook_row(human_relevant="true?")],
            self.adjudication_for(
                product_id=" spm001 ",
                url=" https://www.Trendyol.com/eti/burcak-114-gr-p-1 ",
            ),
        )

        self.assertEqual(records[0]["human_relevant"], "false")

    def test_unresolved_row_without_adjudication_still_fails(self) -> None:
        rows = [
            workbook_row(human_relevant="true?"),
            workbook_row(
                product_id="SPM003",
                url="https://www.trendyol.com/lotus-p-2",
                human_relevant="true?",
                sheet_row=3,
            ),
        ]

        with self.assertRaises(LabelImportError) as error:
            build_ground_truth_records(rows, self.adjudication_for())

        message = str(error.exception)
        self.assertIn("SPM003", message)
        self.assertNotIn("SPM001", message)


class LoadAdjudicationTests(unittest.TestCase):
    """The decision file has to be complete before it can settle anything."""

    def write_adjudication(self, content: str) -> Path:
        temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temp_directory.cleanup)
        file_path = Path(temp_directory.name) / "adjudications.csv"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_missing_file_is_reported_by_path(self) -> None:
        missing_path = Path("data") / "labels" / "not_here.csv"

        with self.assertRaises(LabelImportError) as error:
            load_adjudications(missing_path)

        self.assertIn("not_here.csv", str(error.exception))

    def test_missing_columns_are_named(self) -> None:
        file_path = self.write_adjudication(
            "product_id,url,resolved_label\nSPM001,https://a.example,false\n"
        )

        with self.assertRaises(LabelImportError) as error:
            load_adjudications(file_path)

        message = str(error.exception)
        self.assertIn("rule", message)
        self.assertIn("adjudicated_by", message)

    def test_decision_without_a_rule_is_refused(self) -> None:
        file_path = self.write_adjudication(
            ADJUDICATION_HEADER
            + "SPM001,https://a.example,false,,claude\n"
        )

        with self.assertRaises(LabelImportError) as error:
            load_adjudications(file_path)

        self.assertIn("traceable", str(error.exception))

    def test_hedged_resolution_is_refused(self) -> None:
        file_path = self.write_adjudication(
            ADJUDICATION_HEADER
            + "SPM001,https://a.example,maybe,some rule,claude\n"
        )

        with self.assertRaises(LabelImportError) as error:
            load_adjudications(file_path)

        self.assertIn("resolved_label", str(error.exception))

    def test_duplicate_decisions_are_refused(self) -> None:
        file_path = self.write_adjudication(
            ADJUDICATION_HEADER
            + "SPM001,https://a.example,false,rule one,claude\n"
            + "SPM001,https://a.example,true,rule two,claude\n"
        )

        with self.assertRaises(LabelImportError) as error:
            load_adjudications(file_path)

        self.assertIn("duplicate", str(error.exception).casefold())

    def test_empty_file_is_refused(self) -> None:
        file_path = self.write_adjudication(ADJUDICATION_HEADER)

        with self.assertRaises(LabelImportError) as error:
            load_adjudications(file_path)

        self.assertIn("no decisions", str(error.exception))


if __name__ == "__main__":
    unittest.main()
