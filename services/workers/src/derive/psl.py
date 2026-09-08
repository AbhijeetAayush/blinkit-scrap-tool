def predicted_sales_loss(
    velocity_per_store_day: float,
    stores_oos: int,
    days_oos: float,
    price: float,
) -> float:
    lost_units = max(0.0, velocity_per_store_day * stores_oos * days_oos)
    return round(lost_units * price, 2)
