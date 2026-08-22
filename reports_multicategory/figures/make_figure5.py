"""Render Figure 5, the system architecture, as a print-ready SVG.

The figure is generated rather than drawn so it can be corrected when the
architecture changes, the same way every other number in this report is
recomputed rather than retyped. Coordinates come from a three-column grid:
what a stage reads on the left, the module that runs on it in the middle,
what the stage writes on the right. Reading a row therefore answers "which
file did this produce", which is the question the figure exists for.

Both languages are rendered from one layout and one text table, so a label
cannot be corrected in one language and left stale in the other.

    python reports_multicategory/figures/make_figure5.py

Writes figure5_system_architecture_EN.svg and sekil5_sistem_mimarisi_TR.svg
next to this file. SVG keeps its quality at any size in Word and in print; a
PNG would not.
"""

from __future__ import annotations

from pathlib import Path


HERE = Path(__file__).resolve().parent
OUTPUTS = {
    "en": HERE / "figure5_system_architecture_EN.svg",
    "tr": HERE / "sekil5_sistem_mimarisi_TR.svg",
}

WIDTH = 1020
FONT = "Segoe UI, Calibri, Arial, sans-serif"
MONO = "Consolas, Courier New, monospace"

# One palette, chosen to stay legible in greyscale print: the fills differ in
# lightness as well as in hue.
STYLES = {
    "module": ("#DCE9F7", "#2C5D8F", "#123A5E"),
    "artifact": ("#F2F2F0", "#7A7A72", "#33332E"),
    "external": ("#FBE6CC", "#B9770E", "#6B4406"),
    "human": ("#E3F1E4", "#3B7D42", "#1E4722"),
    "method": ("#E7E1F5", "#5B47A0", "#2E2258"),
}

COL = {
    "left": (40, 240),
    "centre": (320, 300),
    "right": (660, 320),
    "wide": (40, 940),
}

ROW_HEIGHT = 52
ROW_PITCH = 74

# Every piece of prose in the figure, in both languages. Filenames and module
# names are deliberately not translated: they are what a reader looks for on
# disk, and translating them would make the figure disagree with the code.
TEXT: dict[str, dict[str, str]] = {
    "layer_data": {"en": "DATA LAYER", "tr": "VERİ KATMANI"},
    "layer_eval": {"en": "EVALUATION LAYER", "tr": "DEĞERLENDİRME KATMANI"},
    "layer_measure": {
        "en": "MEASUREMENT AND REPORTING LAYER",
        "tr": "ÖLÇÜM VE RAPORLAMA KATMANI",
    },
    "taxonomy_sub": {"en": "10 category groups", "tr": "10 kategori grubu"},
    "akakce": {"en": "Akakçe", "tr": "Akakçe"},
    "akakce_sub": {"en": "external source", "tr": "dış kaynak"},
    "raw_sub": {
        "en": "+ .metadata.json — scraped, 489 products",
        "tr": "+ .metadata.json — scraped, 489 ürün",
    },
    "catalog_sub": {
        "en": "offline fallback — reads the same taxonomy",
        "tr": "çevrimdışı yedek — aynı taksonomiyi okur",
    },
    "synthetic_sub": {"en": "stamped synthetic", "tr": "synthetic damgalı"},
    "processor_sub": {
        "en": "schema + cleaning + row validation",
        "tr": "şema + temizlik + satır doğrulama",
    },
    "processed_sub": {
        "en": "489 records  +  validation_issues_...csv",
        "tr": "489 kayıt  +  validation_issues_...csv",
    },
    "quality_sub": {"en": "dataset-level gate", "tr": "veri kümesi düzeyi kapı"},
    "quality_note": {
        "en": "PASSED / FAILED report — writes no file, does not stop the flow",
        "tr": "PASSED / FAILED raporu — dosya yazmaz, akışı durdurmaz",
    },
    "keywords_sub": {
        "en": "one keyword per product",
        "tr": "ürün başına 1 anahtar kelime",
    },
    "batch_sub": {
        "en": "produces the 80 runs reported here",
        "tr": "rapordaki 80 koşumu üretir",
    },
    "langgraph_sub": {
        "en": "same four methods, LangGraph graph (Figure 1)",
        "tr": "aynı dört yöntem, LangGraph çizgesi (Şekil 1)",
    },
    "m1": {"en": "Selenium + Rule-Based", "tr": "Selenium + Kural Tabanlı"},
    "m2": {"en": "Selenium + NanoLLM", "tr": "Selenium + NanoLLM"},
    "m3": {"en": "Tavily + NanoLLM", "tr": "Tavily + NanoLLM"},
    "m4": {"en": "Agentic Search", "tr": "Agentic Search"},
    "m1_src": {
        "en": "Bing (Selenium) + domain table",
        "tr": "Bing (Selenium) + kural tablosu",
    },
    "m1_src_sub": {"en": "threshold 0.60 — no model", "tr": "eşik 0,60 — model yok"},
    "m2_src": {
        "en": "Bing (Selenium) + OpenRouter",
        "tr": "Bing (Selenium) + OpenRouter",
    },
    "m3_src": {"en": "Tavily API + OpenRouter", "tr": "Tavily API + OpenRouter"},
    "m4_src": {
        "en": "Bing (Selenium) + OpenRouter",
        "tr": "Bing (Selenium) + OpenRouter",
    },
    "m4_src_sub": {"en": "planner + evaluator", "tr": "planlayıcı + değerlendirici"},
    "results": {
        "en": "results_multicategory/&lt;method&gt;/*.json",
        "tr": "results_multicategory/&lt;yöntem&gt;/*.json",
    },
    "results_sub": {
        "en": "80 files — 20 products × 4 methods, 399 results",
        "tr": "80 dosya — 20 ürün × 4 yöntem, 399 sonuç",
    },
    "validator": {
        "en": "result_validator.py — shared JSON schema",
        "tr": "result_validator.py — ortak JSON şeması",
    },
    "export_sub": {"en": "model predictions hidden", "tr": "model tahminleri gizli"},
    "workbook1": {
        "en": "label_review_session1.xlsx — 134 URLs",
        "tr": "label_review_session1.xlsx — 134 URL",
    },
    "workbook2": {
        "en": "label_review_session2.xlsx — 61 URLs",
        "tr": "label_review_session2.xlsx — 61 URL",
    },
    "reviewer": {"en": "Human reviewer", "tr": "İnsan değerlendirici"},
    "reviewer_sub": {
        "en": "193 unique URLs labeled by hand",
        "tr": "193 benzersiz URL elle etiketlenir",
    },
    "adjudication_sub": {
        "en": "adjudications.csv — 5 decisions",
        "tr": "adjudications.csv — 5 karar",
    },
    "ground_truth_sub": {
        "en": "193 labels — 140 relevant / 53 irrelevant",
        "tr": "193 etiket — 140 uygun / 53 uygunsuz",
    },
    "manifest_sub": {
        "en": "multicategory.json — 80 files frozen",
        "tr": "multicategory.json — 80 dosya donduruldu",
    },
    "final_metrics_sub": {"en": "overall metrics", "tr": "genel metrikler"},
    "category_metrics_sub": {"en": "per category", "tr": "kategori bazında"},
}


class Figure:
    def __init__(self, language: str) -> None:
        self.language = language
        self.parts: list[str] = []
        self.boxes: dict[str, tuple[float, float, float, float]] = {}
        self.cursor = 0.0

    def say(self, key: str) -> str:
        return TEXT[key][self.language]

    # -- geometry -----------------------------------------------------
    def band(self, key: str, rows: int) -> float:
        top = self.cursor
        height = 46 + rows * ROW_PITCH
        self.parts.append(
            f'<rect x="16" y="{top:.0f}" width="{WIDTH - 32}" height="{height:.0f}" '
            'rx="10" fill="#FFFFFF" stroke="#B9B9B4" stroke-width="1.5"/>'
        )
        self.parts.append(
            f'<rect x="16" y="{top:.0f}" width="{WIDTH - 32}" height="34" '
            'rx="10" fill="#4A4A45"/>'
        )
        self.parts.append(
            f'<rect x="16" y="{top + 24:.0f}" width="{WIDTH - 32}" '
            'height="10" fill="#4A4A45"/>'
        )
        self.parts.append(
            f'<text x="{WIDTH / 2:.0f}" y="{top + 23:.0f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="15" font-weight="600" '
            f'fill="#FFFFFF" letter-spacing="1.4">{self.say(key)}</text>'
        )
        self.cursor = top + height + 26
        return top + 46

    def box(
        self,
        name: str,
        column: str,
        top: float,
        lines: list[str],
        kind: str = "module",
        x: float | None = None,
        width: float | None = None,
        height: float = ROW_HEIGHT,
    ) -> None:
        base_x, base_width = COL[column]
        left = base_x if x is None else x
        box_width = base_width if width is None else width
        fill, stroke, text_colour = STYLES[kind]

        self.boxes[name] = (left, top, box_width, height)
        self.parts.append(
            f'<rect x="{left:.0f}" y="{top:.0f}" width="{box_width:.0f}" '
            f'height="{height:.0f}" rx="6" fill="{fill}" stroke="{stroke}" '
            'stroke-width="1.5"/>'
        )

        step = 15
        start = top + height / 2 - (len(lines) - 1) * step / 2 + 5
        for index, line in enumerate(lines):
            mono = line.endswith(".py") or ("." in line and "/" in line)
            size = 12.5 if index == 0 else 11
            self.parts.append(
                f'<text x="{left + box_width / 2:.0f}" '
                f'y="{start + index * step:.0f}" text-anchor="middle" '
                f'font-family="{MONO if mono else FONT}" '
                f'font-size="{size}" fill="{text_colour}">{line}</text>'
            )

    # -- connectors ---------------------------------------------------
    def arrow(self, points: list[tuple[float, float]]) -> None:
        path = " ".join(
            ("M" if index == 0 else "L") + f"{x:.0f},{y:.0f}"
            for index, (x, y) in enumerate(points)
        )
        self.parts.append(
            f'<path d="{path}" fill="none" stroke="#5A5A55" stroke-width="1.6" '
            'marker-end="url(#head)"/>'
        )

    def down(self, source: str, target: str) -> None:
        sx, sy, sw, sh = self.boxes[source]
        tx, ty, tw, _ = self.boxes[target]
        start = (sx + sw / 2, sy + sh)
        end = (tx + tw / 2, ty)
        if abs(start[0] - end[0]) < 1:
            self.arrow([start, end])
        else:
            middle = (start[1] + end[1]) / 2
            self.arrow([start, (start[0], middle), (end[0], middle), end])

    def across(self, source: str, target: str) -> None:
        sx, sy, sw, sh = self.boxes[source]
        tx, ty, _, th = self.boxes[target]
        self.arrow([(sx + sw, sy + sh / 2), (tx, ty + th / 2)])

    def note(self, x: float, y: float, text: str) -> None:
        self.parts.append(
            f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="start" '
            f'font-family="{FONT}" font-size="11" font-style="italic" '
            f'fill="#6B6B66">{text}</text>'
        )

    def render(self) -> str:
        height = self.cursor + 10
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{height:.0f}" viewBox="0 0 {WIDTH} {height:.0f}">'
            '<defs><marker id="head" markerWidth="9" markerHeight="7" '
            'refX="8.5" refY="3.5" orient="auto">'
            '<polygon points="0 0, 9 3.5, 0 7" fill="#5A5A55"/></marker></defs>'
            f'<rect width="{WIDTH}" height="{height:.0f}" fill="#FFFFFF"/>'
            + "".join(self.parts)
            + "</svg>"
        )


def build(language: str) -> str:
    figure = Figure(language)
    say = figure.say

    # ---------------- Layer 1 : data ---------------------------------
    top = figure.band("layer_data", 6)
    rows = [top + index * ROW_PITCH for index in range(6)]

    figure.box("taxonomy_csv", "left", rows[0],
               ["product_categories.csv", say("taxonomy_sub")], "artifact")
    figure.box("taxonomy", "centre", rows[0], ["category_taxonomy.py"])

    figure.box("akakce", "left", rows[1],
               [say("akakce"), say("akakce_sub")], "external")
    figure.box("scraper", "centre", rows[1],
               ["product_scraper.py", "BeautifulSoup4 + Selenium"])
    figure.box("raw_csv", "right", rows[1],
               ["candidate_products_multicategory.csv", say("raw_sub")], "artifact")

    figure.box("catalog", "centre", rows[2],
               ["product_catalog.py", say("catalog_sub")])
    figure.box("synthetic_csv", "right", rows[2],
               ["...synthetic.csv", say("synthetic_sub")], "artifact")

    figure.box("processor", "centre", rows[3],
               ["data_processor.py", say("processor_sub")])
    figure.box("processed_json", "right", rows[3],
               ["processed_products_multicategory.json / .csv", say("processed_sub")],
               "artifact")

    figure.box("quality", "centre", rows[4],
               ["quality_check.py", say("quality_sub")])

    figure.box("keywords", "centre", rows[5], ["keyword_generator.py"])
    figure.box("keywords_json", "right", rows[5],
               ["generated_keywords_multicategory.json", say("keywords_sub")],
               "artifact")

    figure.across("taxonomy_csv", "taxonomy")
    figure.down("taxonomy", "scraper")
    figure.across("akakce", "scraper")
    figure.across("scraper", "raw_csv")
    figure.across("catalog", "synthetic_csv")
    figure.across("processor", "processed_json")
    figure.across("keywords", "keywords_json")

    # The raw dataset is what the processor reads.
    figure.arrow([(figure.boxes["raw_csv"][0] + 160, rows[1] + ROW_HEIGHT),
                  (figure.boxes["raw_csv"][0] + 160, rows[3] - 14),
                  (figure.boxes["processor"][0] + 150, rows[3] - 14),
                  (figure.boxes["processor"][0] + 150, rows[3])])

    # The gate reads the processed dataset and writes nothing; it reports and
    # exits, and the decision to continue is the operator's. Drawing it as a
    # side consumer rather than a link in the chain is what makes that true.
    figure.arrow([(figure.boxes["processed_json"][0] + 160, rows[3] + ROW_HEIGHT),
                  (figure.boxes["processed_json"][0] + 160, rows[4] + 26),
                  (figure.boxes["quality"][0] + COL["centre"][1], rows[4] + 26)])
    figure.note(figure.boxes["quality"][0] + COL["centre"][1] + 12, rows[4] + 45,
                say("quality_note"))

    figure.arrow([(figure.boxes["processed_json"][0] + 40, rows[3] + ROW_HEIGHT),
                  (figure.boxes["processed_json"][0] + 40, rows[5] - 14),
                  (figure.boxes["keywords"][0] + 150, rows[5] - 14),
                  (figure.boxes["keywords"][0] + 150, rows[5])])

    # ---------------- Layer 2 : evaluation ---------------------------
    top = figure.band("layer_eval", 5)
    rows = [top + index * ROW_PITCH for index in range(5)]

    figure.box("graph", "wide", rows[0],
               ["run_evaluation_batch.py", say("batch_sub")], x=40, width=460)
    figure.box("langgraph", "wide", rows[0],
               ["langgraph_flow.py", say("langgraph_sub")], x=520, width=460)

    method_x = [40, 278, 516, 754]
    method_w = 226
    methods = [
        ("m1", [say("m1")], ["rule_based_evaluator.py"],
         [say("m1_src"), say("m1_src_sub")], "artifact"),
        ("m2", [say("m2")], ["nano_llm_evaluator.py"], [say("m2_src")], "external"),
        ("m3", [say("m3")], ["tavily_client.py"], [say("m3_src")], "external"),
        ("m4", [say("m4")], ["agentic_search.py"],
         [say("m4_src"), say("m4_src_sub")], "external"),
    ]
    for index, (key, title, module, source, kind) in enumerate(methods):
        figure.box(key, "wide", rows[1], title, "method",
                   x=method_x[index], width=method_w, height=40)
        figure.box(key + "_mod", "wide", rows[1] + 48, module, "module",
                   x=method_x[index], width=method_w, height=38)
        figure.box(key + "_src", "wide", rows[1] + 96, source, kind,
                   x=method_x[index], width=method_w, height=44)

    figure.box("results", "wide", rows[3] + 22,
               [say("results"), say("results_sub")], "artifact")
    figure.box("validator", "wide", rows[4] + 14, [say("validator")],
               x=260, width=500, height=40)

    figure.down("keywords_json", "langgraph")
    figure.down("keywords_json", "graph")
    for index, (key, *_rest) in enumerate(methods):
        figure.down("graph", key)
        figure.down(key, key + "_mod")
        figure.down(key + "_mod", key + "_src")
        figure.arrow([(method_x[index] + method_w / 2, rows[1] + 140),
                      (method_x[index] + method_w / 2, rows[3] + 10),
                      (WIDTH / 2, rows[3] + 10),
                      (WIDTH / 2, rows[3] + 22)])
    figure.down("results", "validator")

    # ---------------- Layer 3 : measurement --------------------------
    top = figure.band("layer_measure", 6)
    rows = [top + index * ROW_PITCH for index in range(6)]

    figure.box("export", "centre", rows[0],
               ["export_label_workbook.py", say("export_sub")])
    figure.box("workbooks", "right", rows[0],
               [say("workbook1"), say("workbook2")], "artifact")

    figure.box("reviewer", "centre", rows[1],
               [say("reviewer"), say("reviewer_sub")], "human")
    figure.box("adjudication", "left", rows[2],
               ["multicategory_label_", say("adjudication_sub")], "artifact")

    figure.box("import", "centre", rows[2], ["import_label_workbook.py"])
    figure.box("ground_truth", "right", rows[2],
               ["multicategory_ground_truth.csv", say("ground_truth_sub")], "artifact")

    figure.box("manifest", "centre", rows[3], ["build_manifest.py"])
    figure.box("manifest_json", "right", rows[3],
               ["final_evaluation_manifest_", say("manifest_sub")], "artifact")

    figure.box("final_metrics", "wide", rows[4],
               ["final_metrics.py", say("final_metrics_sub")], x=170, width=280)
    figure.box("category_metrics", "wide", rows[4],
               ["category_metrics.py", say("category_metrics_sub")], x=560, width=280)

    figure.box("report", "centre", rows[5], ["multicategory_report.py"])
    figure.box("report_md", "right", rows[5],
               ["multicategory_evaluation_report.md"], "artifact")

    figure.down("validator", "export")
    figure.across("export", "workbooks")
    figure.down("export", "reviewer")
    figure.down("reviewer", "import")
    figure.across("adjudication", "import")
    figure.across("import", "ground_truth")
    figure.down("import", "manifest")
    figure.across("manifest", "manifest_json")
    figure.down("manifest", "final_metrics")
    figure.down("manifest", "category_metrics")
    figure.down("final_metrics", "report")
    figure.down("category_metrics", "report")
    figure.across("report", "report_md")

    return figure.render()


def main() -> None:
    for language, path in OUTPUTS.items():
        path.write_text(build(language), encoding="utf-8")
        print(f"{language}: {path.name}")


if __name__ == "__main__":
    main()
