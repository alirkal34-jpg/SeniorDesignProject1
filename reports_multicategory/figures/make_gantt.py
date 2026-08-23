"""Render the project Gantt chart, planned against actual, as an SVG.

The proposal form asks for a Gantt chart after the task table. Drawing only
the plan would say nothing a reader could check, so each task carries two
bars: the dates promised in the proposal of 11.07.2026, and the dates the
version control history actually records. Where a task has no planned bar it
was not in the proposal at all — the two most valuable results of this project
are both in that group.

Actual dates come from the first and last commit that touched a task, except
for the two tasks that finished before the repository existed. Those are
marked as such rather than being given invented commit dates.

    python reports_multicategory/figures/make_gantt.py

Writes figure7_gantt_EN.svg and sekil7_gantt_TR.svg next to this file.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path


HERE = Path(__file__).resolve().parent
OUTPUTS = {
    "en": HERE / "figure7_gantt_EN.svg",
    "tr": HERE / "sekil7_gantt_TR.svg",
}

FONT = "Segoe UI, Calibri, Arial, sans-serif"

START = date(2026, 7, 6)      # Monday of the first project week
END = date(2026, 8, 30)       # Sunday of the last week
WEEKS = 8

LABEL_WIDTH = 372
OWNER_WIDTH = 96
CHART_X = LABEL_WIDTH + OWNER_WIDTH
WEEK_WIDTH = 96
CHART_WIDTH = WEEKS * WEEK_WIDTH
WIDTH = CHART_X + CHART_WIDTH + 26
HEADER_Y = 86
ROW_HEIGHT = 46
BAR_HEIGHT = 13

PLANNED = ("#C9D9EC", "#4C7DAB")
ACTUAL = ("#2C5D8F", "#1B3E60")
UNPLANNED = ("#7E68C4", "#4A3A80")

# task key, planned (start, end) or None, actual (start, end), owner key,
# whether the task was absent from the proposal
TASKS = [
    ("t1", (date(2026, 7, 9), date(2026, 7, 14)),
     (date(2026, 7, 9), date(2026, 7, 14)), "both", False),
    ("t2", (date(2026, 7, 15), date(2026, 7, 23)),
     (date(2026, 7, 15), date(2026, 7, 22)), "both", False),
    ("t3", (date(2026, 7, 20), date(2026, 7, 28)),
     (date(2026, 7, 23), date(2026, 7, 26)), "ali", False),
    ("t4", (date(2026, 7, 27), date(2026, 8, 4)),
     (date(2026, 7, 23), date(2026, 7, 26)), "ali", False),
    ("t5", (date(2026, 8, 3), date(2026, 8, 10)),
     (date(2026, 7, 23), date(2026, 7, 28)), "ali", False),
    ("t6", (date(2026, 8, 8), date(2026, 8, 14)),
     (date(2026, 7, 23), date(2026, 7, 28)), "atahan", False),
    ("t7", (date(2026, 8, 13), date(2026, 8, 17)),
     (date(2026, 7, 28), date(2026, 8, 6)), "both", False),
    ("t8", None, (date(2026, 8, 18), date(2026, 8, 19)), "both", True),
    ("t9", None, (date(2026, 8, 21), date(2026, 8, 21)), "ali", True),
    ("t10", (date(2026, 8, 16), date(2026, 8, 20)),
     (date(2026, 8, 21), date(2026, 8, 23)), "ali", False),
]

TEXT: dict[str, dict[str, str]] = {
    "title": {
        "en": "Figure 7. Project Gantt chart — proposal plan against version control history",
        "tr": "Şekil 7. Proje Gantt şeması — önergedeki plan ile sürüm kontrol geçmişi",
    },
    "task": {"en": "Task", "tr": "Görev"},
    "owner": {"en": "Owner", "tr": "Sorumlu"},
    "ali": {"en": "A. R. Kal", "tr": "A. R. Kal"},
    "atahan": {"en": "A. Bulut", "tr": "A. Bulut"},
    "both": {"en": "both", "tr": "ikisi"},
    "legend_planned": {"en": "planned (proposal, 11.07.2026)", "tr": "planlanan (önerge, 11.07.2026)"},
    "legend_actual": {"en": "actual (commit history)", "tr": "gerçekleşen (işlem geçmişi)"},
    "legend_unplanned": {"en": "not in the proposal", "tr": "önergede yok"},
    "t1": {
        "en": "1. Problem definition and research question",
        "tr": "1. Problem tanımı ve araştırma sorusu",
    },
    "t2": {
        "en": "2. Literature review and search strategy",
        "tr": "2. Literatür taraması ve arama stratejisi",
    },
    "t3": {
        "en": "3. Product dataset and attribute schema",
        "tr": "3. Ürün veri kümesi ve nitelik şeması",
    },
    "t4": {
        "en": "4. Attribute normalization layer",
        "tr": "4. Nitelik normalizasyon katmanı",
    },
    "t5": {
        "en": "5. Rule-based evaluation and quality gate",
        "tr": "5. Kural tabanlı değerlendirme ve kalite kapısı",
    },
    "t6": {
        "en": "6. Language model modules (keyword, judge)",
        "tr": "6. Dil modeli modülleri (anahtar kelime, yargı)",
    },
    "t7": {
        "en": "7. End-to-end pipeline and test suite",
        "tr": "7. Uçtan uca hat ve test paketi",
    },
    "t8": {
        "en": "8. Expansion to ten categories (advisor feedback)",
        "tr": "8. On kategoriye genişletme (danışman geri bildirimi)",
    },
    "t9": {
        "en": "9. Error analysis: prompt–criterion alignment",
        "tr": "9. Hata analizi: istem–ölçüt hizalaması",
    },
    "t10": {
        "en": "10. Report, figures and presentation",
        "tr": "10. Rapor, şekiller ve sunum",
    },
    "prerepo": {
        "en": "before the repository existed",
        "tr": "depo açılmadan önce",
    },
}

PRE_REPO = {"t1", "t2"}


def day_x(value: date) -> float:
    return CHART_X + (value - START).days / 7 * WEEK_WIDTH


def build(language: str) -> str:
    def say(key: str) -> str:
        return TEXT[key][language]

    height = HEADER_Y + len(TASKS) * ROW_HEIGHT + 74
    parts: list[str] = [
        f'<rect width="{WIDTH}" height="{height}" fill="#FFFFFF"/>',
        f'<text x="{WIDTH / 2:.0f}" y="30" text-anchor="middle" '
        f'font-family="{FONT}" font-size="14" font-weight="600" '
        f'fill="#33332E">{say("title")}</text>',
    ]

    # Column headers.
    parts.append(
        f'<text x="16" y="{HEADER_Y - 12}" font-family="{FONT}" font-size="12" '
        f'font-weight="600" fill="#4A4A45">{say("task")}</text>'
    )
    parts.append(
        f'<text x="{LABEL_WIDTH + 8}" y="{HEADER_Y - 12}" font-family="{FONT}" '
        f'font-size="12" font-weight="600" fill="#4A4A45">{say("owner")}</text>'
    )

    # Week grid.
    for index in range(WEEKS + 1):
        x = CHART_X + index * WEEK_WIDTH
        parts.append(
            f'<path d="M{x:.0f},{HEADER_Y - 30} V{HEADER_Y + len(TASKS) * ROW_HEIGHT:.0f}" '
            'stroke="#DFDFDA" stroke-width="1"/>'
        )
        if index < WEEKS:
            week_start = date.fromordinal(START.toordinal() + index * 7)
            parts.append(
                f'<text x="{x + WEEK_WIDTH / 2:.0f}" y="{HEADER_Y - 12}" '
                f'text-anchor="middle" font-family="{FONT}" font-size="11" '
                f'fill="#6B6B66">{week_start.strftime("%d.%m")}</text>'
            )

    # Rows.
    for row, (key, planned, actual, owner, unplanned) in enumerate(TASKS):
        top = HEADER_Y + row * ROW_HEIGHT
        if row % 2 == 0:
            parts.append(
                f'<rect x="10" y="{top}" width="{WIDTH - 20}" height="{ROW_HEIGHT}" '
                'fill="#FAFAF8"/>'
            )
        parts.append(
            f'<text x="16" y="{top + 28}" font-family="{FONT}" font-size="11.5" '
            f'fill="#33332E">{say(key)}</text>'
        )
        parts.append(
            f'<text x="{LABEL_WIDTH + 8}" y="{top + 28}" font-family="{FONT}" '
            f'font-size="11" fill="#6B6B66">{say(owner)}</text>'
        )

        if planned is not None:
            fill, stroke = PLANNED
            x1, x2 = day_x(planned[0]), day_x(planned[1])
            parts.append(
                f'<rect x="{x1:.0f}" y="{top + 8}" width="{max(x2 - x1, 6):.0f}" '
                f'height="{BAR_HEIGHT}" rx="3" fill="{fill}" stroke="{stroke}" '
                'stroke-width="1"/>'
            )

        fill, stroke = UNPLANNED if unplanned else ACTUAL
        x1, x2 = day_x(actual[0]), day_x(actual[1])
        parts.append(
            f'<rect x="{x1:.0f}" y="{top + 25}" width="{max(x2 - x1, 6):.0f}" '
            f'height="{BAR_HEIGHT}" rx="3" fill="{fill}" stroke="{stroke}" '
            'stroke-width="1"/>'
        )
        if key in PRE_REPO:
            parts.append(
                f'<text x="{x2 + 8:.0f}" y="{top + 36}" font-family="{FONT}" '
                f'font-size="10" font-style="italic" fill="#8A8A84">'
                f'{say("prerepo")}</text>'
            )

    # Legend.
    legend_y = HEADER_Y + len(TASKS) * ROW_HEIGHT + 34
    for index, (colours, key) in enumerate(
        ((PLANNED, "legend_planned"), (ACTUAL, "legend_actual"),
         (UNPLANNED, "legend_unplanned"))
    ):
        x = 16 + index * 300
        fill, stroke = colours
        parts.append(
            f'<rect x="{x}" y="{legend_y - 10}" width="26" height="12" rx="3" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
            f'<text x="{x + 34}" y="{legend_y}" font-family="{FONT}" '
            f'font-size="11" fill="#4A4A45">{say(key)}</text>'
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
