from __future__ import annotations

from app.normalize.pack import parse_pack
from app.normalize.unit_price import discount_percent, unit_price_per_kg, unit_price_per_l


def test_parse_pack_kg_and_g() -> None:
    assert parse_pack("10 kg").pack_g == 10_000
    assert parse_pack("500 g").pack_g == 500
    assert parse_pack("1 L").pack_ml == 1000
    assert parse_pack("250 ml").pack_ml == 250


def test_unit_prices() -> None:
    assert unit_price_per_kg(502.0, 10_000) == 50.2
    assert unit_price_per_l(100.0, 1000) == 100.0
    assert discount_percent(700.0, 502.0) == 28.29
    assert discount_percent(700.0, 502.0, from_text=28.0) == 28.0
