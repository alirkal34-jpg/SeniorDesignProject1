import json
from pathlib import Path

import pandas as pd


# ==================================================
# File paths and configuration
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DOMAIN_RULES_FILE = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "trusted_ecommerce_domains.csv"
)

RELEVANCE_THRESHOLD = 0.60


# ==================================================
# Domain-rule loading
# ==================================================

def load_domain_rules(
    file_path: Path,
) -> dict:
    """
    Güvenilir e-ticaret domain listesini CSV'den
    yükler ve hızlı erişilebilecek bir dictionary
    yapısına dönüştürür.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Domain rules file bulunamadı: "
            f"{file_path}"
        )

    rules_df = pd.read_csv(file_path)

    required_columns = [
        "domain",
        "domain_type",
        "relevance_score",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in rules_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Domain rules dosyasında eksik "
            f"sütunlar var: {missing_columns}"
        )

    rules_df["domain"] = (
        rules_df["domain"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    rules_df["relevance_score"] = (
        pd.to_numeric(
            rules_df["relevance_score"],
            errors="coerce",
        )
    )

    invalid_score_condition = (
        rules_df["relevance_score"].isna()
        | ~rules_df["relevance_score"].between(
            0.0,
            1.0,
        )
    )

    if invalid_score_condition.any():
        invalid_rows = rules_df.loc[
            invalid_score_condition
        ]

        raise ValueError(
            "Geçersiz relevance score bulundu:\n"
            f"{invalid_rows}"
        )

    duplicate_domain_condition = (
        rules_df["domain"].duplicated(
            keep=False
        )
    )

    if duplicate_domain_condition.any():
        duplicate_domains = rules_df.loc[
            duplicate_domain_condition,
            "domain",
        ].tolist()

        raise ValueError(
            "Domain rules dosyasında duplicate "
            f"domain var: {duplicate_domains}"
        )

    domain_rules = {}

    for _, row in rules_df.iterrows():
        domain = row["domain"]

        domain_rules[domain] = {
            "domain_type": row["domain_type"],
            "relevance_score": float(
                row["relevance_score"]
            ),
        }

    return domain_rules


# ==================================================
# Individual-result evaluation
# ==================================================

def evaluate_result(
    result: dict,
    domain_rules: dict,
) -> dict:
    """
    Tek bir Selenium sonucunu domain listesine
    göre değerlendirir.

    Orijinal result dictionary'sini değiştirmez;
    kopyasını oluşturup değerlendirme alanlarını
    bu kopyaya ekler.
    """

    evaluated_result = result.copy()

    domain = (
        str(result.get("domain", ""))
        .strip()
        .lower()
    )

    domain_rule = domain_rules.get(domain)

    if domain_rule is None:
        relevance_score = 0.0
    else:
        relevance_score = (
            domain_rule["relevance_score"]
        )

    predicted_relevant = (
        relevance_score
        >= RELEVANCE_THRESHOLD
    )

    evaluated_result[
        "predicted_relevant"
    ] = predicted_relevant

    evaluated_result[
        "relevance_score"
    ] = relevance_score

    return evaluated_result


# ==================================================
# Result-list evaluation
# ==================================================

def evaluate_results(
    results: list[dict],
    domain_rules: dict,
) -> list[dict]:
    """
    Selenium tarafından toplanan bütün sonuçları
    tek tek evaluate_result fonksiyonuna gönderir.
    """

    evaluated_results = []

    for result in results:
        evaluated_result = evaluate_result(
            result=result,
            domain_rules=domain_rules,
        )

        evaluated_results.append(
            evaluated_result
        )

    return evaluated_results


# ==================================================
# Temporary manual test
# ==================================================

def main() -> None:
    """
    Evaluator'ı birkaç örnek Selenium sonucu
    kullanarak bağımsız biçimde test eder.
    """

    domain_rules = load_domain_rules(
        DOMAIN_RULES_FILE
    )

    sample_results = [
        {
            "domain": "akakce.com",
            "url": "https://www.akakce.com/example",
            "title": "iPhone 16 Pro Max Fiyatları",
            "snippet": "En uygun fiyat seçenekleri",
        },
        {
            "domain": "mediamarkt.com.tr",
            "url": (
                "https://www.mediamarkt.com.tr/"
                "example"
            ),
            "title": "Apple iPhone 16 Pro Max",
            "snippet": "Satın alma seçenekleri",
        },
        {
            "domain": "epey.com",
            "url": "https://www.epey.com/example",
            "title": "iPhone 16 Pro Max Özellikleri",
            "snippet": "Teknik özellik karşılaştırması",
        },
    ]

    evaluated_results = evaluate_results(
        results=sample_results,
        domain_rules=domain_rules,
    )

    print()
    print("=== RULE-BASED EVALUATION TEST ===")

    print(
        json.dumps(
            evaluated_results,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()