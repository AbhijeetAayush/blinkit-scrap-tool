def unit_price_per_l(selling_price: float | None, pack_ml: int | None) -> float | None:
    if selling_price is None or pack_ml is None or pack_ml <= 0:
        return None
    litres = pack_ml / 1000.0
    if litres <= 0:
        return None
    return round(selling_price / litres, 4)


def unit_price_per_kg(selling_price: float | None, pack_g: int | None) -> float | None:
    if selling_price is None or pack_g is None or pack_g <= 0:
        return None
    kilos = pack_g / 1000.0
    if kilos <= 0:
        return None
    return round(selling_price / kilos, 4)


def discount_percent(mrp: float | None, selling: float | None, from_text: float | None = None) -> float | None:
    if from_text is not None:
        return from_text
    if mrp is None or selling is None or mrp <= 0 or selling > mrp:
        return None
    return round((mrp - selling) / mrp * 100.0, 2)
