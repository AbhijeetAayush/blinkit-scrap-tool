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
        by_id = {p.id: p for p in self.pins}
        return [by_id[i] for i in pincode_ids if i in by_id]

    def list_keywords_by_ids(self, keyword_ids: list[UUID]) -> list[Keyword]:
        wanted = {str(i) for i in keyword_ids}
        return [k for k in self.keywords if str(k.id) in wanted]


class FakeStoreMap:
    def missing_pins(self, pins: list[CoveragePin]) -> list[CoveragePin]:
        return []


class FakeRuns:
    def __init__(self) -> None:
        self.finished: list[dict] = []

    def create(self, **_kwargs) -> UUID:
        return UUID("11111111-1111-1111-1111-111111111111")

    def finish(self, run_id, **kwargs) -> None:
        self.finished.append({"run_id": run_id, **kwargs})


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
    def __init__(self) -> None:
        self.jobs_left: dict[str, int] = {}

    def is_halted(self, _run_id: str) -> bool:
        return False

    def acquire(self, _key: str, _ttl_s: int) -> bool:
        return True

    def release(self, _key: str) -> None:
        return None

    def set_jobs_left(self, run_id: str, n: int) -> None:
        self.jobs_left[run_id] = n

    def decr_jobs_left(self, run_id: str) -> int | None:
        if run_id not in self.jobs_left:
            return None
        self.jobs_left[run_id] -= 1
        return self.jobs_left[run_id]


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
    lock = kwargs.pop("lock", FakeLock())
    runs = kwargs.pop("runs", FakeRuns())
    svc = DispatchService(
        _settings(**kwargs.pop("settings_overrides", {})),
        FakeCoverage(pins, keywords),
        FakeStoreMap(),
        runs,
        FakeAlerts(),
        publisher,
        lock,
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
    kws = [Keyword(id=uuid4(), brand_id=brand_id, query=f"query {i}") for i in range(7)]
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


def test_dispatch_does_not_mark_dispatched():
    brand_id = uuid4()
    pins = [_pin(0, brand_id)]
    kw = Keyword(id=uuid4(), brand_id=brand_id, query="rice")
    runs = FakeRuns()
    svc, publisher = _svc(pins, [kw], runs=runs)
    result = svc.run(
        DispatchPayload(
            slot_kind="manual",
            brand_id=brand_id,
            keyword_ids=[kw.id],
            pincode_ids=[pins[0].id],
        )
    )
    assert result["status"] == "ok"
    assert publisher.scrapes
    assert runs.finished == []


def test_dispatch_sets_jobs_left_on_first_page():
    brand_id = uuid4()
    pins = [_pin(i, brand_id) for i in range(3)]
    kw = Keyword(id=uuid4(), brand_id=brand_id, query="rice")
    lock = FakeLock()
    svc, _publisher = _svc(pins, [kw], lock=lock)
    svc.run(
        DispatchPayload(
            slot_kind="manual",
            brand_id=brand_id,
            keyword_ids=[kw.id],
            pincode_ids=[p.id for p in pins],
        )
    )
    assert lock.jobs_left["11111111-1111-1111-1111-111111111111"] == 3


def test_continuation_budget_uses_remaining_locations_only():
    brand_id = uuid4()
    pins = [_pin(i, brand_id) for i in range(3)]
    kw = Keyword(id=uuid4(), brand_id=brand_id, query="rice")
    runs = FakeRuns()
    svc, publisher = _svc(
        pins,
        [kw],
        credits=FakeCredits(remaining=6),
        settings_overrides={"max_stores_per_dispatch": 2},
        runs=runs,
    )
    result = svc.run(
        DispatchPayload(
            slot_kind="manual",
            brand_id=brand_id,
            keyword_ids=[kw.id],
            pincode_ids=[p.id for p in pins],
            continuation_offset=2,
            run_id=UUID("11111111-1111-1111-1111-111111111111"),
        )
    )
    assert result["status"] == "ok"
    assert result["published"] == 1
    assert runs.finished == []
    assert publisher.scrapes


def test_first_page_budget_uses_this_invocation_only():
    brand_id = uuid4()
    pins = [_pin(i, brand_id) for i in range(3)]
    kw = Keyword(id=uuid4(), brand_id=brand_id, query="rice")
    svc, publisher = _svc(
        pins,
        [kw],
        credits=FakeCredits(remaining=12),
        settings_overrides={"max_stores_per_dispatch": 2},
    )
    result = svc.run(
        DispatchPayload(
            slot_kind="manual",
            brand_id=brand_id,
            keyword_ids=[kw.id],
            pincode_ids=[p.id for p in pins],
        )
    )
    assert result["status"] == "ok"
    assert result["published"] == 2


def test_order_pins_by_ids_preserves_request_order():
    from src.adapters.supabase_repo import order_pins_by_ids

    brand_id = uuid4()
    pins = [_pin(i, brand_id) for i in range(3)]
    ordered = order_pins_by_ids(pins, [pins[2].id, pins[0].id, pins[1].id])
    assert [p.id for p in ordered] == [pins[2].id, pins[0].id, pins[1].id]


def test_dispatch_normalizes_keyword_case():
    brand_id = uuid4()
    pins = [_pin(0, brand_id)]
    kws = [
        Keyword(id=uuid4(), brand_id=brand_id, query="Rice"),
        Keyword(id=uuid4(), brand_id=brand_id, query="rice"),
    ]
    svc, publisher = _svc(pins, kws)
    svc.run(
        DispatchPayload(
            slot_kind="manual",
            brand_id=brand_id,
            keyword_ids=[k.id for k in kws],
            pincode_ids=[pins[0].id],
        )
    )
    assert publisher.scrapes[0][0].queries == ["rice"]
