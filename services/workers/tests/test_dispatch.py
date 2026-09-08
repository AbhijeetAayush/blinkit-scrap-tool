from uuid import UUID, uuid4

from src.app.dispatch_service import DispatchService
from src.app.settings import Settings
from src.domain.models import CoveragePin, DispatchPayload, StoreRef


def _settings(**overrides) -> Settings:
    values = dict(
        supabase_url="",
        supabase_service_role_key="",
        zenrows_api_key="",
        scrapingbee_api_key="",
        upstash_redis_url="",
        upstash_redis_token="",
        qstash_token="",
        qstash_url="https://qstash.upstash.io",
        qstash_current_signing_key="",
        qstash_next_signing_key="",
        unlocker_search="zenrows",
        unlocker_location="scrapingbee",
        unlocker_failover=True,
        daily_credit_budget=400,
        fail_fast=True,
        scrape_spread_seconds=3,
        default_velocity=5.0,
        max_stores_per_dispatch=500,
        match_auto_commit=0.95,
        share_of_search_n=20,
        pin_page_size=2,
        s3_bucket="",
        scrape_function_url="https://scrape.example/",
        derive_function_url="https://derive.example/",
        resolve_function_url="https://resolve.example/",
        dispatch_function_url="https://dispatch.example/",
        scrape_function_name="",
        derive_function_name="",
        resolve_function_name="",
        dispatch_function_name="",
        manual_run_secret="",
    )
    values.update(overrides)
    return Settings(**values)


def _pin(i: int, brand_id) -> CoveragePin:
    return CoveragePin(
        id=uuid4(),
        brand_id=brand_id,
        pincode=f"{i:06d}",
        lat=12.9 + i * 0.01,
        lon=77.6 + i * 0.01,
        platform="blinkit",
    )


class FakeCoverage:
    def __init__(self, pins: list[CoveragePin]) -> None:
        self.pins = pins

    def list_active_pins(self, *, offset: int, limit: int) -> list[CoveragePin]:
        return self.pins[offset : offset + limit]


class FakeStoreMap:
    def get(self, platform: str, pincode: str) -> StoreRef:
        return StoreRef(platform=platform, merchant_id=f"m-{pincode}", serviceable=True)

    def missing_pins(self, pins: list[CoveragePin]) -> list[CoveragePin]:
        return []


class FakeRuns:
    def create(self, **_kwargs) -> UUID:
        return UUID("11111111-1111-1111-1111-111111111111")

    def finish(self, *_args, **_kwargs) -> None:
        return None


class FakeAlerts:
    def insert(self, *_args, **_kwargs) -> None:
        return None


class FakePublisher:
    def __init__(self) -> None:
        self.scrapes: list = []
        self.continuations: list = []
        self.resolves: list = []

    def publish_scrape(self, job, delay_s: int) -> None:
        self.scrapes.append((job, delay_s))

    def publish_derive(self, job) -> None:
        return None

    def publish_resolve(self, payload: dict) -> None:
        self.resolves.append(payload)

    def publish_dispatch_continuation(self, offset, run_id, observed_slot, slot_kind, self_url) -> None:
        self.continuations.append(
            {
                "offset": offset,
                "run_id": run_id,
                "observed_slot": observed_slot,
                "slot_kind": slot_kind,
                "self_url": self_url,
            }
        )


class FakeLock:
    def is_halted(self, _run_id: str) -> bool:
        return False

    def acquire(self, _key: str, _ttl_s: int) -> bool:
        return True


class FakeCredits:
    def remaining(self) -> float:
        return 100.0

    def add(self, _n: float) -> None:
        return None


class FakePlatforms:
    def get(self, platform: str):
        raise AssertionError(f"resolve should not run for mapped pins: {platform}")


def test_dispatch_paginates_two_pages_no_three_pin_cap():
    brand_id = uuid4()
    pins = [_pin(i, brand_id) for i in range(4)]
    coverage = FakeCoverage(pins)
    publisher = FakePublisher()
    svc = DispatchService(
        _settings(),
        coverage,
        FakeStoreMap(),
        FakeRuns(),
        FakeAlerts(),
        publisher,
        FakeLock(),
        FakeCredits(),
        FakePlatforms(),
    )

    first = svc.run(DispatchPayload(continuation_offset=0, slot_kind="morning"))
    assert first["pins"] == 2
    assert first["published"] == 2
    assert len(publisher.continuations) == 1
    assert publisher.continuations[0]["offset"] == 2

    second = svc.run(
        DispatchPayload(
            continuation_offset=2,
            run_id=publisher.continuations[0]["run_id"],
            observed_slot=publisher.continuations[0]["observed_slot"],
            slot_kind="morning",
        )
    )
    assert second["pins"] == 2
    assert second["published"] == 2
    assert len(publisher.scrapes) == 4
    merchants = {job.merchant_id for job, _delay in publisher.scrapes}
    assert merchants == {"m-000000", "m-000001", "m-000002", "m-000003"}


class _StoreMapThenMapped:
    def __init__(self) -> None:
        self._stores: dict[tuple[str, str], StoreRef] = {}

    def get(self, platform: str, pincode: str) -> StoreRef | None:
        return self._stores.get((platform, pincode))

    def missing_pins(self, pins: list[CoveragePin]) -> list[CoveragePin]:
        return [p for p in pins if self.get(p.platform, p.pincode) is None]


class _InlineResolve:
    def __init__(self, store_map: _StoreMapThenMapped) -> None:
        self.store_map = store_map
        self.ids: list[str] = []

    def run(self, pincode_ids: list[str]) -> dict:
        self.ids = list(pincode_ids)
        self.store_map._stores[("blinkit", "000000")] = StoreRef(
            platform="blinkit", merchant_id="m-inline", serviceable=True
        )
        return {"resolved": len(pincode_ids)}


def test_dispatch_resolves_missing_pins_inline_then_scrapes():
    brand_id = uuid4()
    pin = _pin(0, brand_id)
    store_map = _StoreMapThenMapped()
    resolve = _InlineResolve(store_map)
    publisher = FakePublisher()
    svc = DispatchService(
        _settings(pin_page_size=10),
        FakeCoverage([pin]),
        store_map,
        FakeRuns(),
        FakeAlerts(),
        publisher,
        FakeLock(),
        FakeCredits(),
        FakePlatforms(),
        resolve,
    )
    result = svc.run(DispatchPayload(continuation_offset=0, slot_kind="manual"))
    assert resolve.ids == [str(pin.id)]
    assert publisher.resolves == []
    assert result["published"] == 1
    assert publisher.scrapes[0][0].merchant_id == "m-inline"
