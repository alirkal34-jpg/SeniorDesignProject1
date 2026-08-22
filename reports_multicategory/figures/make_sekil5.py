"""Render Figure 5, the system architecture, as a print-ready SVG.

The figure is generated rather than drawn so it can be corrected when the
architecture changes, the same way every other number in this report is
recomputed rather than retyped. Coordinates are derived from a three-column
grid: what a stage reads on the left, the module that runs on it in the
middle, what the stage writes on the right. Reading a row therefore answers
"which file did this produce", which is the question the figure exists for.

    python reports_multicategory/figures/make_sekil5.py

Writes sekil5_sistem_mimarisi.svg next to this file. SVG keeps its quality at
any size in Word and in a printed thesis; a PNG would not.
"""

from __future__ import annotations

from pathlib import Path


OUTPUT = Path(__file__).resolve().parent / "sekil5_sistem_mimarisi.svg"

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

# Column geometry. Left is what the stage reads, centre is the module, right
# is what it writes.
COL = {
    "left": (40, 240),
    "centre": (320, 300),
    "right": (660, 320),
    "wide": (40, 940),
}

ROW_HEIGHT = 52
ROW_PITCH = 74


class Figure:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.boxes: dict[str, tuple[float, float, float, float]] = {}
        self.cursor = 0.0

    # -- geometry -----------------------------------------------------
    def band(self, title: str, rows: int, extra: float = 0.0) -> float:
        """Open a layer band tall enough for ``rows`` rows and return its top."""

        top = self.cursor
        height = 46 + rows * ROW_PITCH + extra
        self.parts.append(
            f'<rect x="16" y="{top:.0f}" width="{WIDTH - 32}" height="{height:.0f}" '
            'rx="10" fill="#FFFFFF" stroke="#B9B9B4" stroke-width="1.5"/>'
        )
        self.parts.append(
            f'<rect x="16" y="{top:.0f}" width="{WIDTH - 32}" height="34" '
            'rx="10" fill="#4A4A45"/>'
        )
        self.parts.append(
            f'<rect x="16" y="{top + 24:.0f}" width="{WIDTH - 32}" height="10" fill="#4A4A45"/>'
        )
        self.parts.append(
            f'<text x="{WIDTH / 2:.0f}" y="{top + 23:.0f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="15" font-weight="600" '
            f'fill="#FFFFFF" letter-spacing="1.4">{title}</text>'
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
            mono = line.endswith(".py") or "." in line and "/" in line
            size = 12.5 if index == 0 else 11
            self.parts.append(
                f'<text x="{left + box_width / 2:.0f}" y="{start + index * step:.0f}" '
                f'text-anchor="middle" font-family="{MONO if mono else FONT}" '
                f'font-size="{size}" fill="{text_colour}">{line}</text>'
            )

    # -- connectors ---------------------------------------------------
    def arrow(self, points: list[tuple[float, float]], dashed: bool = False) -> None:
        path = " ".join(
            ("M" if index == 0 else "L") + f"{x:.0f},{y:.0f}"
            for index, (x, y) in enumerate(points)
        )
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        self.parts.append(
            f'<path d="{path}" fill="none" stroke="#5A5A55" stroke-width="1.6"'
            f'{dash} marker-end="url(#head)"/>'
        )

    def down(self, source: str, target: str, dashed: bool = False) -> None:
        sx, sy, sw, sh = self.boxes[source]
        tx, ty, tw, _ = self.boxes[target]
        start = (sx + sw / 2, sy + sh)
        end = (tx + tw / 2, ty)
        if abs(start[0] - end[0]) < 1:
            self.arrow([start, end], dashed)
        else:
            middle = (start[1] + end[1]) / 2
            self.arrow(
                [start, (start[0], middle), (end[0], middle), end], dashed
            )

    def across(self, source: str, target: str, dashed: bool = False) -> None:
        sx, sy, sw, sh = self.boxes[source]
        tx, ty, _, th = self.boxes[target]
        self.arrow(
            [(sx + sw, sy + sh / 2), (tx, ty + th / 2)], dashed
        )

    def note(self, x: float, y: float, text: str, anchor: str = "start") -> None:
        self.parts.append(
            f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="{anchor}" '
            f'font-family="{FONT}" font-size="11" font-style="italic" '
            f'fill="#6B6B66">{text}</text>'
        )

    def render(self) -> str:
        height = self.cursor + 10
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{height:.0f}" viewBox="0 0 {WIDTH} {height:.0f}">'
            '<defs><marker id="head" markerWidth="9" markerHeight="7" '
            'refX="8.5" refY="3.5" orient="auto">'
            '<polygon points="0 0, 9 3.5, 0 7" fill="#5A5A55"/></marker></defs>'
            f'<rect width="{WIDTH}" height="{height:.0f}" fill="#FFFFFF"/>'
            + "".join(self.parts)
            + "</svg>"
        )


def build() -> str:
    figure = Figure()

    # ---------------- Layer 1 : data ---------------------------------
    top = figure.band("VER&#304; KATMANI", 6)
    rows = [top + index * ROW_PITCH for index in range(6)]

    figure.box("taxonomy_csv", "left", rows[0],
               ["product_categories.csv", "10 kategori grubu"], "artifact")
    figure.box("taxonomy", "centre", rows[0], ["category_taxonomy.py"])

    figure.box("akakce", "left", rows[1], ["Akak&#231;e", "d&#305;&#351; kaynak"], "external")
    figure.box("scraper", "centre", rows[1],
               ["product_scraper.py", "BeautifulSoup4 + Selenium"])
    figure.box("raw_csv", "right", rows[1],
               ["candidate_products_multicategory.csv",
                "+ .metadata.json &#8212; scraped, 489 &#252;r&#252;n"], "artifact")

    figure.box("catalog", "centre", rows[2],
               ["product_catalog.py",
                "&#231;evrimd&#305;&#351;&#305; yedek &#8212; ayn&#305; taksonomiyi okur"])
    figure.box("synthetic_csv", "right", rows[2],
               ["...synthetic.csv", "synthetic damgal&#305;"], "artifact")

    figure.box("processor", "centre", rows[3],
               ["data_processor.py", "&#351;ema + temizlik + sat&#305;r do&#287;rulama"])
    figure.box("processed_json", "right", rows[3],
               ["processed_products_multicategory.json / .csv",
                "489 kay&#305;t  +  validation_issues_...csv"], "artifact")

    figure.box("quality", "centre", rows[4],
               ["quality_check.py", "veri k&#252;mesi d&#252;zeyi kap&#305;"])

    figure.box("keywords", "centre", rows[5], ["keyword_generator.py"])
    figure.box("keywords_json", "right", rows[5],
               ["generated_keywords_multicategory.json", "&#252;r&#252;n ba&#351;&#305;na 1 anahtar kelime"],
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
                "PASSED / FAILED raporu &#8212; dosya yazmaz, ak&#305;&#351;&#305; durdurmaz")

    figure.arrow([(figure.boxes["processed_json"][0] + 40, rows[3] + ROW_HEIGHT),
                  (figure.boxes["processed_json"][0] + 40, rows[5] - 14),
                  (figure.boxes["keywords"][0] + 150, rows[5] - 14),
                  (figure.boxes["keywords"][0] + 150, rows[5])])

    # ---------------- Layer 2 : evaluation ---------------------------
    top = figure.band("DE&#286;ERLEND&#304;RME KATMANI", 5)
    rows = [top + index * ROW_PITCH for index in range(5)]

    figure.box("graph", "wide", rows[0],
               ["run_evaluation_batch.py", "rapordaki 80 ko&#351;umu &#252;retir"],
               x=40, width=460)
    figure.box("langgraph", "wide", rows[0],
               ["langgraph_flow.py", "ayn&#305; d&#246;rt y&#246;ntem, LangGraph &#231;izgesi (&#350;ekil 1)"],
               x=520, width=460)

    method_x = [40, 278, 516, 754]
    method_w = 226
    names = [
        ("m1", ["Selenium + Kural Tabanl&#305;"], ["rule_based_evaluator.py"],
         ["Bing (Selenium) + kural tablosu", "e&#351;ik 0,60 &#8212; model yok"], "artifact"),
        ("m2", ["Selenium + NanoLLM"], ["nano_llm_evaluator.py"],
         ["Bing (Selenium) + OpenRouter"], "external"),
        ("m3", ["Tavily + NanoLLM"], ["tavily_client.py"],
         ["Tavily API + OpenRouter"], "external"),
        ("m4", ["Agentic Search"], ["agentic_search.py"],
         ["Bing (Selenium) + OpenRouter", "planlay&#305;c&#305; + de&#287;erlendirici"], "external"),
    ]
    for index, (key, title, module, source, kind) in enumerate(names):
        figure.box(key, "wide", rows[1], title, "method",
                   x=method_x[index], width=method_w, height=40)
        figure.box(key + "_mod", "wide", rows[1] + 48, module, "module",
                   x=method_x[index], width=method_w, height=38)
        figure.box(key + "_src", "wide", rows[1] + 96, source, kind,
                   x=method_x[index], width=method_w, height=44)

    figure.box("results", "wide", rows[3] + 22,
               ["results_multicategory/&lt;y&#246;ntem&gt;/*.json",
                "80 dosya &#8212; 20 &#252;r&#252;n &#215; 4 y&#246;ntem, 399 sonu&#231;"], "artifact")
    figure.box("validator", "wide", rows[4] + 14,
               ["result_validator.py &#8212; ortak JSON &#351;emas&#305;"],
               x=260, width=500, height=40)

    figure.down("keywords_json", "langgraph")
    figure.down("keywords_json", "graph")
    for index, (key, *_rest) in enumerate(names):
        figure.down("graph", key)
        figure.down(key, key + "_mod")
        figure.down(key + "_mod", key + "_src")
        figure.arrow([(method_x[index] + method_w / 2, rows[1] + 140),
                      (method_x[index] + method_w / 2, rows[3] + 10),
                      (WIDTH / 2, rows[3] + 10),
                      (WIDTH / 2, rows[3] + 22)])
    figure.down("results", "validator")

    # ---------------- Layer 3 : measurement --------------------------
    top = figure.band("&#214;L&#199;&#220;M VE RAPORLAMA KATMANI", 6)
    rows = [top + index * ROW_PITCH for index in range(6)]

    figure.box("export", "centre", rows[0],
               ["export_label_workbook.py", "model tahminleri gizli"])
    figure.box("workbooks", "right", rows[0],
               ["label_review_session1.xlsx &#8212; 134 URL",
                "label_review_session2.xlsx &#8212; 61 URL"], "artifact")

    figure.box("reviewer", "centre", rows[1],
               ["&#304;nsan de&#287;erlendirici", "193 benzersiz URL elle etiketlenir"], "human")
    figure.box("adjudication", "left", rows[2],
               ["multicategory_label_", "adjudications.csv &#8212; 5 karar"], "artifact")

    figure.box("import", "centre", rows[2], ["import_label_workbook.py"])
    figure.box("ground_truth", "right", rows[2],
               ["multicategory_ground_truth.csv",
                "193 etiket &#8212; 140 uygun / 53 uygunsuz"], "artifact")

    figure.box("manifest", "centre", rows[3], ["build_manifest.py"])
    figure.box("manifest_json", "right", rows[3],
               ["final_evaluation_manifest_", "multicategory.json &#8212; 80 dosya donduruldu"],
               "artifact")

    figure.box("final_metrics", "wide", rows[4],
               ["final_metrics.py", "genel metrikler"], x=170, width=280)
    figure.box("category_metrics", "wide", rows[4],
               ["category_metrics.py", "kategori baz&#305;nda"], x=560, width=280)

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
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"Yaz&#305;ld&#305;: {OUTPUT}".replace("&#305;", "ı"))


if __name__ == "__main__":
    main()
