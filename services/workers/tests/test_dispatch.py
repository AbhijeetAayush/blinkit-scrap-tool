from uuid import UUID, uuid4

from src.app.dispatch_service import DispatchService
from src.app.settings import Settings
from src.domain.models import CoveragePin, DispatchPayload, Keyword


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
    def __init__(self, pins: list[CoveragePin], keywords: list[Keyword] | None = None) -> None:
        self.pins = pins
        self.keywords = keywords or []

    def list_active_pins(self, *, offset: int, limit: int) -> list[CoveragePin]:
        return self.pins[offset : offset + limit]

    def get_pins_by_ids(self, pincode_ids: list[UUID]) -> list[CoveragePin]:
        wanted = {str(i) for i in pincode_ids}
        return [p for p in self.pins if str(p.id) in wanted]

    def list_keywords_by_ids(self, keyword_ids: list[UUID]) -> list[Keyword]:
        wanted = {str(i) for i in keyword_ids}
        return [k for k in self.keywords if str(k.id) in wanted]


class FakeStoreMap:
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

    def publish_dispatch_continuation(self, offset, run_id, observed_slot, slot_kind, self_url, **extra) -> None:
        self.continuations.append(
            {
                "offset": offset,
                "run_id": run_id,
                "observed_slot": observed_slot,
                "slot_kind": slot_kind,
                "self_url": self_url,
                **extra,
            }
        )


class FakeLock:
    def is_halted(self, _run_id: str) -> bool:
        return False

    def acquire(self, _key: str, _ttl_s: int) -> bool:
        return True

    def release(self, _key: str) -> None:
        return None


class FakeCredits:
    def __init__(self, remaining: float = 10_000.0) -> None:
        self._remaining = remaining

    def remaining(self) -> float:
        return self._remaining

    def add(self, _n: float) -> None:
        return None


class FakePlatforms:
    def get(self, platform: str):
        raise AssertionError(f"resolve should not run: {platform}")


def _svc(pins, keywords, **kwargs):
    publisher = FakePublisher()
    svc = DispatchService(
        _settings(**kwargs.pop("settings_overrides", {})),
        FakeCoverage(pins, keywords),
        FakeStoreMap(),
        FakeRuns(),
        FakeAlerts(),
        publisher,
        FakeLock(),
        kwargs.pop("credits", FakeCredits()),
        FakePlatforms(),
    )
    return svc, publisher


def test_dispatch_selected_locations_and_keywords_only():
    brand_id = uuid4()
    pins = [_pin(i, brand_id) for i in range(2)]
    kw = Keyword(id=uuid4(), brand_id=brand_id, query="mini mogra rice")
    svc, publisher = _svc(pins, [kw])
    result = svc.run(
        DispatchPayload(
            slot_kind="manual",
            brand_id=brand_id,
            keyword_ids=[kw.id],
            pincode_ids=[pins[0].id],
        )
    )
    assert result["status"] == "ok"
    assert result["published"] == 1
    assert result["pins"] == 1
    job = publisher.scrapes[0][0]
    assert job.queries == ["mini mogra rice"]
    assert job.pincode == pins[0].pincode
    assert job.brand_id == brand_id
    assert job.merchant_id.startswith("geo:")
    assert publisher.continuations == []


def test_dispatch_rejects_empty_selection():
    svc, publisher = _svc([], [])
    result = svc.run(DispatchPayload(slot_kind="manual"))
    assert result["status"] == "error"
    assert publisher.scrapes == []


def test_dispatch_budget_rejects_large_selection():
    brand_id = uuid4()
    pins = [_pin(0, brand_id)]
    kw = Keyword(id=uuid4(), brand_id=brand_id, query="rice")
    svc, publisher = _svc(pins, [kw], credits=FakeCredits(remaining=1))
    result = svc.run(
        DispatchPayload(
            slot_kind="manual",
            brand_id=brand_id,
            keyword_ids=[kw.id],
            pincode_ids=[pins[0].id],
        )
    )
    assert result["status"] == "budget"
    assert publisher.scrapes == []


def test_dispatch_chunks_keywords_and_continues_locations():
    brand_id = uuid4()
    pins = [_pin(i, brand_id) for i in range(3)]
    kws = [Keyword(id=uuid4(), brand_id=brand_id, query=f"q{i}") for i in range(7)]
    svc, publisher = _svc(pins, kws, settings_overrides={"max_stores_per_dispatch": 2})
    first = svc.run(
        DispatchPayload(
            slot_kind="manual",
            brand_id=brand_id,
            keyword_ids=[k.id for k in kws],
            pincode_ids=[p.id for p in pins],
        )
    )
    assert first["locations"] == 2
    assert first["published"] == 4
    assert len(publisher.continuations) == 1
    assert publisher.continuations[0]["offset"] == 2
    assert publisher.continuations[0]["keyword_ids"] == [k.id for k in kws]
