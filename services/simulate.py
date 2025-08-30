# services/simulate.py
from typing import Optional

from .energy import generation_series, annual_yield_kwh_per_kwp
from .tariff import tariff_series
from .netbilling import (
    retail_series,
    opex_series,
    cashflow_production,
    cashflow_net_billing,
)
from .finance import format_metrics
from .config import defaults, pick_scenario


def simulate(
    kwp: float = 20.0,
    route: str = "accelerated",        # 'nominal' | 'accelerated' | 'cpi'
    accounting: str = "net_billing",   # пока поддерживаем только net_billing
    region: str = "base",
    self_consumption: float = 0.5,
    smb_retail_growth: str = "base",   # low/base/high
    cpi_track: str = "base",           # low/base/high
    capex_per_kwp: Optional[float] = None,
    finance_mode: str = "equity",      # equity | loan | leasing
    loan_scenario: str = "base",       # low/base/high
    apply_urban_premium: bool = True,
):
    cfg = defaults()
    years = cfg["lifetime_years"]
    cpi = pick_scenario("cpi_track", cpi_track)
    retail_growth = pick_scenario("retail_growth", smb_retail_growth)

    # Guard-rails (валидируем вход)
    kwp = max(0.1, min(30.0, float(kwp)))
    self_consumption = max(0.0, min(1.0, float(self_consumption)))

    if capex_per_kwp is None:
        capex_per_kwp = cfg["capex_nis_per_kwp"]["smb"]

    # 1) Генерация энергии (ВНИМАНИЕ: ожидается kWp, не kwp)
    e_series = generation_series(
        kWp=kwp,
        years=years,
        yield_kwh_per_kwp=annual_yield_kwh_per_kwp(region),
    )

    # 2) Тариф (экспорт) + урбан-премия
    urban_add = cfg["urban_premium_addition"] if apply_urban_premium else 0.0
    t_series = tariff_series(route, kwp, years=years, cpi=cpi, urban_premium_add=urban_add)

    # 3) Розница (без CPI)
    r_series = retail_series(kind="smb", years=years, growth=retail_growth)

    # 4) Доход vs OPEX/кредит
    if accounting != "net_billing":
        # UI пока не поддерживает pay_for_production — принудительно используем net_billing
        accounting = "net_billing"

    cash_in = cashflow_net_billing(e_series, self_consumption, r_series, t_series)
    capex_total = capex_per_kwp * kwp
    opex = opex_series(capex_total=capex_total, years=years, cpi=cpi)

    # Финансирование
    if finance_mode == "equity":
        cf = [-capex_total] + [ci - op for ci, op in zip(cash_in, opex)]
        metrics = format_metrics(cf, leasing=False)

    elif finance_mode == "loan":
        from .finance_loan import apply_loan_flows

        cf_before_debt = [-capex_total] + [ci - op for ci, op in zip(cash_in, opex)]
        cf = apply_loan_flows(cf_before_debt, loan_scenario)  # CF с обслуживанием долга
        metrics = format_metrics(cf, leasing=False)

    else:  # leasing
        # Простая модель: нет upfront CAPEX, платёж лизинга внутри OPEX (или добавится в отдельной логике)
        # CF начинается с нуля
        cf = [0.0] + [ci - op for ci, op in zip(cash_in, opex)]
        metrics = format_metrics(cf, leasing=True)

    # Возвращаем также "years", чтобы фронт/тестовый эндпоинт мог их рисовать
    return {
        "metrics": metrics,
        "years": list(range(1, years + 1)),
        "cashflow": cf,
        }
