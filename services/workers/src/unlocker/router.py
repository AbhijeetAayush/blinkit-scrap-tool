from __future__ import annotations

from src.app.settings import Settings
from src.domain.models import FetchResult
from src.unlocker.scrapingbee import ScrapingBeeUnlocker
from src.unlocker.zenrows import ZenRowsUnlocker


class _CookieMemoryUnlocker:
    """Reuse cookies within one store session; failover starts with a clean jar."""

    def __init__(self, inner, redis=None, store_id: str = "", vendor: str = "", cookies: str | None = None) -> None:
        self._inner = inner
        self.vendor = inner.vendor
        self._redis = redis
        self._store_id = store_id
        self._vendor = vendor or inner.vendor
        self._cookies = cookies
        self.last_credits_hint: float | None = None

    def fetch(self, url: str, **kwargs) -> FetchResult:
        cookies = kwargs.get("cookies") or self._cookies
        kwargs["cookies"] = cookies
        result = self._inner.fetch(url, **kwargs)
        self._cookies = result.cookies or cookies
        self.last_credits_hint = result.credits_hint
        if self._redis and self._cookies and self._store_id:
            self._redis.set_session("blinkit", self._store_id, self._vendor, self._cookies, 1200)
        return result


class StickyUnlockerRouter:
    def __init__(self, settings: Settings, redis=None) -> None:
        self._settings = settings
        self._redis = redis
        self._zenrows = ZenRowsUnlocker(settings)
        self._bee = ScrapingBeeUnlocker(settings)
        self._sticky: dict[str, str] = {}

    def _by_name(self, name: str):
        if name == "scrapingbee":
            return self._bee
        return self._zenrows

    def _other(self, name: str) -> str:
        return "zenrows" if name == "scrapingbee" else "scrapingbee"

    def _wrap(self, store_id: str, vendor: str) -> _CookieMemoryUnlocker:
        cached = None
        if self._redis:
            cached = self._redis.get_session("blinkit", store_id, vendor)
        return _CookieMemoryUnlocker(
            self._by_name(vendor),
            redis=self._redis,
            store_id=store_id,
            vendor=vendor,
            cookies=cached,
        )

    def session_for_store(self, store_id: str) -> tuple[object, str]:
        vendor = self._sticky.get(store_id) or self._settings.unlocker_search
        self._sticky[store_id] = vendor
        return self._wrap(store_id, vendor), vendor

    def failover_session(self, store_id: str) -> tuple[object, str]:
        current = self._sticky.get(store_id) or self._settings.unlocker_search
        nxt = self._other(current)
        self._sticky[store_id] = nxt
        return self._wrap(store_id, nxt), nxt

    def location_unlocker(self):
        return self._by_name(self._settings.unlocker_location)
