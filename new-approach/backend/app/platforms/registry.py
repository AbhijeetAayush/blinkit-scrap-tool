from __future__ import annotations

from app.domain.errors import UnknownPlatformError
from app.domain.ports import PlatformCatalog
from app.platforms.blinkit.catalog import BlinkitCatalog

_REGISTRY: dict[str, PlatformCatalog] = {
    "blinkit": BlinkitCatalog(),
}


def known_ids() -> list[str]:
    return sorted(_REGISTRY.keys())


def get(platform_id: str) -> PlatformCatalog:
    key = (platform_id or "").strip().lower()
    try:
        return _REGISTRY[key]
    except KeyError as exc:
        raise UnknownPlatformError(f"unknown platform: {platform_id}") from exc
