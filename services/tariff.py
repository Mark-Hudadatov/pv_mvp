from .config import defaults, tariffs, pick_scenario

def tariff_nominal(kWp: float) -> float:
    t = tariffs()["nominal"]
    return t["up_to_15_kw"] if kWp <= 15 else t["from_16_to_30_kw"]

def tariff_accelerated_series(kWp: float, years: int | None = None) -> list[float]:
    if years is None:
        years = defaults()["lifetime_years"]
    acc = tariffs()["accelerated_payback"]
    y_high = acc["years_high"]
    if kWp <= 15:
        hi = acc["tier1_up_to_15_kw"]["high_phase"]
        lo = acc["tier1_up_to_15_kw"]["low_phase"]
    else:
        hi = acc["tier2_15_to_30_kw"]["high_phase"]
        lo = acc["tier2_15_to_30_kw"]["low_phase"]
    return [hi] * y_high + [lo] * (years - y_high)

def tariff_cpi_series(kWp: float, years: int | None = None,
                      cpi: float | None = None) -> list[float]:
    if years is None:
        years = defaults()["lifetime_years"]
    cfg = tariffs()["cpi_linked"]
    if kWp > cfg["max_kw"]:
        # fallback на номинальный, если >15 кВт
        return [tariff_nominal(kWp)] * years
    if cpi is None:
        cpi = pick_scenario("cpi_track", "base")
    rate = cfg["base_rate"]
    out = []
    for _ in range(years):
        out.append(rate)
        rate *= (1 + cpi)
    return out

def tariff_series(route: str, kWp: float,
                  years: int | None = None,
                  cpi: float | None = None,
                  urban_premium_add: float = 0.0,
                  premium_years: int = 15) -> list[float]:
    if years is None:
        years = defaults()["lifetime_years"]
    if route == "nominal":
        base = [tariff_nominal(kWp)] * years
    elif route == "accelerated":
        base = tariff_accelerated_series(kWp, years)
    elif route == "cpi":
        base = tariff_cpi_series(kWp, years, cpi)
    else:
        raise ValueError("route must be: nominal / accelerated / cpi")
    out = []
    for t, r in enumerate(base):
        add = urban_premium_add if t < premium_years else 0.0
        out.append(r + add)
    return out
