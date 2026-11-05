import asyncio
from contextlib import suppress
from time import monotonic

from capture.web_capture import WEB_VIEWPORT, validate_web_url


CSS_SELECTOR = r"""element => {
    if (window !== window.top || element.getRootNode() !== document)
        return null;
    const parts = [];
    for (let node = element; node; node = node.parentElement) {
        if (node.id) {
            const id = "#" + CSS.escape(node.id);
            if (document.querySelectorAll(id).length === 1) {
                parts.unshift(id);
                break;
            }
        }
        const tag = CSS.escape(node.localName);
        const siblings = node.parentElement
            ? Array.from(node.parentElement.children).filter(child => child.localName === node.localName)
            : [node];
        const index = siblings.indexOf(node) + 1;
        parts.unshift(siblings.length > 1 ? tag + ":nth-of-type(" + index + ")" : tag);
    }
    const selector = parts.join(" > ");
    const matches = document.querySelectorAll(selector);
    return matches.length === 1 && matches[0] === element ? selector : null;
}"""


async def pick_web_element(url, cancelled):
    validate_web_url(url)
    from playwright.async_api import Error, async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            channel="msedge", headless=False, timeout=30_000
        )
        try:
            if cancelled.is_set():
                return None
            page = await browser.new_page(viewport=WEB_VIEWPORT, accept_downloads=False)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            if response is not None and not response.ok:
                raise RuntimeError(f"網站回傳 HTTP {response.status}，請確認網址與存取權限。")

            pick = asyncio.create_task(page.pick_locator())
            try:
                deadline = monotonic() + 180
                while not pick.done():
                    if cancelled.is_set() or page.is_closed():
                        return None
                    if monotonic() >= deadline:
                        raise TimeoutError("選取時間已到，請重新開啟網頁選取。")
                    await asyncio.wait([pick], timeout=0.2)
                locator = pick.result()
                selector = await locator.evaluate(CSS_SELECTOR, timeout=5_000)
                if not selector:
                    raise ValueError("請選取主網頁中可唯一辨識的元素。")
                return selector
            except Error:
                if cancelled.is_set() or page.is_closed() or not browser.is_connected():
                    return None
                raise
            finally:
                if not pick.done():
                    pick.cancel()
                with suppress(asyncio.CancelledError, Error):
                    await pick
        finally:
            await browser.close()
