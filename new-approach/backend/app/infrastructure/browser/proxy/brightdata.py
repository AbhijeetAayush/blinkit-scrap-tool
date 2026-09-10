from __future__ import annotations

from app.config import Settings
from app.infrastructure.browser.proxy.base import ProxyConfig


def build_config(settings: Settings, *, session_id: str | None = None) -> ProxyConfig:
    if not settings.brightdata_customer or not settings.brightdata_zone or not settings.brightdata_password:
        raise ValueError(
            "BRIGHTDATA_CUSTOMER, BRIGHTDATA_ZONE, and BRIGHTDATA_PASSWORD are required "
            "when PROXY_PROVIDER=brightdata"
        )
    country = (settings.brightdata_country or "in").lower()
    user = (
        f"brd-customer-{settings.brightdata_customer}"
        f"-zone-{settings.brightdata_zone}"
        f"-country-{country}"
    )
    if session_id:
        safe = "".join(ch for ch in session_id if ch.isalnum())[:24] or "job"
        user = f"{user}-session-{safe}"
    endpoint = settings.brightdata_endpoint.strip()
    return ProxyConfig(server=endpoint, username=user, password=settings.brightdata_password)
