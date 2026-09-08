def unit_price_per_l(selling_price: float | None, pack_ml: int | None) -> float | None:
    if selling_price is None or pack_ml is None or pack_ml <= 0:
        return None
    litres = pack_ml / 1000.0
    if litres <= 0:
        return None
    return round(selling_price / litres, 4)
