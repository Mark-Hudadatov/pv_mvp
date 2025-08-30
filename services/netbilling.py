from .config import defaults, pick_scenario

def retail_series(kind: str = "smb", years: int | None = None,
                  growth: float | None = None) -> list[float]:
    if years is None:
        years = defaults()["lifetime_years"]
    if growth is None:
        growth = pick_scenario("retail_growth", "base")
    r = defaults()["retail_tariff_nis_per_kwh"][kind]
    arr = []
    for _ in range(years):
        arr.append(r)
        r *= (1 + growth)  # БЕЗ CPI!
    return arr

def opex_series(capex_total: float, years: int | None = None,
                cpi: float | None = None) -> list[float]:
    if years is None:
        years = defaults()["lifetime_years"]
    if cpi is None:
        cpi = pick_scenario("cpi_track", "base")
    opex1 = defaults()["opex_pct_of_capex"] * capex_total
    return [opex1 * ((1 + cpi) ** t) for t in range(years)]

def cashflow_production(e_series_kwh: list[float], tariff_rate_series: list[float]) -> list[float]:
    return [e * t for e, t in zip(e_series_kwh, tariff_rate_series)]

def cashflow_net_billing(e_series_kwh: list[float], self_share: float,
                         retail_series_nis: list[float],
                         export_tariff_series: list[float]) -> list[float]:
    s = self_share
    return [(s * e) * rt + ((1 - s) * e) * tx
            for e, rt, tx in zip(e_series_kwh, retail_series_nis, export_tariff_series)]
