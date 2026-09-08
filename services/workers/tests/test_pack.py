from src.normalize.pack import parse_pack


def test_500_ml_spaced():
    assert parse_pack("500 ml").pack_ml == 500


def test_500ml_compact():
    assert parse_pack("500ml").pack_ml == 500


def test_half_litre():
    assert parse_pack("0.5 L").pack_ml == 500


def test_one_litre():
    assert parse_pack("1L").pack_ml == 1000


def test_500_g():
    assert parse_pack("500 g").pack_g == 500
