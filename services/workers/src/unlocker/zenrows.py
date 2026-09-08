from __future__ import annotations

from src.app.settings import Settings
from src.domain.models import FetchResult
from src.unlocker.base import BaseUnlocker
from src.unlocker.http import RENDER_WAIT_MS, unlocker_get


class ZenRowsUnlocker(BaseUnlocker):
    vendor = "zenrows"

    def __init__(self, settings: Settings) -> None:
        self._key = settings.zenrows_api_key

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
        params: dict[str, str] = {
            "apikey": self._key,
            "url": url,
            "js_render": "true" if render else "false",
        }
        if render:
            params["wait"] = RENDER_WAIT_MS
            if wait_for:
                params["wait_for"] = wait_for
        if country:
            params["premium_proxy"] = "true"
            params["proxy_country"] = country
        headers = dict(extra_headers or {})
        if cookies:
            headers["Cookie"] = cookies
        if headers:
            params["custom_headers"] = "true"
        response = unlocker_get(self.vendor, "https://api.zenrows.com/v1/", params=params, headers=headers)
        credits = None
        raw = response.headers.get("x-request-cost") or response.headers.get("zenrows-request-cost")
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
