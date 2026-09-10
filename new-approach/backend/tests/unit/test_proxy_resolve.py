from __future__ import annotations

import pytest

from app.config import Settings
from app.infrastructure.browser.proxy.resolve import resolve_proxy


def _settings(**overrides: object) -> Settings:
    base = {
        "proxy_provider": "none",
        "proxy_server": "",
        "proxy_username": "",
        "proxy_password": "",
        "oxylabs_username": "user1",
        "oxylabs_password": "secret",
        "oxylabs_endpoint": "pr.oxylabs.io:7777",
        "oxylabs_country": "IN",
        "brightdata_customer": "cust",
        "brightdata_zone": "zone1",
        "brightdata_password": "bdpass",
        "brightdata_endpoint": "brd.superproxy.io:33335",
        "brightdata_country": "in",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_proxy_none_returns_none() -> None:
    assert resolve_proxy(_settings(proxy_provider="none")) is None
    assert resolve_proxy(_settings(proxy_provider="off")) is None


def test_proxy_generic_override_wins() -> None:
    cfg = resolve_proxy(
        _settings(
            proxy_provider="oxylabs",
            proxy_server="proxy.example:8000",
            proxy_username="u",
            proxy_password="p",
        )
    )
    assert cfg is not None
    assert cfg.server == "proxy.example:8000"
    assert cfg.username == "u"
    assert cfg.password == "p"


def test_oxylabs_username_contains_country_and_sessid() -> None:
    cfg = resolve_proxy(_settings(proxy_provider="oxylabs"), session_id="run:loc")
    assert cfg is not None
    assert "cc-IN" in cfg.username or "-cc-IN" in cfg.username
    assert "sessid" in cfg.username


def test_brightdata_username_contains_zone_and_session() -> None:
    cfg = resolve_proxy(_settings(proxy_provider="brightdata"), session_id="abc123")
    assert cfg is not None
    assert "zone-zone1" in cfg.username
    assert "session-" in cfg.username
    assert "country-in" in cfg.username


def test_invalid_provider_raises() -> None:
    with pytest.raises(ValueError, match="Unknown PROXY_PROVIDER"):
        resolve_proxy(_settings(proxy_provider="scrapingbee"))
