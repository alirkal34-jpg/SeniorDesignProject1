"""Check that the experiment, the metrics and the written report agree.

Numbers in this project travel a long way: a search result becomes a JSON
file, the file is labeled by hand, the label is matched back by URL, the match
becomes a metric, and the metric is quoted in the report. Every hop is a place
where the report can end up claiming something the data no longer says.

This walks the whole chain and fails loudly on the first disagreement, so a
single command answers the question "is anything inconsistent right now?".

    .venv\\Scripts\\python.exe src\\evaluation\\check_consistency.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.category_metrics import build_category_report  # noqa: E402
from evaluation.final_metrics import build_final_metrics_report  # noqa: E402
from evaluation.ground_truth import (  # noqa: E402
    build_ground_truth_lookup,
    find_human_label,
    load_ground_truth,
)

MANIFESTS = PROJECT_ROOT / "data" / "evaluation"
# Which stored report each manifest is supposed to produce. Reading a metrics
# file and checking it against itself proves nothing: a stale file agrees with
# itself perfectly. These are recomputed from the manifests instead.
RECOMPUTABLE = (
    (
        "telefon (dondurulmus)",
        MANIFESTS / "final_evaluation_manifest.json",
        PROJECT_ROOT / "reports" / "final_evaluation_metrics.json",
        None,
    ),
    (
        "cok kategori (v1)",
        MANIFESTS / "final_evaluation_manifest_multicategory.json",
        PROJECT_ROOT
        / "reports_multicategory"
        / "multicategory_evaluation_metrics.json",
        PROJECT_ROOT
        / "reports_multicategory"
        / "multicategory_category_metrics.json",
    ),
    (
        "hizalanmis istem (v2)",
        MANIFESTS / "final_evaluation_manifest_prompt_v2.json",
        PROJECT_ROOT
        / "reports_multicategory"
        / "prompt_v2_evaluation_metrics.json",
        PROJECT_ROOT / "reports_multicategory" / "prompt_v2_category_metrics.json",
    ),
)

V1_RESULTS = PROJECT_ROOT / "results_multicategory"
V2_RESULTS = PROJECT_ROOT / "results_multicategory_prompt_v2"
GROUND_TRUTH = PROJECT_ROOT / "data" / "labels" / "multicategory_ground_truth.csv"
REPORT = PROJECT_ROOT / "reports_multicategory" / "SDP_rapor_TR.md"
REPORTS = PROJECT_ROOT / "reports_multicategory"
FROZEN_PHONE = PROJECT_ROOT / "reports" / "final_evaluation_metrics.json"

RULE_METHOD = "selenium_rule_based"


class Checker:
    """Collects pass/fail lines so every check runs before the verdict."""

    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        mark = "OK " if ok else "HATA"
        print(f"  [{mark}] {name}" + (f"  -> {detail}" if detail else ""))
        if not ok:
            self.failures.append(name)


def load_results(root: Path) -> dict[tuple[str, str], dict]:
    payloads = {}
    for path in root.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        payloads[(data["product_id"], data["method"])] = data
    return payloads


def fixed_part(payload: dict) -> list:
    return [
        (item["url"], item["title"], item["snippet"])
        for item in payload["results"]
    ]


def confusion(payloads: dict, lookup) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for (_, method), payload in payloads.items():
        slot = counts.setdefault(
            method, {"tp": 0, "tn": 0, "fp": 0, "fn": 0, "unlabeled": 0}
        )
        for item in payload["results"]:
            human = find_human_label(
                lookup=lookup,
                product_id=payload["product_id"],
                keyword=payload["keyword"],
                method=method,
                domain=item["domain"],
                url=item["url"],
            )
            if human is None:
                slot["unlabeled"] += 1
                continue
            predicted = bool(item["predicted_relevant"])
            if predicted and human:
                slot["tp"] += 1
            elif not predicted and not human:
                slot["tn"] += 1
            elif predicted:
                slot["fp"] += 1
            else:
                slot["fn"] += 1
    return counts


def main() -> int:
    checker = Checker()
    lookup = build_ground_truth_lookup(load_ground_truth(GROUND_TRUTH))
    labels = list(csv.DictReader(GROUND_TRUTH.open(encoding="utf-8")))

    print("=== 1. TEMEL DOGRULUK ===")
    checker.check("etiket sayisi 193", len(labels) == 193, str(len(labels)))
    keys = {(r["product_id"], r["url"].rstrip("/").lower()) for r in labels}
    checker.check("tekrar eden URL yok", len(keys) == len(labels))
    values = {r["human_relevant"] for r in labels}
    checker.check(
        "etiketler yalnizca true/false", values <= {"true", "false"}, str(values)
    )
    relevant = sum(1 for r in labels if r["human_relevant"] == "true")
    checker.check("140 uygun / 53 uygunsuz", relevant == 140, f"{relevant} uygun")
    adjudicated = sum(1 for r in labels if "[adjudicated:" in r["notes"])
    checker.check("5 hakem karari izlenebilir", adjudicated == 5, str(adjudicated))

    print()
    print("=== 2. SONUC DOSYALARI ===")
    v1, v2 = load_results(V1_RESULTS), load_results(V2_RESULTS)
    checker.check("v1 80 kosum", len(v1) == 80, str(len(v1)))
    checker.check("v2 80 kosum", len(v2) == 80, str(len(v2)))
    checker.check("ayni urun/yontem izgarasi", set(v1) == set(v2))
    same_content = all(fixed_part(v1[k]) == fixed_part(v2[k]) for k in v1)
    checker.check("arama sonuclari degismemis (url+baslik+ozet)", same_content)

    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    rule_same = all(
        digest(a) == digest(V2_RESULTS / a.relative_to(V1_RESULTS))
        for a in (V1_RESULTS / RULE_METHOD).glob("*.json")
    )
    checker.check("kontrol grubu bit duzeyinde ayni", rule_same)

    v2_models = {
        p["model"] for k, p in v2.items() if k[1] != RULE_METHOD
    }
    checker.check(
        "v2 tek uc noktada tekil", len(v2_models) == 1, ", ".join(sorted(v2_models))
    )
    v2_prompts = {
        p.get("prompt_version") for k, p in v2.items() if k[1] != RULE_METHOD
    }
    checker.check(
        "v2 tek istem surumu",
        v2_prompts == {"relevance-v2-aligned"},
        ", ".join(sorted(str(x) for x in v2_prompts)),
    )

    print()
    print("=== 3. ETIKET KAPSAMI VE KARISIKLIK MATRISI ===")
    for name, payloads in (("v1", v1), ("v2", v2)):
        counts = confusion(payloads, lookup)
        unlabeled = sum(c["unlabeled"] for c in counts.values())
        total = sum(c["tp"] + c["tn"] + c["fp"] + c["fn"] for c in counts.values())
        checker.check(f"{name}: etiketsiz sonuc yok", unlabeled == 0, str(unlabeled))
        checker.check(f"{name}: 399 etiketli sonuc", total == 399, str(total))

    print()
    print("=== 4. METRIK DOSYALARI KENDI ICINDE TUTARLI MI ===")
    for stem in ("multicategory", "prompt_v2"):
        cat = json.loads(
            (REPORTS / f"{stem}_category_metrics.json").read_text(encoding="utf-8")
        )
        for method, payload in cat["methods"].items():
            o = payload["overall"]
            n = o["labeled_result_count"]
            quadrants = (
                o["true_positive_count"]
                + o["true_negative_count"]
                + o["false_positive_count"]
                + o["false_negative_count"]
            )
            checker.check(f"{stem}/{method}: TP+TN+FP+FN = n", quadrants == n)
            expected = round(
                (o["true_positive_count"] + o["true_negative_count"]) / n, 4
            )
            checker.check(
                f"{stem}/{method}: dogruluk tutarli", expected == o["accuracy"]
            )
            denominator = o["true_negative_count"] + o["false_positive_count"]
            if denominator:
                spec = round(o["true_negative_count"] / denominator, 4)
                checker.check(
                    f"{stem}/{method}: ozgulluk tutarli", spec == o["specificity"]
                )

    print()
    print("=== 5. KONTROL GRUBU DEGISMEMIS OLMALI ===")
    a = json.loads(
        (REPORTS / "multicategory_category_metrics.json").read_text(encoding="utf-8")
    )["methods"][RULE_METHOD]["overall"]
    b = json.loads(
        (REPORTS / "prompt_v2_category_metrics.json").read_text(encoding="utf-8")
    )["methods"][RULE_METHOD]["overall"]
    checker.check("kural tabanli metrikleri ayni", a == b)

    print()
    print("=== 6. RAPORDAKI SAYILAR METRIKLERLE TUTUYOR MU ===")
    report = REPORT.read_text(encoding="utf-8")
    m1 = json.loads(
        (REPORTS / "multicategory_evaluation_metrics.json").read_text(encoding="utf-8")
    )
    m2 = json.loads(
        (REPORTS / "prompt_v2_evaluation_metrics.json").read_text(encoding="utf-8")
    )
    c2 = json.loads(
        (REPORTS / "prompt_v2_category_metrics.json").read_text(encoding="utf-8")
    )
    # The report quotes ratios at three decimals. Rounding, not truncating:
    # 0.7826 is written 0,783 there, and a truncated 0,782 would raise a
    # disagreement that only exists in this checker.
    tr = lambda value: f"{value:.3f}".replace(".", ",")
    pct = lambda value: f"{value * 100:.2f}".replace(".", ",")

    claims = [
        (f"%{pct(m1['accuracy'])}", "v1 genel dogruluk"),
        (f"%{pct(m2['accuracy'])}", "v2 genel dogruluk"),
        (str(m1["labeled_result_count"]), "etiketli sonuc sayisi"),
    ]
    for method in ("selenium_nano_llm", "agentic_search", "tavily_llm"):
        spec = c2["methods"][method]["overall"]["specificity"]
        claims.append((tr(spec), f"{method} v2 ozgulluk"))
    for text, label in claims:
        checker.check(f"raporda geciyor: {text} ({label})", text in report)

    stale = [x for x in ("%83,21", "0,826", "348 test") if x in report]
    checker.check("eski degerler temizlenmis", not stale, ", ".join(stale))

    print()
    print("=== 7. DONDURULMUS TELEFON DENEYI ===")
    phone = json.loads(FROZEN_PHONE.read_text(encoding="utf-8"))
    checker.check("telefon dogrulugu 0.6884", phone["accuracy"] == 0.6884)
    checker.check("telefon 199 etiketli sonuc", phone["labeled_result_count"] == 199)

    print()
    print("=== 8. METRIKLER MANIFESTTEN YENIDEN URETILEBILIYOR MU ===")
    for label, manifest, metrics_file, category_file in RECOMPUTABLE:
        if not manifest.exists():
            checker.check(f"{label}: manifest mevcut", False, str(manifest))
            continue

        stored = json.loads(metrics_file.read_text(encoding="utf-8"))
        rebuilt = build_final_metrics_report(manifest)
        checker.check(
            f"{label}: genel metrikler yeniden uretiliyor",
            rebuilt == stored,
            f"dogruluk {rebuilt['accuracy']}",
        )

        if category_file is None:
            continue

        stored_categories = json.loads(category_file.read_text(encoding="utf-8"))
        rebuilt_categories = build_category_report(manifest)
        checker.check(
            f"{label}: kategori metrikleri yeniden uretiliyor",
            rebuilt_categories == stored_categories,
        )

    print()
    if checker.failures:
        print(f"SONUC: {len(checker.failures)} TUTARSIZLIK")
        for name in checker.failures:
            print(f"   - {name}")
        return 1

    print("SONUC: tutarsizlik bulunmadi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
