"""Render the project schedule as a week grid, in the shape the report template asks for.

The earlier version of this figure drew commit spans. That understated the
work: a task carried for a week and committed once appeared as a single day,
and the heaviest day of the project produced no commit at all, because
scraping 489 products and labeling 193 URLs changes no code. Version control
records when work was published, not when it was done.

The schedule is therefore given in weeks, which is the unit the work was
actually planned and carried out in. What version control still supports well
is volume: the row under the grid marks output that can be counted on disk —
result files, label rows, scraping session logs — at the week it appeared.

    python reports_multicategory/figures/make_schedule.py

Writes figure7_schedule_EN.svg and sekil7_calisma_takvimi_TR.svg.
"""

from __future__ import annotations

from pathlib import Path


HERE = Path(__file__).resolve().parent
OUTPUTS = {
    "en": HERE / "figure7_schedule_EN.svg",
    "tr": HERE / "sekil7_calisma_takvimi_TR.svg",
}

FONT = "Segoe UI, Calibri, Arial, sans-serif"

WEEKS = [
    ("W1", "09.07 – 15.07"),
    ("W2", "16.07 – 22.07"),
    ("W3", "23.07 – 29.07"),
    ("W4", "30.07 – 05.08"),
    ("W5", "06.08 – 12.08"),
    ("W6", "13.08 – 19.08"),
    ("W7", "20.08 – 23.08"),
]

LABEL_WIDTH = 452
OWNER_WIDTH = 104
GRID_X = LABEL_WIDTH + OWNER_WIDTH
CELL_WIDTH = 104
GRID_WIDTH = len(WEEKS) * CELL_WIDTH
WIDTH = GRID_X + GRID_WIDTH + 20
HEADER_TOP = 58
HEADER_HEIGHT = 48
ROW_HEIGHT = 40

FILL = "#2C5D8F"
FILL_LIGHT = "#DCE9F7"
GRID_LINE = "#C9C9C3"
TEXT_COLOUR = "#33332E"

# task key, owner key, first week (1-based), last week
TASKS = [
    ("t1", "both", 1, 1),
    ("t2", "both", 1, 2),
    ("t3", "both", 2, 3),
    ("t4", "ali", 3, 4),
    ("t5", "atahan", 3, 4),
    ("t6", "atahan", 3, 4),
    ("t7", "both", 4, 5),
    ("t8", "both", 4, 5),
    ("t9", "both", 5, 6),
    ("t10", "both", 6, 7),
]

# Output that can be counted on disk, at the week it appeared.
OUTPUTS_BY_WEEK = {
    4: "out_w4",
    5: "out_w5",
    6: "out_w6",
    7: "out_w7",
}

TEXT: dict[str, dict[str, str]] = {
    "title": {
        "en": "Figure 7. Project schedule, 09.07.2026 – 23.08.2026",
        "tr": "Şekil 7. Proje çalışma takvimi, 09.07.2026 – 23.08.2026",
    },
    "task": {"en": "Task", "tr": "Görev"},
    "owner": {"en": "Responsible", "tr": "Sorumlu"},
    "weeks": {"en": "Weeks", "tr": "Haftalar"},
    "ali": {"en": "Student 1", "tr": "Öğrenci 1"},
    "atahan": {"en": "Student 2", "tr": "Öğrenci 2"},
    "both": {"en": "Student 1\nStudent 2", "tr": "Öğrenci 1\nÖğrenci 2"},
    "t1": {
        "en": "Problem definition and research question",
        "tr": "Problem tanımı ve araştırma sorusu",
    },
    "t2": {
        "en": "Literature review and search strategy",
        "tr": "Literatür taraması ve arama stratejisi",
    },
    "t3": {
        "en": "Product dataset, attribute schema and normalization",
        "tr": "Ürün veri kümesi, nitelik şeması ve normalizasyon",
    },
    "t4": {
        "en": "Rule-based evaluation and dataset quality gate",
        "tr": "Kural tabanlı değerlendirme ve kalite kapısı",
    },
    "t5": {
        "en": "Keyword generation and relevance judging modules",
        "tr": "Anahtar kelime üretimi ve uygunluk yargısı modülleri",
    },
    "t6": {
        "en": "Search integrations (Selenium/Bing, Tavily, agentic)",
        "tr": "Arama entegrasyonları (Selenium/Bing, Tavily, etmen)",
    },
    "t7": {
        "en": "LangGraph orchestration and end-to-end pipeline",
        "tr": "LangGraph orkestrasyonu ve uçtan uca hat",
    },
    "t8": {
        "en": "First evaluation and human labeling (10 products)",
        "tr": "İlk değerlendirme ve insan etiketleme (10 ürün)",
    },
    "t9": {
        "en": "Expansion to ten categories: scraping, runs, labeling",
        "tr": "On kategoriye genişletme: kazıma, koşumlar, etiketleme",
    },
    "t10": {
        "en": "Error analysis, report, figures and presentation",
        "tr": "Hata analizi, rapor, şekiller ve sunum",
    },
    "output_header": {
        "en": "Counted output",
        "tr": "Sayılan çıktı",
    },
    "out_w4": {
        "en": "40 live runs\n199 results",
        "tr": "40 canlı koşum\n199 sonuç",
    },
    "out_w5": {
        "en": "107 human\nlabels",
        "tr": "107 insan\netiketi",
    },
    "out_w6": {
        "en": "489 products\n80 runs · 193 labels",
        "tr": "489 ürün\n80 koşum · 193 etiket",
    },
    "out_w7": {
        "en": "60 files re-judged\n7 figures · 399 tests",
        "tr": "60 dosya yeniden\n7 şekil · 399 test",
    },
    "footnote": {
        "en": "Weeks are the unit the work was carried out in. The counted output row lists "
              "files that exist on disk, not estimates.",
        "tr": "Haftalar, işin yürütüldüğü birimdir. Sayılan çıktı satırı diskte var olan "
              "dosyaları listeler, tahmin değildir.",
    },
}


def build(language: str) -> str:
    def say(key: str) -> str:
        return TEXT[key][language]

    rows_top = HEADER_TOP + HEADER_HEIGHT
    rows_bottom = rows_top + len(TASKS) * ROW_HEIGHT
    output_top = rows_bottom
    output_height = 44
    height = output_top + output_height + 46

    parts: list[str] = [
        f'<rect width="{WIDTH}" height="{height}" fill="#FFFFFF"/>',
        f'<text x="{WIDTH / 2:.0f}" y="32" text-anchor="middle" '
        f'font-family="{FONT}" font-size="14" font-weight="600" '
        f'fill="{TEXT_COLOUR}">{say("title")}</text>',
    ]

    # Header block.
    parts.append(
        f'<rect x="10" y="{HEADER_TOP}" width="{WIDTH - 20}" '
        f'height="{HEADER_HEIGHT}" fill="#F2F2F0" stroke="{GRID_LINE}" '
        'stroke-width="1.2"/>'
    )
    parts.append(
        f'<text x="22" y="{HEADER_TOP + 30}" font-family="{FONT}" '
        f'font-size="12.5" font-weight="600" fill="{TEXT_COLOUR}">'
        f'{say("task")}</text>'
    )
    parts.append(
        f'<text x="{LABEL_WIDTH + 12}" y="{HEADER_TOP + 30}" font-family="{FONT}" '
        f'font-size="12.5" font-weight="600" fill="{TEXT_COLOUR}">'
        f'{say("owner")}</text>'
    )
    parts.append(
        f'<text x="{GRID_X + GRID_WIDTH / 2:.0f}" y="{HEADER_TOP + 17}" '
        f'text-anchor="middle" font-family="{FONT}" font-size="12.5" '
        f'font-weight="600" fill="{TEXT_COLOUR}">{say("weeks")}</text>'
    )
    for index, (label, span) in enumerate(WEEKS):
        centre = GRID_X + index * CELL_WIDTH + CELL_WIDTH / 2
        parts.append(
            f'<text x="{centre:.0f}" y="{HEADER_TOP + 33}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="11.5" font-weight="600" '
            f'fill="{TEXT_COLOUR}">{label}</text>'
        )
        parts.append(
            f'<text x="{centre:.0f}" y="{HEADER_TOP + 44}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="9.5" fill="#6B6B66">{span}</text>'
        )

    # Task rows.
    for row, (key, owner, first, last) in enumerate(TASKS):
        top = rows_top + row * ROW_HEIGHT
        parts.append(
            f'<rect x="10" y="{top}" width="{WIDTH - 20}" height="{ROW_HEIGHT}" '
            f'fill="{"#FFFFFF" if row % 2 else "#FAFAF8"}" stroke="{GRID_LINE}" '
            'stroke-width="1"/>'
        )
        parts.append(
            f'<text x="22" y="{top + 25}" font-family="{FONT}" font-size="11.5" '
            f'fill="{TEXT_COLOUR}">{row + 1}. {say(key)}</text>'
        )
        owner_lines = say(owner).split("\n")
        start_y = top + 25 - (len(owner_lines) - 1) * 6
        for index, line in enumerate(owner_lines):
            parts.append(
                f'<text x="{LABEL_WIDTH + 12}" y="{start_y + index * 12:.0f}" '
                f'font-family="{FONT}" font-size="10.5" fill="#5A5A55">{line}</text>'
            )

        for index in range(len(WEEKS)):
            x = GRID_X + index * CELL_WIDTH
            parts.append(
                f'<rect x="{x}" y="{top}" width="{CELL_WIDTH}" '
                f'height="{ROW_HEIGHT}" fill="none" stroke="{GRID_LINE}" '
                'stroke-width="0.8"/>'
            )
            if first <= index + 1 <= last:
                parts.append(
                    f'<rect x="{x + 5}" y="{top + 11}" width="{CELL_WIDTH - 10}" '
                    f'height="{ROW_HEIGHT - 22}" rx="3" fill="{FILL}"/>'
                )

    # Counted output row.
    parts.append(
        f'<rect x="10" y="{output_top}" width="{WIDTH - 20}" '
        f'height="{output_height}" fill="#F7F4EA" stroke="{GRID_LINE}" '
        'stroke-width="1.2"/>'
    )
    parts.append(
        f'<text x="22" y="{output_top + 27}" font-family="{FONT}" '
        f'font-size="11.5" font-weight="600" fill="#6B5A2E">'
        f'{say("output_header")}</text>'
    )
    for index in range(len(WEEKS)):
        x = GRID_X + index * CELL_WIDTH
        parts.append(
            f'<rect x="{x}" y="{output_top}" width="{CELL_WIDTH}" '
            f'height="{output_height}" fill="none" stroke="{GRID_LINE}" '
            'stroke-width="0.8"/>'
        )
        key = OUTPUTS_BY_WEEK.get(index + 1)
        if key is None:
            continue
        lines = say(key).split("\n")
        centre = x + CELL_WIDTH / 2
        start_y = output_top + 24 - (len(lines) - 1) * 6
        for line_index, line in enumerate(lines):
            parts.append(
                f'<text x="{centre:.0f}" y="{start_y + line_index * 13:.0f}" '
                f'text-anchor="middle" font-family="{FONT}" font-size="9.5" '
                f'fill="#6B5A2E">{line}</text>'
            )

    parts.append(
        f'<text x="22" y="{output_top + output_height + 26}" '
        f'font-family="{FONT}" font-size="10.5" font-style="italic" '
        f'fill="#8A8A84">{say("footnote")}</text>'
    )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{height}" viewBox="0 0 {WIDTH} {height}">'
        + "".join(parts)
        + "</svg>"
    )


def main() -> None:
    for language, path in OUTPUTS.items():
        path.write_text(build(language), encoding="utf-8")
        print(f"{language}: {path.name}")


if __name__ == "__main__":
    main()
