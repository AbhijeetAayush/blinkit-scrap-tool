from __future__ import annotations

from app.config import Settings
from app.infrastructure.browser.proxy.base import ProxyConfig


def build_config(settings: Settings, *, session_id: str | None = None) -> ProxyConfig:
    if not settings.oxylabs_username or not settings.oxylabs_password:
        raise ValueError("OXYLABS_USERNAME and OXYLABS_PASSWORD are required when PROXY_PROVIDER=oxylabs")
    user = settings.oxylabs_username
    country = (settings.oxylabs_country or "IN").upper()
    if "-cc-" not in user:
        user = f"customer-{user}-cc-{country}"
    elif f"-cc-{country}" not in user and "-cc-" not in user:
        user = f"{user}-cc-{country}"
    if session_id:
        safe = "".join(ch for ch in session_id if ch.isalnum())[:24] or "job"
        if "-sessid-" not in user:
            user = f"{user}-sessid-{safe}"
    endpoint = settings.oxylabs_endpoint.strip()
    return ProxyConfig(server=endpoint, username=user, password=settings.oxylabs_password)
