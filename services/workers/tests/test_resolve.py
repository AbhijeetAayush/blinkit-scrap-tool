from uuid import uuid4

from src.app.dispatch_service import ResolveStoresService
from src.domain.models import CoveragePin, StoreRef


def test_resolve_empty_ids_loads_unmapped_pins():
    pin = CoveragePin(
        id=uuid4(),
        brand_id=uuid4(),
        pincode="000010",
        lat=12.9,
        lon=77.6,
    )

    class Coverage:
        def list_active_pins(self, *, offset, limit):
            return [pin] if offset == 0 else []

        def get_pins_by_ids(self, ids):
            raise AssertionError("empty cron must not query by id")

    class StoreMap:
        def missing_pins(self, pins):
            return pins

        def upsert(self, _pin, _store):
            self.upserted = True

        def get(self, *_a, **_k):
            return None

    class Catalog:
        platform_id = "blinkit"

        def resolve_store(self, lat, lon, unlocker):
            return StoreRef(platform="blinkit", merchant_id="m-1", serviceable=True, lat=lat, lon=lon)

    class Platforms:
        def get(self, _platform):
            return Catalog()

    class Lock:
        def cache_store(self, *_a, **_k):
            return None

    maps = StoreMap()
    svc = ResolveStoresService(Coverage(), maps, Platforms(), Lock(), object())
    result = svc.run([])
    assert result["resolved"] == 1
    assert maps.upserted is True
