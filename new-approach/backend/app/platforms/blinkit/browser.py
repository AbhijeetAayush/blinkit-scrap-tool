from __future__ import annotations

from app.domain.ports import BrowserSession
from app.platforms.blinkit import constants
from app.platforms.blinkit.parser import search_url


async def fetch_search_html(
    session: BrowserSession,
    query: str,
    *,
    lat: float,
    lon: float,
) -> str:
    cookies = [
        {"name": "gr_1_lat", "value": str(lat), "domain": ".blinkit.com", "path": "/"},
        {"name": "gr_1_lon", "value": str(lon), "domain": ".blinkit.com", "path": "/"},
        {"name": "lat", "value": str(lat), "domain": ".blinkit.com", "path": "/"},
        {"name": "lon", "value": str(lon), "domain": ".blinkit.com", "path": "/"},
    ]
    headers = {
        "lat": str(lat),
        "lon": str(lon),
        "app_client": constants.APP_CLIENT,
    }
    return await session.fetch_html(
        search_url(query),
        wait_selector=constants.WAIT_FOR_CARDS,
        cookies=cookies,
        extra_headers=headers,
    )
