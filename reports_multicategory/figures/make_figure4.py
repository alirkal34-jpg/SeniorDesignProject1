"""Render Figure 4, the use case diagram, as a UML SVG.

Drawn to the notation: actors as stick figures outside a system boundary,
use cases as ellipses inside it, plain association lines to the actors, and
dashed dependencies for «include» and «extend» pointing the way UML requires
— an include points from the base to the included case, an extend points from
the extension back to the base.

Two of those dependencies carry the design decisions the report argues for.
Exporting the workbook always includes hiding the model's predictions, so a
reviewer cannot be shown a guess before making a judgment. And an ambiguous
row extends into adjudication rather than being resolved inside the labeling
step, which is what keeps an adjudicator from overwriting an answer the
reviewer actually gave.

Both languages come from one layout and one text table, so a label cannot be
corrected in one and left stale in the other.

    python reports_multicategory/figures/make_figure4.py

Writes figure4_use_cases_EN.svg and sekil4_kullanim_senaryolari_TR.svg.
"""

from __future__ import annotations

from pathlib import Path


HERE = Path(__file__).resolve().parent
OUTPUTS = {
    "en": HERE / "figure4_use_cases_EN.svg",
    "tr": HERE / "sekil4_kullanim_senaryolari_TR.svg",
}

WIDTH = 1280
HEIGHT = 800
FONT = "Segoe UI, Calibri, Arial, sans-serif"

LINE = "#5A5A55"
ACTOR_COLOUR = "#2E5E34"
EXTERNAL_COLOUR = "#8A5A0B"
CASE_FILL = "#DCE9F7"
CASE_STROKE = "#2C5D8F"
CASE_TEXT = "#123A5E"
SUPPORT_FILL = "#EFE9FA"
SUPPORT_STROKE = "#5B47A0"
SUPPORT_TEXT = "#2E2258"

BOUNDARY = (250, 66, 748, 672)  # x, y, width, height

ACTOR_X = 96
EXTERNAL_X = 1150

CASE_X = 470
CASE_RX = 156
CASE_RY = 27

SUPPORT_X = 832
SUPPORT_RX = 132

CASES = {
    "uc1": 124,
    "uc2": 199,
    "uc3": 274,
    "uc4": 349,
    "uc5": 455,
    "uc6": 530,
    "uc7": 605,
    "uc8": 690,
}
SUPPORTS = {"hide": 455, "adjudicate": 605}

ACTORS = {"researcher": 250, "reviewer": 530, "advisor": 690}
# A stick figure plus its two-line name is about 90px tall, so the external
# actors need at least that much between them or the names collide.
EXTERNALS = {"akakce": 120, "openrouter": 245, "bing": 350, "tavily": 455}

TEXT: dict[str, dict[str, str]] = {
    "title": {
        "en": "Figure 4. Use case diagram",
        "tr": "Şekil 4. Kullanım senaryosu diyagramı",
    },
    "system": {
        "en": "E-Commerce Relevance Evaluation System",
        "tr": "E-Ticaret Uygunluk Değerlendirme Sistemi",
    },
    "researcher": {"en": "Researcher\n(student)", "tr": "Araştırmacı\n(öğrenci)"},
    "reviewer": {"en": "Reviewer\n(human)", "tr": "Değerlendirici\n(insan)"},
    "advisor": {"en": "Advisor", "tr": "Danışman"},
    "akakce": {"en": "Akakçe\n(data source)", "tr": "Akakçe\n(veri kaynağı)"},
    "openrouter": {"en": "OpenRouter\n(language model)", "tr": "OpenRouter\n(dil modeli)"},
    "bing": {"en": "Bing\n(Selenium search)", "tr": "Bing\n(Selenium araması)"},
    "tavily": {"en": "Tavily\n(search API)", "tr": "Tavily\n(arama API'si)"},
    "uc1": {"en": "UC1: Collect product data", "tr": "UC1: Ürün verisi topla"},
    "uc2": {
        "en": "UC2: Clean and validate the data",
        "tr": "UC2: Veriyi temizle ve doğrula",
    },
    "uc3": {"en": "UC3: Generate keywords", "tr": "UC3: Anahtar kelime üret"},
    "uc4": {"en": "UC4: Run the four methods", "tr": "UC4: Dört yöntemi çalıştır"},
    "uc5": {
        "en": "UC5: Export the labeling workbook",
        "tr": "UC5: Etiketleme kitabı üret",
    },
    "uc6": {"en": "UC6: Label the URLs by hand", "tr": "UC6: URL'leri elle etiketle"},
    "uc7": {"en": "UC7: Build the ground truth", "tr": "UC7: Temel doğruluk üret"},
    "uc8": {
        "en": "UC8: Compute the metrics\nand render the report",
        "tr": "UC8: Metrik hesapla\nve rapor üret",
    },
    "hide": {
        "en": "Hide the model\npredictions",
        "tr": "Model tahminlerini\ngizle",
    },
    "adjudicate": {
        "en": "Resolve an ambiguous\nrow by adjudication",
        "tr": "Belirsiz satırı\nhakeme taşı",
    },
    "include": {"en": "«include»", "tr": "«include»"},
    "extend": {"en": "«extend»", "tr": "«extend»"},
    "legend_actor": {"en": "primary actor", "tr": "birincil aktör"},
    "legend_external": {"en": "external system", "tr": "dış sistem"},
    "note": {
        "en": "An «extend» is conditional: a row reaches adjudication only when the "
              "reviewer left it ambiguous.",
        "tr": "«extend» koşulludur: bir satır hakeme yalnızca değerlendirici onu "
              "belirsiz bıraktığında gider.",
    },
}


class UseCaseDiagram:
    def __init__(self, language: str) -> None:
        self.language = language
        self.parts: list[str] = []

    def say(self, key: str) -> str:
        return TEXT[key][self.language]

    # -- primitives ---------------------------------------------------
    def lines_of(self, key: str) -> list[str]:
        return self.say(key).split("\n")

    def actor(self, x: float, y: float, key: str, colour: str) -> None:
        """A UML stick figure with its name underneath."""

        self.parts.append(
            f'<circle cx="{x:.0f}" cy="{y - 26:.0f}" r="9" fill="none" '
            f'stroke="{colour}" stroke-width="1.8"/>'
            f'<path d="M{x:.0f},{y - 17:.0f} V{y + 6:.0f} '
            f'M{x - 13:.0f},{y - 8:.0f} H{x + 13:.0f} '
            f'M{x:.0f},{y + 6:.0f} L{x - 11:.0f},{y + 24:.0f} '
            f'M{x:.0f},{y + 6:.0f} L{x + 11:.0f},{y + 24:.0f}" '
            f'fill="none" stroke="{colour}" stroke-width="1.8" '
            'stroke-linecap="round"/>'
        )
        for index, line in enumerate(self.lines_of(key)):
            self.parts.append(
                f'<text x="{x:.0f}" y="{y + 42 + index * 14:.0f}" '
                f'text-anchor="middle" font-family="{FONT}" font-size="11.5" '
                f'fill="{colour}">{line}</text>'
            )

    def ellipse(
        self,
        x: float,
        y: float,
        rx: float,
        key: str,
        fill: str,
        stroke: str,
        colour: str,
    ) -> None:
        self.parts.append(
            f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rx:.0f}" ry="{CASE_RY}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
        )
        lines = self.lines_of(key)
        start = y + 4 - (len(lines) - 1) * 7
        for index, line in enumerate(lines):
            self.parts.append(
                f'<text x="{x:.0f}" y="{start + index * 14:.0f}" '
                f'text-anchor="middle" font-family="{FONT}" font-size="11.5" '
                f'fill="{colour}">{line}</text>'
            )

    def association(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.parts.append(
            f'<path d="M{x1:.0f},{y1:.0f} L{x2:.0f},{y2:.0f}" fill="none" '
            f'stroke="{LINE}" stroke-width="1.3"/>'
        )

    def dependency(
        self, x1: float, y1: float, x2: float, y2: float, key: str
    ) -> None:
        self.parts.append(
            f'<path d="M{x1:.0f},{y1:.0f} L{x2:.0f},{y2:.0f}" fill="none" '
            f'stroke="{SUPPORT_STROKE}" stroke-width="1.4" '
            'stroke-dasharray="7 4" marker-end="url(#open)"/>'
        )
        self.parts.append(
            f'<text x="{(x1 + x2) / 2:.0f}" y="{(y1 + y2) / 2 - 7:.0f}" '
            f'text-anchor="middle" font-family="{FONT}" font-size="11" '
            f'font-style="italic" fill="{SUPPORT_STROKE}">{self.say(key)}</text>'
        )

    def render(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">'
            '<defs><marker id="open" markerWidth="10" markerHeight="8" '
            'refX="9" refY="4" orient="auto">'
            f'<path d="M0,0 L9,4 L0,8" fill="none" stroke="{SUPPORT_STROKE}" '
            'stroke-width="1.4"/></marker></defs>'
            f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#FFFFFF"/>'
            + "".join(self.parts)
            + "</svg>"
        )


def build(language: str) -> str:
    diagram = UseCaseDiagram(language)

    diagram.parts.append(
        f'<text x="{WIDTH / 2:.0f}" y="30" text-anchor="middle" '
        f'font-family="{FONT}" font-size="14" font-weight="600" '
        f'fill="#33332E">{diagram.say("title")}</text>'
    )

    # System boundary.
    bx, by, bw, bh = BOUNDARY
    diagram.parts.append(
        f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="8" '
        'fill="#FCFCFB" stroke="#7A7A72" stroke-width="1.6"/>'
    )
    diagram.parts.append(
        f'<text x="{bx + bw / 2:.0f}" y="{by + 24}" text-anchor="middle" '
        f'font-family="{FONT}" font-size="12.5" font-weight="600" '
        f'fill="#4A4A45">{diagram.say("system")}</text>'
    )

    # Use cases.
    for key, y in CASES.items():
        diagram.ellipse(CASE_X, y, CASE_RX, key, CASE_FILL, CASE_STROKE, CASE_TEXT)
    for key, y in SUPPORTS.items():
        diagram.ellipse(
            SUPPORT_X, y, SUPPORT_RX, key, SUPPORT_FILL, SUPPORT_STROKE, SUPPORT_TEXT
        )

    # Actors and their associations.
    for key, y in ACTORS.items():
        diagram.actor(ACTOR_X, y, key, ACTOR_COLOUR)

    researcher_cases = ["uc1", "uc2", "uc3", "uc4", "uc5", "uc7", "uc8"]
    for key in researcher_cases:
        diagram.association(
            ACTOR_X + 16, ACTORS["researcher"] - 8,
            CASE_X - CASE_RX - 2, CASES[key],
        )
    diagram.association(
        ACTOR_X + 16, ACTORS["reviewer"] - 8, CASE_X - CASE_RX - 2, CASES["uc6"]
    )
    diagram.association(
        ACTOR_X + 16, ACTORS["advisor"] - 8, CASE_X - CASE_RX - 2, CASES["uc8"]
    )

    # External systems, drawn as secondary actors on the right.
    for key, y in EXTERNALS.items():
        diagram.actor(EXTERNAL_X, y, key, EXTERNAL_COLOUR)
    for key, case in (
        ("akakce", "uc1"),
        ("openrouter", "uc3"),
        ("bing", "uc4"),
        ("tavily", "uc4"),
    ):
        diagram.association(
            EXTERNAL_X - 16, EXTERNALS[key] - 8,
            CASE_X + CASE_RX + 2, CASES[case],
        )

    # «include» points from the base case to the included one; «extend»
    # points from the extension back to the base.
    diagram.dependency(
        CASE_X + CASE_RX + 2, CASES["uc5"],
        SUPPORT_X - SUPPORT_RX - 2, SUPPORTS["hide"], "include",
    )
    diagram.dependency(
        SUPPORT_X - SUPPORT_RX - 2, SUPPORTS["adjudicate"],
        CASE_X + CASE_RX + 2, CASES["uc7"], "extend",
    )

    # Legend and the one note the notation cannot carry on its own.
    legend_y = by + bh + 34
    diagram.parts.append(
        f'<circle cx="60" cy="{legend_y - 4:.0f}" r="6" fill="none" '
        f'stroke="{ACTOR_COLOUR}" stroke-width="1.8"/>'
        f'<text x="76" y="{legend_y:.0f}" font-family="{FONT}" font-size="11" '
        f'fill="{ACTOR_COLOUR}">{diagram.say("legend_actor")}</text>'
    )
    diagram.parts.append(
        f'<circle cx="230" cy="{legend_y - 4:.0f}" r="6" fill="none" '
        f'stroke="{EXTERNAL_COLOUR}" stroke-width="1.8"/>'
        f'<text x="246" y="{legend_y:.0f}" font-family="{FONT}" font-size="11" '
        f'fill="{EXTERNAL_COLOUR}">{diagram.say("legend_external")}</text>'
    )
    diagram.parts.append(
        f'<text x="420" y="{legend_y:.0f}" font-family="{FONT}" font-size="11" '
        f'font-style="italic" fill="#6B6B66">{diagram.say("note")}</text>'
    )

    return diagram.render()


def main() -> None:
    for language, path in OUTPUTS.items():
        path.write_text(build(language), encoding="utf-8")
        print(f"{language}: {path.name}")


if __name__ == "__main__":
    main()
