from src.unlocker.cookies import merge_cookie_header
from src.unlocker.router import _CookieMemoryUnlocker
from src.domain.models import FetchResult


class _Inner:
    vendor = "scrapingbee"

    def __init__(self) -> None:
        self.last_cookies: str | None = None

    def fetch(self, url: str, **kwargs) -> FetchResult:
        self.last_cookies = kwargs.get("cookies")
        return FetchResult(
            html="<html></html>",
            cookies="session=abc; Path=/; gr_1_lat=28.4; gr_1_lon=77.0",
            status_code=200,
            vendor="scrapingbee",
        )


def test_merge_keeps_job_lat_lon():
    existing = "gr_1_lat=18.4478; gr_1_lon=73.8371; lat=18.4478; lon=73.8371"
    incoming = "session=abc; Path=/; gr_1_lat=28.4595; gr_1_lon=77.0266"
    merged = merge_cookie_header(existing, incoming)
    assert merged is not None
    assert "gr_1_lat=18.4478" in merged
    assert "gr_1_lon=73.8371" in merged
    assert "session=abc" in merged


def test_cookie_memory_unlocker_keeps_lat_after_set_cookie():
    unlocker = _CookieMemoryUnlocker(_Inner(), cookies="gr_1_lat=18.4478; gr_1_lon=73.8371")
    unlocker.fetch("https://blinkit.com/s/?q=rice")
    assert unlocker.session_cookies is not None
    assert "gr_1_lat=18.4478" in unlocker.session_cookies
    assert "gr_1_lon=73.8371" in unlocker.session_cookies


def test_geo_kwargs_do_not_drop_redis_session_token():
    """Catalog passes geo Cookie string; Redis jar must still forward session tokens."""
    inner = _Inner()
    unlocker = _CookieMemoryUnlocker(
        inner,
        cookies="session=tok123; other=1; gr_1_lat=28.0; gr_1_lon=77.0",
    )
    job_geo = "gr_1_lat=18.4478; gr_1_lon=73.8371; lat=18.4478; lon=73.8371"
    unlocker.fetch("https://blinkit.com/s/?q=rice", cookies=job_geo)
    sent = inner.last_cookies or ""
    assert "gr_1_lat=18.4478" in sent
    assert "gr_1_lon=73.8371" in sent
    assert "session=tok123" in sent
    # Job coords must win over Redis foreign lat/lon
    assert "gr_1_lat=28.0" not in sent
