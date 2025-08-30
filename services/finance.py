# services/finance.py

from typing import List, Optional
from .config import defaults, pick_scenario
import math

def safe_round(x, n=2):
    return None if x is None else round(x, n)

def nominal_rate_from_real(r_real: float, cpi: float) -> float:
    # (1+r_nom) = (1+r_real)*(1+CPI)
    return (1 + r_real) * (1 + cpi) - 1

def nominal_discount_rate() -> float:
    cpi = pick_scenario("cpi_track", "base")
    r_real = defaults()["discount_rate_real"]
    return nominal_rate_from_real(r_real, cpi)

def npv(cashflows: List[float], r: float) -> float:
    return sum(cf / ((1 + r) ** t) for t, cf in enumerate(cashflows))

def irr(cashflows: List[float], guess: float = 0.1, tol: float = 1e-6, max_iter: int = 100) -> Optional[float]:
    # IRR существует только если есть смена знака в потоке
    has_pos = any(cf > 0 for cf in cashflows)
    has_neg = any(cf < 0 for cf in cashflows)
    if not (has_pos and has_neg):
        return None

    r = guess
    for _ in range(max_iter):
        dnpv = 0.0
        npv_val = 0.0
        for t, cf in enumerate(cashflows):
            disc = (1 + r) ** t
            npv_val += cf / disc
            if t > 0:
                dnpv += -t * cf / ((1 + r) ** (t + 1))
        if abs(npv_val) < tol:
            return r
        if dnpv == 0:
            return None
        step = npv_val / dnpv
        r -= step
        if abs(step) < tol:
            return r
    return None

def payback_year(cashflows: List[float]) -> Optional[int]:
    cum = 0.0
    for t, cf in enumerate(cashflows):
        cum += cf
        if cum >= 0:
            return t
    return None  # никогда не окупается

def format_metrics(cashflows: List[float], leasing: bool = False):
    """Возвращает метрики безопасно, без падений."""
    r_nom = nominal_discount_rate()
    the_npv = npv(cashflows, r_nom)

    # Для лизинга IRR/Payback не применимы (денежный поток другой природы)
    if leasing:
        return {
            "npv": safe_round(the_npv),
            "irr": None,
            "payback_year": None,
            "annual_surplus": safe_round(sum(cashflows[1:]) / (len(cashflows) - 1)) if len(cashflows) > 1 else None,
            "not_applicable": ["irr", "payback_year"],
            "warnings": ["IRR and Payback are not applicable to leasing flows."]
        }

    the_irr = irr(cashflows)
    the_payback = payback_year(cashflows)

    warn = []
    na = []
    if the_irr is None:
        na.append("irr")
        warn.append("IRR is undefined (no sign change in cash flow).")
    if the_payback is None:
        na.append("payback_year")
        warn.append("Payback does not occur within the analysis horizon.")

    return {
        "npv": safe_round(the_npv),
        "irr": safe_round(the_irr),
        "payback_year": the_payback,
        "not_applicable": na,
        "warnings": warn
    }
