from .config import defaults, pick_scenario
from .energy import generation_series, annual_yield_kwh_per_kwp
from .tariff import tariff_series
from .netbilling import retail_series, opex_series, cashflow_production, cashflow_net_billing
from .finance import apply_loan_flows, npv, irr, payback_year, nominal_discount_rate

def simulate(kWp: float = 20.0,
             route: str = "accelerated",            # nominal / accelerated / cpi
             accounting: str = "net_billing",       # production / net_billing
             region: str = "base",
             self_consumption: float = 0.5,
             smb_retail_growth: str = "base",       # low/base/high
             cpi_track: str = "base",               # low/base/high
             capex_per_kwp: float | None = None,
             finance_mode: str = "equity",          # equity / loan / leasing
             loan_scenario: str = "base",           # conservative / base / optimistic
             apply_urban_premium: bool = True):
    years = defaults()["lifetime_years"]
    cpi = pick_scenario("cpi_track", cpi_track)
    retail_growth = pick_scenario("retail_growth", smb_retail_growth)
    if capex_per_kwp is None:
        capex_per_kwp = defaults()["capex_nis_per_kwp"]["smb"]

    # 1) Энергия
    e_series = generation_series(
        kWp,
        years=years,
        yield_kwh_per_kwp=annual_yield_kwh_per_kwp(region),
    )

    # 2) Тарифы (экспорт) + Urban Premium
    up = defaults()["urban_premium_addition"] if apply_urban_premium else 0.0
    t_series = tariff_series(route, kWp, years=years, cpi=cpi, urban_premium_add=up)

    # 3) Ритейл (без CPI)
    r_series = retail_series(kind="smb", years=years, growth=retail_growth)

    # 4) Доходы до OPEX/кредита
    if accounting == "production":
        cash_in = cashflow_production(e_series, t_series)
    else:
        cash_in = cashflow_net_billing(e_series, self_consumption, r_series, t_series)

    # 5) CAPEX/OPEX
    capex_total = capex_per_kwp * kWp
    opex = opex_series(capex_total, years=years, cpi=cpi)

    # 6) Финансирование
    if finance_mode == "equity":
        cf = [-capex_total] + [ci - op for ci, op in zip(cash_in, opex)]

    elif finance_mode == "loan":
        mode_cfg = defaults()["finance_modes"]["loan"]
        scen_cfg = pick_scenario("loan_scenarios", loan_scenario)  # returns dict
        # pick_scenario вернёт dict => доступ по ключам:
        downpayment_ratio = scen_cfg["downpayment"]
        interest = mode_cfg["interest_rate"][scen_cfg["interest"]]
        tenor = mode_cfg["tenor_years"][scen_cfg["tenor"]]

        downpayment = downpayment_ratio * capex_total
        cf0 = -downpayment
        cf_rest = [ci - op for ci, op in zip(cash_in, opex)]
        cf_loan, _ann = apply_loan_flows(cf_rest,
                                         principal=(capex_total - downpayment),
                                         rate_nominal=interest,
                                         years=tenor,
                                         horizon=years)
        cf = [cf0] + cf_loan

    elif finance_mode == "leasing":
        mode_cfg = defaults()["finance_modes"]["leasing"]
        share = mode_cfg["client_share"]
        leasing_years = mode_cfg["leasing_years"]
        cf = [0.0]
        for t, ci in enumerate(cash_in, start=1):
            if t <= leasing_years:
                cf.append(ci * share - opex[t-1])
            else:
                cf.append(ci - opex[t-1])
    else:
        raise ValueError("finance_mode must be equity/loan/leasing")

    # 7) Метрики
    r_disc = nominal_discount_rate()
    metrics = {
        "capex_total": capex_total,
        "payback_year": payback_year(cf),
        "npv": npv(cf, r_disc),
        "irr": irr(cf)
    }

    return {
        "years": list(range(years + 1)),
        "energy_kwh": [0.0] + e_series,
        "tariff_series": [0.0] + t_series,
        "retail_series": [0.0] + r_series,
        "opex": [0.0] + opex,
        "cashflow": cf,
        "metrics": metrics
    }
