from .config import defaults

def size_kwp_from_area(area_m2: float, power_density: float | None = None) -> float:
    if power_density is None:
        power_density = defaults()["power_density_kw_per_m2"]
    return area_m2 * power_density

def annual_yield_kwh_per_kwp(region: str = "base") -> float:
    y = defaults()["yield_kwh_per_kwp_year"]
    return y[region] if isinstance(y, dict) else y

def generation_series(kWp: float,
                      years: int | None = None,
                      yield_kwh_per_kwp: float | None = None,
                      degradation: float | None = None) -> list[float]:
    if years is None:
        years = defaults()["lifetime_years"]
    if yield_kwh_per_kwp is None:
        yield_kwh_per_kwp = annual_yield_kwh_per_kwp("base")
    if degradation is None:
        degradation = defaults()["degradation_annual"]
    e1 = kWp * yield_kwh_per_kwp
    return [e1 * ((1 - degradation) ** t) for t in range(years)]
