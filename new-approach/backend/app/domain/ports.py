from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.models import Listing, ScrapeJob


class BrowserSession(Protocol):
    async def fetch_html(
        self,
        url: str,
        *,
        wait_selector: str | None = None,
        cookies: list[dict] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> str: ...


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
