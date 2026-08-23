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

import subprocess
from collections import Counter
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
    "output_header": {
        "en": "Measured output (counted artifacts, not commits)",
        "tr": "Ölçülen çıktı (sayılmış dosyalar, işlem değil)",
    },
    "density_header": {"en": "Commits per day", "tr": "Günlük işlem sayısı"},
    "ms_phase1": {
        "en": "40 live runs, 199 results (phones)",
        "tr": "40 canlı koşum, 199 sonuç (telefon)",
    },
    "ms_labels1": {"en": "107 human labels", "tr": "107 insan etiketi"},
    "ms_scrape": {
        "en": "7 scraping sessions, 489 products — no commit this day",
        "tr": "7 kazıma oturumu, 489 ürün — bu gün hiç işlem yok",
    },
    "ms_runs": {"en": "80 live runs, 399 results", "tr": "80 canlı koşum, 399 sonuç"},
    "ms_labels2": {
        "en": "193 URLs labeled by hand, 2 sessions",
        "tr": "193 URL elle etiketlendi, 2 oturum",
    },
    "ms_rejudge": {
        "en": "60 files re-judged on one endpoint",
        "tr": "60 dosya tek uç noktada yeniden yargılandı",
    },
    "ms_figures": {"en": "4 figures, 399 tests", "tr": "4 şekil, 399 test"},
    "note_gap": {
        "en": "No commit and no artifact between 07.08 and 17.08.",
        "tr": "07.08 – 17.08 arasında ne işlem ne üretilmiş dosya var.",
    },
}

PRE_REPO = {"t1", "t2"}

# What the commit history cannot show. Each of these is a counted artifact on
# disk, not an estimate: scraping session logs, result files, label rows in the
# workbooks, re-judged files, and rendered figures. The heaviest single day of
# the project, 18.08, produced no commit at all.
MILESTONES = [
    (date(2026, 7, 28), "ms_phase1"),
    (date(2026, 7, 31), "ms_labels1"),
    (date(2026, 8, 18), "ms_scrape"),
    (date(2026, 8, 19), "ms_runs"),
    (date(2026, 8, 19), "ms_labels2"),
    (date(2026, 8, 21), "ms_rejudge"),
    (date(2026, 8, 23), "ms_figures"),
]


def commits_per_day() -> dict[date, int]:
    """Read the commit history so the density strip is measured, not typed."""

    try:
        output = subprocess.run(
            ["git", "log", "--all", "--format=%ad", "--date=format:%Y-%m-%d"],
            cwd=HERE.parents[1],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return {}

    counts: Counter[date] = Counter()
    for line in output.split():
        year, month, day = (int(part) for part in line.split("-"))
        counts[date(year, month, day)] += 1
    return dict(counts)


def day_x(value: date) -> float:
    return CHART_X + (value - START).days / 7 * WEEK_WIDTH


def build(language: str) -> str:
    def say(key: str) -> str:
        return TEXT[key][language]

    rows_bottom = HEADER_Y + len(TASKS) * ROW_HEIGHT
    output_top = rows_bottom + 34
    density_top = output_top + 128
    height = density_top + 96
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

    # Measured output: what the commit history cannot show.
    parts.append(
        f'<path d="M10,{rows_bottom + 12} H{WIDTH - 10}" stroke="#DFDFDA" '
        'stroke-width="1"/>'
    )
    parts.append(
        f'<text x="16" y="{output_top + 4:.0f}" font-family="{FONT}" '
        f'font-size="12" font-weight="600" fill="#4A4A45">'
        f'{say("output_header")}</text>'
    )
    # Five of the seven milestones fall inside one week, so labelling them in
    # place would stack the text on top of itself. They are numbered on the
    # timeline and spelled out in a key underneath.
    # Five milestones fall inside one week and two share a date, so a marker
    # placed exactly on its date would sit under its neighbour. A left-to-right
    # sweep pushes each one just far enough to clear the last.
    marker_x: list[float] = []
    for when, _ in MILESTONES:
        x = day_x(when)
        if marker_x and x - marker_x[-1] < 21:
            x = marker_x[-1] + 21
        marker_x.append(x)

    for index, x in enumerate(marker_x):
        anchor_x = day_x(MILESTONES[index][0])
        parts.append(
            f'<path d="M{anchor_x:.0f},{output_top + 12:.0f} '
            f'L{anchor_x:.0f},{output_top + 19:.0f} '
            f'L{x:.0f},{output_top + 24:.0f}" fill="none" '
            'stroke="#B08A3E" stroke-width="1"/>'
            f'<circle cx="{x:.0f}" cy="{output_top + 33:.0f}" r="8.5" '
            'fill="#E8B84B" stroke="#B08A3E" stroke-width="1.2"/>'
            f'<text x="{x:.0f}" y="{output_top + 37:.0f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="10" font-weight="600" '
            f'fill="#5C4A18">{index + 1}</text>'
        )

    for index, (when, key) in enumerate(MILESTONES):
        column, row = divmod(index, 4)
        x = 16 + column * 620
        y = output_top + 62 + row * 15
        parts.append(
            f'<text x="{x}" y="{y:.0f}" font-family="{FONT}" font-size="10.5" '
            f'fill="#6B5A2E">{index + 1}. {when.strftime("%d.%m")} — '
            f'{say(key)}</text>'
        )

    # Commit density, read from the history rather than typed in.
    counts = commits_per_day()
    peak = max(counts.values(), default=1)
    parts.append(
        f'<text x="16" y="{density_top + 4:.0f}" font-family="{FONT}" '
        f'font-size="12" font-weight="600" fill="#4A4A45">'
        f'{say("density_header")}</text>'
    )
    base = density_top + 44
    for when, count in sorted(counts.items()):
        if not (START <= when <= END):
            continue
        x = day_x(when)
        bar = count / peak * 32
        parts.append(
            f'<rect x="{x - 4:.0f}" y="{base - bar:.0f}" width="8" '
            f'height="{bar:.0f}" rx="1.5" fill="#8FA9C4"/>'
            f'<text x="{x:.0f}" y="{base - bar - 4:.0f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="9" fill="#5A6B7C">{count}</text>'
        )
    parts.append(
        f'<path d="M{CHART_X},{base} H{CHART_X + CHART_WIDTH}" '
        'stroke="#DFDFDA" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{CHART_X + CHART_WIDTH / 2:.0f}" y="{base + 20:.0f}" '
        f'text-anchor="middle" font-family="{FONT}" font-size="10.5" '
        f'font-style="italic" fill="#8A8A84">{say("note_gap")}</text>'
    )

    # Legend.
    legend_y = base + 44
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
