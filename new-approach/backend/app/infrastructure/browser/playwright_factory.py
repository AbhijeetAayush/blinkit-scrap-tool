from __future__ import annotations

from typing import Any, AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Page, Response, async_playwright

from app.config import Settings, get_settings
from app.infrastructure.browser.proxy import resolve_proxy

_JSON_URL_HINTS = (
    "search",
    "listing",
    "layout",
    "catalog",
    "product",
    "snippet",
    "feed",
    "grocery",
)


class PlaywrightBrowserSession:
    def __init__(self, context: BrowserContext, timeout_ms: int, settings: Settings) -> None:
        self._context = context
        self._timeout_ms = timeout_ms
        self._settings = settings
        self._page: Page | None = None
        self._json_payloads: list[Any] = []

    async def _ensure_page(self) -> Page:
        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
            self._page.set_default_timeout(self._timeout_ms)
            self._page.on("response", self._on_response)
        return self._page

    async def _on_response(self, response: Response) -> None:
        try:
            req = response.request
            if req.resource_type not in {"xhr", "fetch"}:
                return
            url = response.url.lower()
            if not any(h in url for h in _JSON_URL_HINTS):
                return
            ctype = (response.headers.get("content-type") or "").lower()
            if "json" not in ctype and "javascript" not in ctype:
                return
            if response.status >= 400:
                return
            data = await response.json()
            if data is not None:
                self._json_payloads.append(data)
        except Exception:
            return

    async def _card_count(self, page: Page) -> int:
        return await page.locator('div[role="button"][id]').count()

    async def _scroll_once(self, page: Page) -> None:
        await page.evaluate(
            """() => {
              const cards = document.querySelectorAll('div[role="button"][id]');
              let node = cards.length ? cards[cards.length - 1] : null;
              while (node) {
                const style = window.getComputedStyle(node);
                const oy = style.overflowY;
                if ((oy === 'auto' || oy === 'scroll' || oy === 'overlay')
                    && node.scrollHeight > node.clientHeight + 40) {
                  node.scrollTop = Math.min(node.scrollTop + node.clientHeight * 0.95, node.scrollHeight);
                  return 'container';
                }
                node = node.parentElement;
              }
              window.scrollBy(0, Math.floor(window.innerHeight * 0.9));
              return 'window';
            }"""
        )

    async def _lazy_scroll(
        self,
        page: Page,
        *,
        max_scrolls: int,
        scroll_pause_ms: int,
        max_cards: int,
        stable_rounds: int,
    ) -> None:
        stable = 0
        last = await self._card_count(page)
        for _ in range(max_scrolls):
            if last >= max_cards:
                break
            await self._scroll_once(page)
            await page.wait_for_timeout(scroll_pause_ms)
            count = await self._card_count(page)
            if count <= last:
                stable += 1
                if stable >= stable_rounds:
                    break
            else:
                stable = 0
            last = count

    async def fetch_html(
        self,
        url: str,
        *,
        wait_selector: str | None = None,
        cookies: list[dict] | None = None,
        extra_headers: dict[str, str] | None = None,
        scroll: bool = False,
        max_scrolls: int | None = None,
        scroll_pause_ms: int | None = None,
        max_cards: int | None = None,
        stable_rounds: int | None = None,
        capture_json: bool = False,
    ) -> tuple[str, list[Any]]:
        self._json_payloads = []
        if cookies:
            await self._context.add_cookies(cookies)
        if extra_headers:
            await self._context.set_extra_http_headers(extra_headers)
        page = await self._ensure_page()
        await page.goto(url, wait_until="domcontentloaded")
        if wait_selector:
            await page.wait_for_selector(wait_selector, timeout=self._timeout_ms)
        if scroll:
            await self._lazy_scroll(
                page,
                max_scrolls=max_scrolls if max_scrolls is not None else self._settings.search_max_scrolls,
                scroll_pause_ms=(
                    scroll_pause_ms
                    if scroll_pause_ms is not None
                    else self._settings.search_scroll_pause_ms
                ),
                max_cards=max_cards if max_cards is not None else self._settings.search_max_cards,
                stable_rounds=(
                    stable_rounds
                    if stable_rounds is not None
                    else self._settings.search_stable_rounds
                ),
            )
        html = await page.content()
        payloads = list(self._json_payloads) if capture_json else []
        return html, payloads


@asynccontextmanager
async def launch_session(
    *,
    session_id: str | None = None,
    settings: Settings | None = None,
) -> AsyncIterator[PlaywrightBrowserSession]:
    cfg = settings or get_settings()
    proxy = resolve_proxy(cfg, session_id=session_id)
    pw = await async_playwright().start()
    browser: Browser | None = None
    context: BrowserContext | None = None
    try:
        launch_kwargs: dict[str, Any] = {"headless": cfg.playwright_headless}
        if proxy:
            launch_kwargs["proxy"] = proxy.as_playwright()
        browser = await pw.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        block = set(cfg.block_types)

        async def _route(route, request):  # type: ignore[no-untyped-def]
            if request.resource_type in block:
                await route.abort()
            else:
                await route.continue_()

        if block:
            await context.route("**/*", _route)
        yield PlaywrightBrowserSession(context, cfg.playwright_nav_timeout_ms, cfg)
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        await pw.stop()
