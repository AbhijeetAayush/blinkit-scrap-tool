from __future__ import annotations

from typing import Any, Protocol

from app.domain.models import Listing, ScrapeJob


class BrowserSession(Protocol):
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
    ) -> tuple[str, list[Any]]: ...


class PlatformCatalog(Protocol):
    platform_id: str

    async def search(
        self,
        query: str,
        *,
        lat: float,
        lon: float,
        session: BrowserSession,
    ) -> list[Listing]: ...


class JobQueue(Protocol):
    async def enqueue_scrape(self, job: ScrapeJob) -> None: ...
