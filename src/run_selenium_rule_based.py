import hashlib
import json
from pathlib import Path
from time import perf_counter

from rule_based_evaluator import (
    DOMAIN_RULES_FILE,
    evaluate_results,
    load_domain_rules,
)
from selenium_collector import (
    collect_search_results,
    create_browser,
)


# ==================================================
# File paths and method configuration
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_DIRECTORY = (
    PROJECT_ROOT
    / "results"
    / "selenium_rule_based"
)

METHOD_NAME = "selenium_rule_based"

ESTIMATED_COST_USD = 0.0


# ==================================================
# Pipeline execution
# ==================================================

def run_selenium_rule_based(
    product_id: str,
    keyword: str,
    max_results: int = 5,
) -> dict:
    """
    Selenium ile arama sonuçlarını toplar,
    rule-based evaluator ile değerlendirir
    ve ortak deney formatını döndürür.
    """

    domain_rules = load_domain_rules(
        DOMAIN_RULES_FILE
    )

    # perf_counter süre ölçümü için başlangıç
    # noktasını kaydeder.
    start_time = perf_counter()

    browser = create_browser()

    try:
        raw_results = collect_search_results(
            browser=browser,
            keyword=keyword,
            max_results=max_results,
        )

        evaluated_results = evaluate_results(
            results=raw_results,
            domain_rules=domain_rules,
        )

        # Veri toplama ve değerlendirme bittikten
        # sonra geçen süreyi hesapla.
        runtime_seconds = (
            perf_counter() - start_time
        )

    finally:
        browser.quit()

    output = {
        "product_id": product_id,
        "keyword": keyword,
        "method": METHOD_NAME,
        "runtime_seconds": round(
            runtime_seconds,
            2,
        ),
        "estimated_cost_usd": (
            ESTIMATED_COST_USD
        ),
        "results": evaluated_results,
    }

    return output


# ==================================================
# Output file generation
# ==================================================

def create_output_file_name(
    product_id: str,
    keyword: str,
) -> str:
    """
    Aynı product_id için birden fazla keyword
    kullanılabileceği için keyword'den kısa ve
    tekrarlanabilir bir kimlik üretir.
    """

    keyword_hash = hashlib.sha256(
        keyword.encode("utf-8")
    ).hexdigest()[:8]

    file_name = (
        f"{product_id}_"
        f"{METHOD_NAME}_"
        f"{keyword_hash}.json"
    )

    return file_name


def save_result(
    output: dict,
) -> Path:
    """
    Ortak deney çıktısını JSON dosyası olarak
    results klasörüne kaydeder.
    """

    RESULTS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file_name = (
        create_output_file_name(
            product_id=output["product_id"],
            keyword=output["keyword"],
        )
    )

    output_file_path = (
        RESULTS_DIRECTORY
        / output_file_name
    )

    with output_file_path.open(
        mode="w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            output,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    return output_file_path


# ==================================================
# Temporary single-keyword execution
# ==================================================

def main() -> None:
    """
    Pipeline'ı P001 ve tek bir test keyword'ü
    kullanarak uçtan uca çalıştırır.
    """

    product_id = "P001"

    keyword = (
        "iPhone 16 Pro Max 256 GB fiyat"
    )

    output = run_selenium_rule_based(
        product_id=product_id,
        keyword=keyword,
        max_results=5,
    )

    output_file_path = save_result(
        output
    )

    print()
    print(
        "=== SELENIUM RULE-BASED OUTPUT ==="
    )

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print(
        f"Result file saved: "
        f"{output_file_path}"
    )


if __name__ == "__main__":
    main()