"""Render Figure 6, the labeling and measurement sequence, as a UML SVG.

Unlike Figure 5, this one sits in the UML section of the report, so it is
drawn as a real sequence diagram: lifelines, activation bars, filled
arrowheads for synchronous calls and open dashed ones for returns.

Three things in this sequence are design decisions rather than mechanics, and
the diagram is arranged so they are visible rather than described. The
workbook reaches the reviewer with the model's predictions removed. The
adjudication file enters as a separate found message, because it resolves
rows the reviewer left ambiguous and can never overwrite an answer the
reviewer gave. And the manifest is frozen before any metric is computed, so a
later run cannot change what a published number was calculated from.

Both languages come from one layout and one text table, so a label cannot be
corrected in one and left stale in the other.

    python reports_multicategory/figures/make_figure6.py

Writes figure6_labeling_sequence_EN.svg and sekil6_etiketleme_dizisi_TR.svg.
"""

from __future__ import annotations

from pathlib import Path


HERE = Path(__file__).resolve().parent
OUTPUTS = {
    "en": HERE / "figure6_labeling_sequence_EN.svg",
    "tr": HERE / "sekil6_etiketleme_dizisi_TR.svg",
}

# Wide enough that the self-message labels on the two right-hand lanes,
# which are the longest text in the diagram, stay inside the canvas.
WIDTH = 1400
FONT = "Segoe UI, Calibri, Arial, sans-serif"
MONO = "Consolas, Courier New, monospace"

ACTOR_FILL = ("#E3F1E4", "#3B7D42", "#1E4722")
TOOL_FILL = ("#DCE9F7", "#2C5D8F", "#123A5E")
LINE = "#5A5A55"

HEAD_Y = 40
HEAD_HEIGHT = 56
FIRST_MESSAGE = 150
PITCH = 54
SELF_HEIGHT = 34

# Participants, left to right. The order is the order they first act.
LANES = ["researcher", "export", "reviewer", "import", "manifest", "metrics"]
LANE_X = {name: 100 + index * 180 for index, name in enumerate(LANES)}
LANE_WIDTH = 164

TEXT: dict[str, dict[str, str]] = {
    "title": {
        "en": "Figure 6. Labeling and measurement sequence",
        "tr": "Şekil 6. Etiketleme ve ölçüm dizisi",
    },
    "researcher": {"en": "Researcher", "tr": "Araştırmacı"},
    "reviewer": {"en": "Reviewer", "tr": "Değerlendirici"},
    "actor": {"en": "«actor»", "tr": "«aktör»"},
    "tool": {"en": "«tool»", "tr": "«araç»"},
    "m_export": {
        "en": "export the unique URLs",
        "tr": "benzersiz URL'leri dışa aktar",
    },
    "m_workbook": {
        "en": "review workbook — model predictions removed",
        "tr": "değerlendirme kitabı — model tahminleri çıkarılmış",
    },
    "m_label": {
        "en": "label 193 unique URLs by hand",
        "tr": "193 benzersiz URL'yi elle etiketle",
    },
    "m_filled": {
        "en": "filled workbooks (134 + 61 rows)",
        "tr": "doldurulmuş kitaplar (134 + 61 satır)",
    },
    "m_import": {
        "en": "import the filled workbooks",
        "tr": "doldurulmuş kitapları içe aktar",
    },
    "m_adjudication": {
        "en": "adjudication file — 5 ambiguous rows",
        "tr": "hakem dosyası — 5 belirsiz satır",
    },
    "m_ground_truth": {
        "en": "multicategory_ground_truth.csv — 193 labels",
        "tr": "multicategory_ground_truth.csv — 193 etiket",
    },
    "m_manifest": {"en": "build the manifest", "tr": "manifesti üret"},
    "m_freeze": {
        "en": "freeze 80 result files, refuse a hole in the grid",
        "tr": "80 sonuç dosyasını dondur, ızgarada delik varsa reddet",
    },
    "m_manifest_out": {
        "en": "manifest.json — 80 files frozen",
        "tr": "manifest.json — 80 dosya donduruldu",
    },
    "m_metrics": {"en": "compute the metrics", "tr": "metrikleri hesapla"},
    "m_compute": {
        "en": "overall + per category, against the frozen set",
        "tr": "genel + kategori bazında, dondurulmuş küme üzerinden",
    },
    "m_report": {
        "en": "evaluation report",
        "tr": "değerlendirme raporu",
    },
    "note_blind": {
        "en": "The reviewer never sees a method's guess: showing it\nwould pull the label towards the model.",
        "tr": "Değerlendirici yöntemin tahminini görmez: görmesi\netiketi modele doğru kaydırırdı.",
    },
    "note_adjudication": {
        "en": "An adjudication record only resolves a row the reviewer\nleft ambiguous. It can never change an answer they gave.",
        "tr": "Hakem kaydı yalnızca değerlendiricinin belirsiz bıraktığı\nsatırı çözer. Verdiği bir cevabı asla değiştiremez.",
    },
}


class Sequence:
    def __init__(self, language: str) -> None:
        self.language = language
        self.parts: list[str] = []
        self.y = FIRST_MESSAGE
        self.activations: list[tuple[float, float, float]] = []

    def say(self, key: str) -> str:
        return TEXT[key][self.language]

    # -- participants -------------------------------------------------
    def header(self, name: str, label: str, stereotype: str, actor: bool) -> None:
        fill, stroke, colour = ACTOR_FILL if actor else TOOL_FILL
        centre = LANE_X[name]
        left = centre - LANE_WIDTH / 2
        self.parts.append(
            f'<rect x="{left:.0f}" y="{HEAD_Y}" width="{LANE_WIDTH}" '
            f'height="{HEAD_HEIGHT}" rx="6" fill="{fill}" stroke="{stroke}" '
            'stroke-width="1.5"/>'
        )
        self.parts.append(
            f'<text x="{centre:.0f}" y="{HEAD_Y + 21}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="10.5" fill="{colour}" '
            f'opacity="0.75">{stereotype}</text>'
        )
        font = FONT if actor else MONO
        self.parts.append(
            f'<text x="{centre:.0f}" y="{HEAD_Y + 40}" text-anchor="middle" '
            f'font-family="{font}" font-size="11.5" fill="{colour}">{label}</text>'
        )

    def lifelines(self, bottom: float) -> None:
        for name in LANES:
            centre = LANE_X[name]
            self.parts.append(
                f'<path d="M{centre:.0f},{HEAD_Y + HEAD_HEIGHT} '
                f'L{centre:.0f},{bottom:.0f}" stroke="#9A9A94" '
                'stroke-width="1.2" stroke-dasharray="6 5"/>'
            )

    def activate(self, name: str, start: float, end: float) -> None:
        self.activations.append((LANE_X[name], start, end))

    def draw_activations(self) -> None:
        for centre, start, end in self.activations:
            self.parts.append(
                f'<rect x="{centre - 6:.0f}" y="{start:.0f}" width="12" '
                f'height="{end - start:.0f}" fill="#FFFFFF" stroke="{LINE}" '
                'stroke-width="1.2"/>'
            )

    # -- messages -----------------------------------------------------
    def message(self, source: str, target: str, key: str, dashed: bool = False) -> float:
        y = self.y
        x1, x2 = LANE_X[source], LANE_X[target]
        direction = 1 if x2 > x1 else -1
        start = x1 + direction * 6
        end = x2 - direction * 6
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        head = "open" if dashed else "solid"
        self.parts.append(
            f'<path d="M{start:.0f},{y:.0f} L{end:.0f},{y:.0f}" fill="none" '
            f'stroke="{LINE}" stroke-width="1.5"{dash} '
            f'marker-end="url(#{head})"/>'
        )
        self.parts.append(
            f'<text x="{(x1 + x2) / 2:.0f}" y="{y - 8:.0f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="11.5" fill="#33332E">'
            f'{self.say(key)}</text>'
        )
        self.y += PITCH
        return y

    def self_message(self, name: str, key: str) -> float:
        y = self.y
        centre = LANE_X[name]
        self.parts.append(
            f'<path d="M{centre + 6:.0f},{y:.0f} L{centre + 44:.0f},{y:.0f} '
            f'L{centre + 44:.0f},{y + SELF_HEIGHT:.0f} '
            f'L{centre + 8:.0f},{y + SELF_HEIGHT:.0f}" fill="none" '
            f'stroke="{LINE}" stroke-width="1.5" marker-end="url(#solid)"/>'
        )
        self.parts.append(
            f'<text x="{centre + 52:.0f}" y="{y + SELF_HEIGHT / 2 + 4:.0f}" '
            f'text-anchor="start" font-family="{FONT}" font-size="11.5" '
            f'fill="#33332E">{self.say(key)}</text>'
        )
        self.y += SELF_HEIGHT + 24
        return y

    def found_message(self, target: str, key: str) -> float:
        """A message with no participant as its origin — the adjudication file."""

        y = self.y
        centre = LANE_X[target]
        origin = centre - 210
        self.parts.append(
            f'<circle cx="{origin:.0f}" cy="{y:.0f}" r="5" fill="{LINE}"/>'
        )
        self.parts.append(
            f'<path d="M{origin + 5:.0f},{y:.0f} L{centre - 6:.0f},{y:.0f}" '
            f'fill="none" stroke="{LINE}" stroke-width="1.5" '
            'marker-end="url(#solid)"/>'
        )
        self.parts.append(
            f'<text x="{origin - 10:.0f}" y="{y + 4:.0f}" text-anchor="end" '
            f'font-family="{FONT}" font-size="11.5" fill="#33332E">'
            f'{self.say(key)}</text>'
        )
        self.y += PITCH
        return y

    def note(self, x: float, y: float, key: str, width: float = 330) -> None:
        lines = self.say(key).split("\n")
        height = 14 + len(lines) * 15
        self.parts.append(
            f'<path d="M{x:.0f},{y:.0f} h{width - 14:.0f} l14,14 '
            f'v{height - 14:.0f} h-{width:.0f} z" fill="#FFFCEB" '
            'stroke="#C8B560" stroke-width="1.2"/>'
        )
        self.parts.append(
            f'<path d="M{x + width - 14:.0f},{y:.0f} v14 h14" fill="none" '
            'stroke="#C8B560" stroke-width="1.2"/>'
        )
        for index, line in enumerate(lines):
            self.parts.append(
                f'<text x="{x + 10:.0f}" y="{y + 19 + index * 15:.0f}" '
                f'font-family="{FONT}" font-size="10.5" fill="#5C5326">{line}</text>'
            )

    def render(self, height: float) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{height:.0f}" viewBox="0 0 {WIDTH} {height:.0f}">'
            '<defs>'
            '<marker id="solid" markerWidth="9" markerHeight="7" refX="8.5" '
            'refY="3.5" orient="auto">'
            f'<polygon points="0 0, 9 3.5, 0 7" fill="{LINE}"/></marker>'
            '<marker id="open" markerWidth="10" markerHeight="8" refX="9" '
            'refY="4" orient="auto">'
            f'<path d="M0,0 L9,4 L0,8" fill="none" stroke="{LINE}" '
            'stroke-width="1.4"/></marker>'
            '</defs>'
            f'<rect width="{WIDTH}" height="{height:.0f}" fill="#FFFFFF"/>'
            + "".join(self.parts)
            + "</svg>"
        )


def build(language: str) -> str:
    sequence = Sequence(language)
    say = sequence.say

    headers = [
        ("researcher", say("researcher"), say("actor"), True),
        ("export", "export_label_workbook", say("tool"), False),
        ("reviewer", say("reviewer"), say("actor"), True),
        ("import", "import_label_workbook", say("tool"), False),
        ("manifest", "build_manifest", say("tool"), False),
        ("metrics", "final_metrics /\ncategory_metrics", say("tool"), False),
    ]
    for name, label, stereotype, actor in headers:
        if "\n" in label:
            first, second = label.split("\n")
            centre = LANE_X[name]
            fill, stroke, colour = TOOL_FILL
            sequence.parts.append(
                f'<rect x="{centre - LANE_WIDTH / 2:.0f}" y="{HEAD_Y}" '
                f'width="{LANE_WIDTH}" height="{HEAD_HEIGHT}" rx="6" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
            )
            sequence.parts.append(
                f'<text x="{centre:.0f}" y="{HEAD_Y + 16}" text-anchor="middle" '
                f'font-family="{FONT}" font-size="10.5" fill="{colour}" '
                f'opacity="0.75">{stereotype}</text>'
            )
            sequence.parts.append(
                f'<text x="{centre:.0f}" y="{HEAD_Y + 33}" text-anchor="middle" '
                f'font-family="{MONO}" font-size="10.5" fill="{colour}">{first}</text>'
            )
            sequence.parts.append(
                f'<text x="{centre:.0f}" y="{HEAD_Y + 47}" text-anchor="middle" '
                f'font-family="{MONO}" font-size="10.5" fill="{colour}">{second}</text>'
            )
        else:
            sequence.header(name, label, stereotype, actor)

    export_start = sequence.y - 12
    sequence.message("researcher", "export", "m_export")
    sequence.message("export", "reviewer", "m_workbook")
    sequence.activate("export", export_start, sequence.y - PITCH + 12)

    review_start = sequence.y - 12
    sequence.self_message("reviewer", "m_label")
    sequence.message("reviewer", "researcher", "m_filled", dashed=True)
    sequence.activate("reviewer", review_start, sequence.y - PITCH + 12)

    import_start = sequence.y - 12
    sequence.message("researcher", "import", "m_import")
    sequence.found_message("import", "m_adjudication")
    sequence.message("import", "researcher", "m_ground_truth", dashed=True)
    sequence.activate("import", import_start, sequence.y - PITCH + 12)

    manifest_start = sequence.y - 12
    sequence.message("researcher", "manifest", "m_manifest")
    sequence.self_message("manifest", "m_freeze")
    sequence.message("manifest", "researcher", "m_manifest_out", dashed=True)
    sequence.activate("manifest", manifest_start, sequence.y - PITCH + 12)

    metrics_start = sequence.y - 12
    sequence.message("researcher", "metrics", "m_metrics")
    sequence.self_message("metrics", "m_compute")
    sequence.message("metrics", "researcher", "m_report", dashed=True)
    sequence.activate("metrics", metrics_start, sequence.y - PITCH + 12)

    bottom = sequence.y - PITCH + 30
    sequence.activate("researcher", FIRST_MESSAGE - 12, bottom)

    sequence.lifelines(bottom)
    sequence.draw_activations()

    notes_top = bottom + 24
    sequence.note(40, notes_top, "note_blind", width=360)
    sequence.note(430, notes_top, "note_adjudication", width=430)

    title_height = notes_top + 70
    sequence.parts.insert(
        0,
        f'<text x="{WIDTH / 2:.0f}" y="26" text-anchor="middle" '
        f'font-family="{FONT}" font-size="14" font-weight="600" '
        f'fill="#33332E">{say("title")}</text>',
    )
    return sequence.render(title_height)


def main() -> None:
    for language, path in OUTPUTS.items():
        path.write_text(build(language), encoding="utf-8")
        print(f"{language}: {path.name}")


if __name__ == "__main__":
    main()
