from __future__ import annotations

from src.app.settings import Settings
from src.domain.models import FetchResult
from src.unlocker.base import BaseUnlocker
from src.unlocker.http import unlocker_get


class ScrapingBeeUnlocker(BaseUnlocker):
    vendor = "scrapingbee"

    def __init__(self, settings: Settings) -> None:
        self._key = settings.scrapingbee_api_key

    def fetch(
        self,
        url: str,
        *,
        render: bool = False,
        country: str = "in",
        wait_for: str | None = None,
        cookies: str | None = None,
        js_scenario: dict | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> FetchResult:
        # Proven combo (ScrapingBee 200 + 24 Blinkit cards):
        # networkidle0 + wait=8000 + forward_headers Cookie. Plain wait / wait_for CSS → 500.
        # Ignore wait_for — Blinkit's selector breaks ScrapingBee.
        params: dict[str, str] = {
            "api_key": self._key,
            "url": url,
            "render_js": "true" if render else "false",
            "country_code": country,
        }
        if render:
            # networkidle is required for Blinkit search cards; home/location is lighter.
            if "/s/" in url or "search" in url.lower():
                params["wait_browser"] = "networkidle0"
                params["wait"] = "8000"
            else:
                params["wait"] = "5000"
        headers = dict(extra_headers or {})
        if cookies:
            headers["Cookie"] = cookies
        if headers:
            params["forward_headers"] = "true"
        response = unlocker_get(
            self.vendor,
            "https://app.scrapingbee.com/api/v1/",
            params=params,
            headers=headers,
        )
        credits = None
        raw = response.headers.get("spb-cost") or response.headers.get("x-scrapingbee-cost")
        if raw:
            try:
                credits = float(raw)
            except ValueError:
                credits = None
        return FetchResult(
            html=response.text,
            cookies=response.headers.get("set-cookie") or cookies,
            status_code=response.status_code,
            vendor=self.vendor,
            credits_hint=credits,
        )
