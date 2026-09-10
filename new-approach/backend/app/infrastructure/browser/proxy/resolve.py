from __future__ import annotations

from app.config import Settings
from app.infrastructure.browser.proxy import brightdata, oxylabs
from app.infrastructure.browser.proxy.base import ProxyConfig


def resolve_proxy(settings: Settings, *, session_id: str | None = None) -> ProxyConfig | None:
    if settings.proxy_server and settings.proxy_username and settings.proxy_password:
        return ProxyConfig(
            server=settings.proxy_server,
            username=settings.proxy_username,
            password=settings.proxy_password,
        )

    provider = (settings.proxy_provider or "none").strip().lower()
    if provider in {"", "none", "off", "direct"}:
        return None
    if provider == "oxylabs":
        return oxylabs.build_config(settings, session_id=session_id)
    if provider in {"brightdata", "bright_data", "bright"}:
        return brightdata.build_config(settings, session_id=session_id)
    raise ValueError(f"Unknown PROXY_PROVIDER={settings.proxy_provider!r}; use none|oxylabs|brightdata")
