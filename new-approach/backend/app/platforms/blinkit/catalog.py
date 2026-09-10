from __future__ import annotations

from app.domain.models import Listing
from app.domain.ports import BrowserSession
from app.platforms.blinkit import browser as blinkit_browser
from app.platforms.blinkit.parser import parse_search_html


class BlinkitCatalog:
    platform_id = "blinkit"

    async def search(
        self,
        query: str,
        *,
        lat: float,
        lon: float,
        session: BrowserSession,
    ) -> list[Listing]:
        html, payloads = await blinkit_browser.fetch_search_page(
            session,
            query,
            lat=lat,
            lon=lon,
        )
        return parse_search_html(html, query=query, json_payloads=payloads)
