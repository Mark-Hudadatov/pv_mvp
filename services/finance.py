from .config import defaults, nominal_rate_from_real, pick_scenario

def annuity_payment(principal: float, rate: float, years: int) -> float:
    if rate == 0:
        return principal / years
    k = rate
    return principal * (k * (1 + k) ** years) / ((1 + k) ** years - 1)

def apply_loan_flows(cash_in_series: list[float], principal: float,
                     rate_nominal: float, years: int, horizon: int) -> tuple[list[float], float]:
    pay = annuity_payment(principal, rate_nominal, years)
    out = []
    for t in range(horizon):
        out.append(cash_in_series[t] - (pay if t < years else 0.0))
    return out, pay

def npv(cashflows: list[float], r: float) -> float:
    return cashflow[0] + sum(cf / ((1 + r) ** t) for t, cf in enumerate(cashflows[1:], start=1))

def irr(cashflows: list[float], guess: float = 0.1, tol: float = 1e-6, max_iter: int = 100):
    r = guess
    for _ in range(max_iter):
        npv_val = 0.0
        dnpv = 0.0
        for t, cf in enumerate(cashflows):
            denom = (1 + r) ** t
            npv_val += cf / denom
            if t > 0:
                dnpv -= t * cf / ((1 + r) ** (t + 1))
        if abs(dnpv) < 1e-12:
            return None
        step = npv_val / dnpv
        r -= step
        if abs(step) < tol:
            return r
    return None

def payback_year(cashflows: list[float]):
    cum = 0.0
    for t, cf in enumerate(cashflows):
        cum += cf
        if cum >= 0:
            return t
    return None

def nominal_discount_rate() -> float:
    cpi = pick_scenario("cpi_track", "base")
    return nominal_rate_from_real(defaults()["discount_rate_real"], cpi)
