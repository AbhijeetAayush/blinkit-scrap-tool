from src.domain.errors import UnlockerBlockedError
from src.unlocker.http import unlocker_get


class _Boom:
    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def get(self, *_a, **_k):
        import httpx

        raise httpx.ReadTimeout("read timed out")


def test_unlocker_get_maps_timeout(monkeypatch):
    import httpx
    import src.unlocker.http as http_mod

    monkeypatch.setattr(http_mod.httpx, "Client", lambda **_k: _Boom())
    try:
        unlocker_get("zenrows", "https://example.invalid/", params={}, headers={})
        raise AssertionError("expected UnlockerBlockedError")
    except UnlockerBlockedError as exc:
        assert "ReadTimeout" in str(exc)
    except httpx.ReadTimeout:
        raise AssertionError("timeout must become UnlockerBlockedError")
