from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.app.scrape_store_service import ScrapeStoreService
from src.app.settings import Settings
from src.domain.models import ScrapeJob
from src.platforms.blinkit.parser import parse_search_html


def _settings() -> Settings:
    return Settings(
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
        unlocker_search="scrapingbee",
        unlocker_location="scrapingbee",
        unlocker_failover=False,
        daily_credit_budget=400,
        fail_fast=True,
        scrape_spread_seconds=3,
        default_velocity=5.0,
        max_stores_per_dispatch=500,
        match_auto_commit=0.95,
        share_of_search_n=20,
        pin_page_size=500,
        s3_bucket="",
        scrape_function_url="",
        derive_function_url="",
        resolve_function_url="",
        dispatch_function_url="",
        scrape_function_name="",
        derive_function_name="",
        resolve_function_name="",
        dispatch_function_name="",
        manual_run_secret="",
    )


class FakeObs:
    def __init__(self) -> None:
        self.rows = []

    def upsert_many(self, drafts) -> None:
        self.rows.extend(drafts)


class FakePublisher:
    def __init__(self) -> None:
        self.derive = []

    def publish_derive(self, job) -> None:
        self.derive.append(job)


class FakeLock:
    def __init__(self) -> None:
        self.jobs: dict[str, int] = {}

    def is_halted(self, _run_id: str) -> bool:
        return False

    def acquire(self, _key: str, _ttl_s: int) -> bool:
        return True

    def release(self, _key: str) -> None:
        return None

    def set_jobs_left(self, run_id: str, n: int) -> None:
        self.jobs[run_id] = n

    def decr_jobs_left(self, run_id: str) -> int | None:
        if run_id not in self.jobs:
            return None
        self.jobs[run_id] -= 1
        return self.jobs[run_id]


class FakeCredits:
    def add(self, _n: float) -> None:
        return None

    def remaining(self) -> float:
        return 1000


class FakeLake:
    def __init__(self) -> None:
        self.keys: list[str] = []

    def put_bronze(self, key: str, _body: bytes) -> None:
        self.keys.append(key)


class FakeCatalog:
    platform_id = "blinkit"
    last_html = "<html>cards</html>"

    def search(self, _unlocker, _cookies, query, lat=None, lon=None):
        html = (
            '<div role="button" id="527868">28% OFF8 minsKohinoor Mini Mogra 2 Rice10 kg₹502 ₹700ADD</div>'
            '<div role="button" id="100633">India Gate Mini Mogra Rice 10 kg ₹540 ₹720 ADD</div>'
            '<div role="button" id="999001">Daawat Rozana Mini 5 kg ₹389 ₹450 ADD</div>'
        )
        return parse_search_html(html, query=query)


class FakePlatforms:
    def get(self, _platform: str):
        return FakeCatalog()


class FakeRouter:
    def session_for_store(self, _store_id: str):
        return FakeCatalog(), "scrapingbee"


class FakeAlerts:
    def insert(self, *_args, **_kwargs) -> None:
        return None


def _job(brand_id, run_id=None):
    return ScrapeJob(
        brand_ids=[brand_id],
        brand_id=brand_id,
        merchant_id="geo:18.4478,73.8371",
        platform="blinkit",
        run_id=run_id or UUID("11111111-1111-1111-1111-111111111111"),
        correlation_id="c1",
        observed_slot=datetime.now(timezone.utc),
        queries=["mini mogra rice"],
        pincode="411046",
        lat=18.4478,
        lon=73.8371,
    )


def test_scrape_harvests_all_cards_one_pincode():
    brand_id = uuid4()
    obs = FakeObs()
    pub = FakePublisher()
    lake = FakeLake()
    svc = ScrapeStoreService(
        _settings(),
        None,
        None,
        obs,
        FakeAlerts(),
        pub,
        FakeLock(),
        FakeCredits(),
        lake,
        FakePlatforms(),
        FakeRouter(),
    )
    result = svc.run(_job(brand_id))
    assert result["rows"] == 3
    pins = {d.pincode for d in obs.rows}
    assert pins == {"411046"}
    assert all(d.sku_id is None for d in obs.rows)
    names = {d.sku_name for d in obs.rows}
    assert any("Kohinoor" in n for n in names)
    assert any("India Gate" in n for n in names)
    assert any("Daawat" in n for n in names)
    kohinoor = next(d for d in obs.rows if d.product_id == "527868")
    assert kohinoor.brand_name == "Kohinoor"
    assert kohinoor.discount_percent == 28
    assert kohinoor.unit_price_per_kg == 50.2
    assert pub.derive
    assert any(k.endswith(".html") for k in lake.keys)
    assert any(k.endswith(".json") for k in lake.keys)


def test_blocked_search_retries_bee_not_zenrows():
    from src.domain.errors import UnlockerBlockedError

    class BlockedCatalog:
        platform_id = "blinkit"

        def search(self, *_a, **_k):
            raise UnlockerBlockedError("blocked")

    class Platforms:
        def get(self, _p):
            return BlockedCatalog()

    class Router:
        def __init__(self) -> None:
            self.failovers = 0
            self.fresh = 0

        def session_for_store(self, _s):
            return object(), "scrapingbee"

        def failover_session(self, _s):
            self.failovers += 1
            return object(), "zenrows"

        def fresh_session(self, _s):
            self.fresh += 1
            return object(), "scrapingbee"

    router = Router()
    obs = FakeObs()
    svc = ScrapeStoreService(
        _settings(),
        None,
        None,
        obs,
        FakeAlerts(),
        FakePublisher(),
        FakeLock(),
        FakeCredits(),
        FakeLake(),
        Platforms(),
        router,
    )
    result = svc.run(_job(uuid4()))
    assert result["pages_fail"] == 1
    assert result["rows"] == 0
    assert router.failovers == 0
    assert router.fresh == 1
    assert obs.rows == []


def test_derive_only_on_last_job():
    lock = FakeLock()
    run_id = UUID("11111111-1111-1111-1111-111111111111")
    lock.set_jobs_left(str(run_id), 2)
    pub = FakePublisher()
    svc = ScrapeStoreService(
        _settings(),
        None,
        None,
        FakeObs(),
        FakeAlerts(),
        pub,
        lock,
        FakeCredits(),
        FakeLake(),
        FakePlatforms(),
        FakeRouter(),
    )
    svc.run(_job(uuid4(), run_id))
    assert pub.derive == []
    svc.run(_job(uuid4(), run_id))
    assert pub.derive


def test_scrape_passes_session_cookies_to_catalog():
    seen: list[str | None] = []

    class TrackingCatalog:
        platform_id = "blinkit"
        last_html = "<html></html>"

        def search(self, _unlocker, cookies, query, lat=None, lon=None):
            seen.append(cookies)
            return parse_search_html(
                '<div role="button" id="1">Rice ₹10 ₹12 ADD</div>',
                query=query,
            )

    class Platforms:
        def get(self, _p):
            return TrackingCatalog()

    class SessionUnlocker:
        vendor = "scrapingbee"
        session_cookies = "session=warmed; tok=abc"

    class Router:
        def session_for_store(self, _s):
            return SessionUnlocker(), "scrapingbee"

    svc = ScrapeStoreService(
        _settings(),
        None,
        None,
        FakeObs(),
        FakeAlerts(),
        FakePublisher(),
        FakeLock(),
        FakeCredits(),
        FakeLake(),
        Platforms(),
        Router(),
    )
    svc.run(_job(uuid4()))
    assert seen == ["session=warmed; tok=abc"]
