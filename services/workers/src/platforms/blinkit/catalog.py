from urllib.parse import quote

from src.domain.errors import ParseEmptyError, UnserviceableError
from src.domain.models import ParsedListing, StoreRef
from src.domain.ports import Unlocker
from src.platforms.blinkit import constants
from src.platforms.blinkit.parser import is_unserviceable, merchant_id_from_html, parse_search_html


def _location_headers(lat: float | None, lon: float | None) -> dict[str, str]:
    if lat is None or lon is None:
        return {}
    return {"lat": str(lat), "lon": str(lon), "app_client": "consumer_web"}


def _location_cookies(lat: float | None, lon: float | None, extra: str | None) -> str | None:
    parts: list[str] = []
    if lat is not None and lon is not None:
        parts.append(f"gr_1_lat={lat}; gr_1_lon={lon}; lat={lat}; lon={lon}")
    if extra:
        parts.append(extra)
    return "; ".join(parts) or None


class BlinkitCatalog:
    platform_id = "blinkit"

    def resolve_store(self, lat: float, lon: float, unlocker: Unlocker) -> StoreRef:
        url = f"{constants.HOME_URL}?lat={lat}&lon={lon}"
        result = unlocker.fetch(
            url,
            render=True,
            country="in",
            cookies=_location_cookies(lat, lon, None),
            extra_headers=_location_headers(lat, lon),
        )
        if is_unserviceable(result.html):
            raise UnserviceableError("blinkit unserviceable at given coordinates")
        merchant = merchant_id_from_html(result.html) or f"geo:{lat:.4f},{lon:.4f}"
        return StoreRef(
            platform=self.platform_id,
            merchant_id=merchant,
            serviceable=True,
            lat=lat,
            lon=lon,
        )

    def search(
        self,
        unlocker: Unlocker,
        cookies: str | None,
        query: str,
        lat: float | None = None,
        lon: float | None = None,
    ) -> list[ParsedListing]:
        url = constants.SEARCH_URL.format(query=quote(query))
        result = unlocker.fetch(
            url,
            render=True,
            country="in",
            wait_for=constants.WAIT_FOR_CARDS,
            cookies=_location_cookies(lat, lon, cookies),
            extra_headers=_location_headers(lat, lon),
        )
        try:
            return parse_search_html(result.html, query=query)
        except ParseEmptyError as exc:
            raise ParseEmptyError(str(exc), html=result.html) from exc
