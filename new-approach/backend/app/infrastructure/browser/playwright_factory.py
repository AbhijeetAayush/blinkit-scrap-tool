from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.config import Settings, get_settings
from app.infrastructure.browser.proxy import resolve_proxy


class PlaywrightBrowserSession:
    def __init__(self, context: BrowserContext, timeout_ms: int) -> None:
        self._context = context
        self._timeout_ms = timeout_ms
        self._page: Page | None = None

    async def _ensure_page(self) -> Page:
        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
            self._page.set_default_timeout(self._timeout_ms)
        return self._page

    async def fetch_html(
        self,
        url: str,
        *,
        wait_selector: str | None = None,
        cookies: list[dict] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> str:
        if cookies:
            await self._context.add_cookies(cookies)
        if extra_headers:
            await self._context.set_extra_http_headers(extra_headers)
        page = await self._ensure_page()
        await page.goto(url, wait_until="domcontentloaded")
        if wait_selector:
            await page.wait_for_selector(wait_selector, timeout=self._timeout_ms)
        return await page.content()


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
        yield PlaywrightBrowserSession(context, cfg.playwright_nav_timeout_ms)
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        await pw.stop()
