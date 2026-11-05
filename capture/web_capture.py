from io import BytesIO
from urllib.parse import urlsplit

from PIL import Image

WEB_VIEWPORT = {"width": 1920, "height": 1080}


def validate_web_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("請輸入有效的 HTTP 或 HTTPS 網址。")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("請勿在網址中填入帳號或密碼。")


def validate_web_target(url, selector):
    validate_web_url(url)
    if not selector.strip():
        raise ValueError("請輸入圖表的 CSS 選擇器。")


def capture_web(target):
    url, selector = target["url"], target["selector"]
    validate_web_target(url, selector)
    try:
        from playwright.sync_api import Error, TimeoutError, sync_playwright
    except ImportError as exc:
        raise RuntimeError("缺少 Playwright，請用 Start.bat 更新套件。") from exc

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(channel="msedge", headless=True, timeout=30_000)
        except Error as exc:
            raise RuntimeError(f"無法開啟背景瀏覽器，請確認已安裝 Microsoft Edge。{exc}") from exc
        try:
            page = browser.new_page(viewport=WEB_VIEWPORT, accept_downloads=False)
            page.set_default_timeout(30_000)
            response = page.goto(url, wait_until="domcontentloaded")
            if response is not None and not response.ok:
                raise RuntimeError(f"網站回傳 HTTP {response.status}，請確認網址與存取權限。")
            chart = page.locator(f"css={selector}")
            chart.wait_for(state="visible")
            delay = target.get("delay_seconds", 1)
            if delay:
                page.wait_for_timeout(delay * 1000)
            screenshot = chart.screenshot(animations="disabled")
        except TimeoutError as exc:
            raise RuntimeError("載入網站或等待圖表逾時。請檢查網址、網路與 CSS 選擇器。") from exc
        except Error as exc:
            raise RuntimeError(f"無法擷取圖表，請確認選擇器只符合一個可見元素。{exc}") from exc
        finally:
            browser.close()

    with Image.open(BytesIO(screenshot)) as image:
        return image.convert("RGB")
