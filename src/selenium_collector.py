import json
from urllib.parse import parse_qs
from urllib.parse import quote_plus
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ==================================================
# Browser creation
# ==================================================

def create_browser() -> webdriver.Chrome:
    """
    Selenium tarafından kontrol edilecek
    Chrome tarayıcısını oluşturur.
    """

    chrome_options = Options()

    chrome_options.add_argument(
        "--start-maximized"
    )

    browser = webdriver.Chrome(
        options=chrome_options
    )

    return browser


# ==================================================
# URL processing
# ==================================================

def normalize_result_url(url: str) -> str:
    """
    Google yönlendirme URL'si varsa gerçek hedef
    URL'yi çıkarır. Normal bir URL geldiyse
    değiştirmeden döndürür.
    """

    parsed_url = urlparse(url)

    is_google_redirect = (
        parsed_url.netloc.endswith("google.com")
        and parsed_url.path == "/url"
    )

    if is_google_redirect:
        query_parameters = parse_qs(
            parsed_url.query
        )

        target_urls = query_parameters.get(
            "q",
            [],
        )

        if target_urls:
            return target_urls[0]

    return url


def extract_domain(url: str) -> str:
    """
    Tam URL içerisinden yalnızca domain bilgisini
    çıkarır.

    Örnek:
    https://www.trendyol.com/apple/...
    -> trendyol.com
    """

    parsed_url = urlparse(url)

    domain = parsed_url.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


# ==================================================
# Search-result extraction
# ==================================================

def extract_snippet(
    heading,
) -> str:
    """
    Bir Google sonucunun başlığından hareketle
    aynı sonuç kutusundaki snippet metnini bulur.

    Snippet bulunamazsa boş string döndürür.
    """

    result_containers = heading.find_elements(
        By.XPATH,
        (
            "./ancestor::div"
            "[contains(@class, 'MjjYud')][1]"
        ),
    )

    if not result_containers:
        return ""

    result_container = result_containers[0]

    snippet_elements = (
        result_container.find_elements(
            By.CSS_SELECTOR,
            "div.VwiC3b",
        )
    )

    if not snippet_elements:
        return ""

    return snippet_elements[0].text.strip()


def collect_search_results(
    browser: webdriver.Chrome,
    keyword: str,
    max_results: int = 5,
) -> list[dict]:
    """
    Google üzerinde verilen keyword ile arama yapar
    ve organik sonuçları standart bir liste olarak
    döndürür.
    """

    encoded_keyword = quote_plus(keyword)

    search_url = (
        "https://www.google.com/search"
        f"?q={encoded_keyword}"
    )

    print(
        f"Searching keyword: {keyword}",
        flush=True,
    )

    browser.get(search_url)

    wait = WebDriverWait(
        browser,
        20,
    )

    try:
        wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "h3",
                )
            )
        )

    except TimeoutException as error:
        raise RuntimeError(
            "Google sonuç başlıkları bulunamadı. "
            "Consent veya CAPTCHA sayfası açılmış olabilir. "
            f"Current URL: {browser.current_url}"
        ) from error

    heading_elements = (
        browser.find_elements(
            By.CSS_SELECTOR,
            "h3",
        )
    )

    collected_results = []
    seen_urls = set()

    for heading in heading_elements:
        title = heading.text.strip()

        if not title:
            continue

        link_elements = heading.find_elements(
            By.XPATH,
            "./ancestor::a[1]",
        )

        if not link_elements:
            continue

        raw_url = link_elements[0].get_attribute(
            "href"
        )

        if not raw_url:
            continue

        result_url = normalize_result_url(
            raw_url
        )

        if not result_url.startswith(
            ("http://", "https://")
        ):
            continue

        domain = extract_domain(
            result_url
        )

        # Google'ın kendi navigasyon bağlantılarını
        # organik sonuç olarak kaydetme.
        if domain.endswith("google.com"):
            continue

        # Aynı URL birden fazla kez bulunursa
        # yalnızca ilkini kaydet.
        if result_url in seen_urls:
            continue

        snippet = extract_snippet(
            heading
        )

        result = {
            "domain": domain,
            "url": result_url,
            "title": title,
            "snippet": snippet,
        }

        collected_results.append(
            result
        )

        seen_urls.add(
            result_url
        )

        if len(collected_results) >= max_results:
            break

    return collected_results


# ==================================================
# Temporary manual test
# ==================================================

def main() -> None:
    """
    Collector modülünü tek ürün ve tek keyword
    kullanarak test eder.
    """

    product_id = "P001"

    keyword = (
        "iPhone 16 Pro Max 256 GB fiyat"
    )

    browser = create_browser()

    try:
        results = collect_search_results(
            browser=browser,
            keyword=keyword,
            max_results=5,
        )

        output = {
            "product_id": product_id,
            "keyword": keyword,
            "results": results,
        }

        print()
        print("=== COLLECTED SEARCH RESULTS ===")

        print(
            json.dumps(
                output,
                ensure_ascii=False,
                indent=2,
            )
        )

        print()
        print(
            f"Collected result count: "
            f"{len(results)}"
        )

        input(
            "Tarayıcıyı kapatmak için "
            "Enter tuşuna bas..."
        )

    finally:
        browser.quit()


if __name__ == "__main__":
    main()