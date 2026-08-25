"""Render the end-to-end pipeline overview as a print-ready SVG.

This is a presentation-support figure, not one of the report's seven
numbered figures — it draws the same six real stages described in report
section 3.2 (Stage 1 through Stage 6) as a single horizontal flowchart, in
the same visual language as Figure 5 (module = blue, artifact = grey,
external = orange, human = green) so it can sit next to the report's own
figures without looking like a different document.

Both languages are rendered from one layout and one text table, the same
pattern as make_figure5.py.

    python reports_multicategory/figures/make_figure_pipeline_overview.py

Writes figure_pipeline_overview_EN.svg and sekil_hat_ozeti_TR.svg next to
this file.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUTS = {
    "en": HERE / "figure_pipeline_overview_EN.svg",
    "tr": HERE / "sekil_hat_ozeti_TR.svg",
}

BOX_W = 232
GAP = 46
MARGIN = 40
WIDTH = MARGIN * 2 + 6 * BOX_W + 5 * GAP
FONT = "Segoe UI, Calibri, Arial, sans-serif"
MONO = "Consolas, Courier New, monospace"

STYLES = {
    "module": ("#DCE9F7", "#2C5D8F", "#123A5E"),
    "artifact": ("#F2F2F0", "#7A7A72", "#33332E"),
    "external": ("#FBE6CC", "#B9770E", "#6B4406"),
    "human": ("#E3F1E4", "#3B7D42", "#1E4722"),
}

TOP_WITH_TITLE = 92
TOP_NO_TITLE = 30
BOX_H = 272

TEXT: dict[str, dict[str, str]] = {
    "title": {"en": "THE END-TO-END PIPELINE", "tr": "UÇTAN UCA HAT"},
    "n1": {"en": "1. COLLECT", "tr": "1. TOPLAMA"},
    "d1": {
        "en": "Scrapes real listings from Akakçe, category by category, resuming across sessions when rate-limited.",
        "tr": "Akakçe'den kategori kategori gerçek ilan kazır; hız sınırında oturumlar arası devam eder.",
    },
    "f1": ["category_taxonomy.py", "product_scraper.py", "selenium_collector.py"],
    "s1": {"en": "489 products · 10 categories", "tr": "489 ürün · 10 kategori"},
    "k1": "external",
    "n2": {"en": "2. PROCESS & VALIDATE", "tr": "2. İŞLE VE DOĞRULA"},
    "d2": {
        "en": "Applies a profile-specific required-field set per category, then flags any row that fails the quality gate.",
        "tr": "Kategoriye göre zorunlu alan profilini uygular, kalite kapısından geçemeyen satırı işaretler.",
    },
    "f2": ["data_processor.py", "quality_check.py", "product_catalog.py"],
    "s2": {"en": "489 valid · 0 issues", "tr": "489 geçerli · 0 sorun"},
    "k2": "module",
    "n3": {"en": "3. GENERATE KEYWORD", "tr": "3. ANAHTAR KELİME"},
    "d3": {
        "en": "Builds one transactional-intent search phrase per product from real brand, model and variant fields.",
        "tr": "Her ürün için gerçek marka/model/varyant alanlarından işlemsel niyetli tek anahtar kelime üretir.",
    },
    "f3": ["keyword_generator.py", "keyword_loader.py"],
    "s3": {"en": "489 keywords · deterministic", "tr": "489 anahtar kelime · deterministik"},
    "k3": "module",
    "n4": {"en": "4. EVALUATE — 4 METHODS", "tr": "4. DEĞERLENDİR — 4 YÖNTEM"},
    "d4": {
        "en": "Runs all four judging methods on the same keyword inside one LangGraph graph, each writing to a shared schema.",
        "tr": "Aynı anahtar kelimeyle dört yöntemi tek LangGraph çizgesinde çalıştırır, hepsi ortak şemaya yazar.",
    },
    "f4": ["langgraph_flow.py", "rule_based_evaluator.py", "nano_llm_evaluator.py", "tavily_client.py", "agentic_search.py"],
    "s4": {"en": "80 live runs · 399 results", "tr": "80 canlı koşum · 399 sonuç"},
    "k4": "module",
    "n5": {"en": "5. LABEL BY HUMAN", "tr": "5. İNSAN ETİKETLER"},
    "d5": {
        "en": "Exports unique URLs to Excel with predictions hidden, then re-imports the filled workbook into ground truth.",
        "tr": "Benzersiz URL'leri tahminler gizli olarak Excel'e aktarır, dolan kitabı temel doğruluğa geri okur.",
    },
    "f5": ["export_label_workbook.py", "import_label_workbook.py", "ground_truth.py"],
    "s5": {"en": "193 URLs · 100% coverage", "tr": "193 URL · %100 kapsam"},
    "k5": "human",
    "n6": {"en": "6. MEASURE & REPORT", "tr": "6. ÖLÇ VE RAPORLA"},
    "d6": {
        "en": "Freezes which result files a report is built from, then computes accuracy, specificity and balanced accuracy.",
        "tr": "Raporun hangi sonuç dosyalarından üretildiğini dondurur; doğruluk, özgüllük ve dengeli doğruluğu hesaplar.",
    },
    "f6": ["build_manifest.py", "metrics.py", "category_metrics.py", "multicategory_report.py"],
    "s6": {"en": "Accuracy · Specificity · Bal. acc.", "tr": "Doğruluk · Özgüllük · Dengeli doğ."},
    "k6": "artifact",
    "footnote": {
        "en": "Every number above comes from a file on disk — the pipeline is reproducible end to end, from raw scrape to final report.",
        "tr": "Yukarıdaki her sayı diskteki bir dosyadan gelir — hat, ham kazımadan nihai rapora kadar uçtan uca yeniden üretilebilir.",
    },
}


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def wrap(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def build(language: str, include_title: bool = True) -> str:
    say = lambda key: TEXT[key][language]  # noqa: E731
    parts: list[str] = []
    top_offset = TOP_WITH_TITLE if include_title else TOP_NO_TITLE

    if include_title:
        parts.append(
            f'<text x="{WIDTH / 2:.0f}" y="40" text-anchor="middle" font-family="{FONT}" '
            f'font-size="26" font-weight="700" fill="#22252A">{esc(say("title"))}</text>'
        )

    for index in range(6):
        i = index + 1
        left = MARGIN + index * (BOX_W + GAP)
        top = top_offset
        kind = TEXT[f"k{i}"]
        fill, stroke, text_colour = STYLES[kind]

        parts.append(
            f'<rect x="{left}" y="{top}" width="{BOX_W}" height="{BOX_H}" rx="10" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>'
        )
        # step badge
        parts.append(
            f'<circle cx="{left + 26}" cy="{top + 28}" r="15" fill="{stroke}"/>'
        )
        parts.append(
            f'<text x="{left + 26}" y="{top + 33}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="14" font-weight="700" fill="#FFFFFF">{i}</text>'
        )
        step_title = esc(say(f"n{i}").split(". ", 1)[-1])
        parts.append(
            f'<text x="{left + 50}" y="{top + 33}" text-anchor="start" font-family="{FONT}" '
            f'font-size="13" font-weight="700" fill="{text_colour}">{step_title}</text>'
        )

        desc_lines = wrap(say(f"d{i}"), 30)
        for row, line in enumerate(desc_lines):
            parts.append(
                f'<text x="{left + 18}" y="{top + 66 + row * 17}" text-anchor="start" '
                f'font-family="{FONT}" font-size="11.5" fill="{text_colour}">{esc(line)}</text>'
            )

        files_top = top + 66 + len(desc_lines) * 17 + 18
        parts.append(
            f'<text x="{left + 18}" y="{files_top}" text-anchor="start" font-family="{FONT}" '
            f'font-size="9.5" font-weight="700" letter-spacing="1" fill="{stroke}">FILES</text>'
        )
        files_joined = ", ".join(TEXT[f"f{i}"])
        file_lines = wrap(files_joined, 28)
        for row, line in enumerate(file_lines):
            parts.append(
                f'<text x="{left + 18}" y="{files_top + 16 + row * 14}" text-anchor="start" '
                f'font-family="{MONO}" font-size="9.5" fill="{text_colour}">{esc(line)}</text>'
            )

        stat_y = files_top + 16 + len(file_lines) * 14 + 22
        parts.append(
            f'<text x="{left + 18}" y="{stat_y}" text-anchor="start" font-family="{FONT}" '
            f'font-size="11.5" font-weight="700" fill="{stroke}">{esc(say(f"s{i}"))}</text>'
        )

        if index < 5:
            ax = left + BOX_W + 6
            ay = top + BOX_H / 2
            parts.append(
                f'<path d="M{ax},{ay - 10} L{ax + GAP - 12},{ay} L{ax},{ay + 10} Z" fill="#5A5A55"/>'
            )
            parts.append(
                f'<line x1="{ax - 6}" y1="{ay}" x2="{ax + GAP - 12}" y2="{ay}" '
                'stroke="#5A5A55" stroke-width="1.8"/>'
            )

    footnote_y = top_offset + BOX_H + 42
    parts.append(
        f'<text x="{WIDTH / 2:.0f}" y="{footnote_y}" text-anchor="middle" font-family="{FONT}" '
        f'font-size="13" font-style="italic" fill="#5A5A55">{esc(say("footnote"))}</text>'
    )

    height = footnote_y + 24
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}">'
        f'<rect width="{WIDTH}" height="{height}" fill="#FFFFFF"/>'
        + "".join(parts)
        + "</svg>"
    )


def main() -> None:
    for language, path in OUTPUTS.items():
        path.write_text(build(language), encoding="utf-8")
        print(f"{language}: {path.name}")


if __name__ == "__main__":
    main()
