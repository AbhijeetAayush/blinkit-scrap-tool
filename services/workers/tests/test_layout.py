from src.platforms.blinkit.layout import enrich_from_layout, fetch_product_layout
from src.domain.models import ParsedListing


def test_fetch_product_layout_blocked_returns_none(monkeypatch):
    class _Resp:
        status_code = 401
        def json(self):
            return {}

    class _Client:
        def __enter__(self):
            return self
        def __exit__(self, *_a):
            return False
        def post(self, *_a, **_k):
            return _Resp()

    import src.platforms.blinkit.layout as layout_mod

    monkeypatch.setattr(layout_mod.httpx, "Client", lambda **_k: _Client())
    assert fetch_product_layout("527868", lat=18.44, lon=73.83) is None


def test_enrich_from_layout_stops_when_blocked(monkeypatch):
    listings = [
        ParsedListing(product_id="527868", sku_name="Kohinoor", selling_price=502, mrp=700)
    ]

    def _blocked(*_a, **_k):
        return None

    monkeypatch.setattr("src.platforms.blinkit.layout.fetch_product_layout", _blocked)
    out = enrich_from_layout(listings, lat=18.44, lon=73.83, cookies=None)
    assert out[0].selling_price == 502
    assert out[0].rating is None
