from selenium import webdriver
from selenium.webdriver.chrome.options import Options


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


def main() -> None:
    """
    Chrome tarayıcısını açar ve Google ana
    sayfasına erişerek Selenium bağlantısını test eder.
    """

    browser = create_browser()

    try:
        browser.get(
            "https://www.google.com"
        )

        print(
            f"Page title: {browser.title}"
        )

        print(
            f"Current URL: {browser.current_url}"
        )

        input(
            "Tarayıcıyı kapatmak için "
            "Enter tuşuna bas..."
        )

    finally:
        browser.quit()


if __name__ == "__main__":
    main()