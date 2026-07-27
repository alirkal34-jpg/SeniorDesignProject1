import base64
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


SUPPORTED_SEARCH_ENGINES = ("google", "bing")


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

    is_bing_redirect = (
        parsed_url.netloc.endswith("bing.com")
        and parsed_url.path == "/ck/a"
    )

    if is_bing_redirect:
        query_parameters = parse_qs(
            parsed_url.query
        )
        encoded_targets = query_parameters.get(
            "u",
            [],
        )

        if encoded_targets:
            encoded_target = encoded_targets[0]
            if encoded_target.startswith("a1"):
                encoded_target = encoded_target[2:]
            padding = "=" * (-len(encoded_target) % 4)
            try:
                target_url = base64.urlsafe_b64decode(
                    encoded_target + padding
                ).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                target_url = ""

            if target_url.startswith(
                ("http://", "https://")
            ):
                return target_url

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


def extract_bing_snippet(link) -> str:
    """
    Bir Bing sonucunun linkinden hareketle aynı
    sonuç kutusundaki snippet metnini bulur.
    """

    result_containers = link.find_elements(
        By.XPATH,
        "./ancestor::li[contains(@class, 'b_algo')][1]",
    )

    if not result_containers:
        return ""

    snippet_elements = result_containers[0].find_elements(
        By.CSS_SELECTOR,
        "div.b_caption p, p",
    )

    if not snippet_elements:
        return ""

    return snippet_elements[0].text.strip()


def collect_search_results(
    browser: webdriver.Chrome,
    keyword: str,
    max_results: int = 5,
    search_engine: str = "bing",
) -> list[dict]:
    """
    Seçilen arama motorunda verilen keyword ile arama yapar
    ve organik sonuçları standart bir liste olarak
    döndürür.
    """

    if search_engine not in SUPPORTED_SEARCH_ENGINES:
        raise ValueError(
            f"Unsupported search engine: {search_engine}"
        )

    encoded_keyword = quote_plus(keyword)

    search_urls = {
        "google": (
            "https://www.google.com/search"
            f"?q={encoded_keyword}"
        ),
        "bing": (
            "https://www.bing.com/search"
            f"?q={encoded_keyword}"
        ),
    }
    result_selectors = {
        "google": "h3",
        "bing": "li.b_algo h2 a",
    }
    search_url = search_urls[search_engine]
    result_selector = result_selectors[search_engine]

    print(
        f"Searching {search_engine}: {keyword}",
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
                    result_selector,
                )
            )
        )

    except TimeoutException as error:
        raise RuntimeError(
            f"{search_engine.title()} sonuç başlıkları bulunamadı. "
            "Consent veya CAPTCHA sayfası açılmış olabilir. "
            f"Current URL: {browser.current_url}"
        ) from error

    result_elements = (
        browser.find_elements(
            By.CSS_SELECTOR,
            result_selector,
        )
    )

    collected_results = []
    seen_urls = set()

    for result_element in result_elements:
        title = result_element.text.strip()

        if not title:
            continue

        if search_engine == "google":
            link_elements = result_element.find_elements(
                By.XPATH,
                "./ancestor::a[1]",
            )

            if not link_elements:
                continue

            link_element = link_elements[0]
        else:
            link_element = result_element

        raw_url = link_element.get_attribute("href")

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

        # Arama motorunun kendi navigasyon bağlantılarını
        # organik sonuç olarak kaydetme.
        if domain.endswith(
            ("google.com", "bing.com")
        ):
            continue

        # Aynı URL birden fazla kez bulunursa
        # yalnızca ilkini kaydet.
        if result_url in seen_urls:
            continue

        snippet = (
            extract_snippet(result_element)
            if search_engine == "google"
            else extract_bing_snippet(link_element)
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
