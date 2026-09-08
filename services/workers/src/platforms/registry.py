from src.domain.errors import UnknownPlatformError
from src.domain.ports import PlatformCatalog
from src.platforms.blinkit.catalog import BlinkitCatalog


class DefaultPlatformRegistry:
    def __init__(self) -> None:
        self._map: dict[str, PlatformCatalog] = {
            "blinkit": BlinkitCatalog(),
        }

    def get(self, platform: str) -> PlatformCatalog:
        try:
            return self._map[platform]
        except KeyError as exc:
            raise UnknownPlatformError(platform) from exc
