"""Financial utility functions."""

from __future__ import annotations


def xirr(cash_flows: list[float], dates: list[float], guess: float = 0.1) -> float:
    """Calculate Internal Rate of Return using XNPV method.

    Args:
        cash_flows: list of cash flows (negative = outflow, positive = inflow)
        dates: list of dates as fractional years from t=0
        guess: initial guess for IRR

    Returns:
        IRR as a decimal (e.g. 0.25 = 25%)
    """
    if len(cash_flows) < 2:
        return float("inf")

    # NPV function for a given rate
    def npv(rate: float) -> float:
        return sum(  # type: ignore[no-any-return]
            cf / (1 + rate) ** t for cf, t in zip(cash_flows, dates)
        )

    # Newton-Raphson solver
    rate = guess
    for _ in range(1000):
        val = npv(rate)
        if abs(val) < 1e-8:
            return rate
        # Numerical derivative
        delta = 1e-7
        der = (npv(rate + delta) - val) / delta
        if abs(der) < 1e-12:
            break
        rate = rate - val / der

    # Fallback to numpy if Newton-Raphson fails
    try:
        import numpy as _np

        result = _np.irr(cash_flows)  # type: ignore[attr-defined]
        if result is not None and len(result) > 0:
            return float(result[0])
    except Exception:
        pass
    return rate


def moic(total_distributions: float, total_invested: float) -> float:
    """Multiple on Invested Capital."""
    if total_invested == 0:
        return float("inf")
    return total_distributions / total_invested


def payback_period(cash_flows: list[float], years: list[float]) -> float:
    """Calculate payback period in years.

    Args:
        cash_flows: cumulative cash flows (starting with negative investment)
        years: corresponding years

    Returns:
        Payback period in years, or -1 if never paid back
    """
    cumulative = 0.0
    for i, cf in enumerate(cash_flows):
        cumulative += cf
        if cumulative >= 0:
            if i == 0:
                return years[0]
            # Linear interpolation
            prev_cumulative = cumulative - cf
            fraction = -prev_cumulative / cf if cf != 0 else 0
            return years[i - 1] + fraction * (years[i] - years[i - 1])
    return -1.0


def wacc(
    equity_weight: float,
    debt_weight: float,
    cost_of_equity: float,
    cost_of_debt: float,
    tax_rate: float,
) -> float:
    """Weighted Average Cost of Capital.

    WACC = We * Re + Wd * Rd * (1 - T)
    """
    return equity_weight * cost_of_equity + debt_weight * cost_of_debt * (1 - tax_rate)


def gordon_terminal_value(
    final_year_fcf: float, terminal_growth_rate: float, discount_rate: float
) -> float:
    """Gordon Growth Model for terminal value.

    TV = FCF_n * (1 + g) / (r - g)
    """
    if discount_rate <= terminal_growth_rate:
        raise ValueError("Discount rate must be greater than terminal growth rate")
    return final_year_fcf * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)


def break_even_exit_multiple(
    target_irr: float,
    equity_invested: float,
    annual_cash_flows: list[float],
    hold_period: int,
) -> float:
    """Find exit enterprise value that yields target IRR.

    Uses binary search to find the exit EV that makes IRR = target.
    """
    low = 0.0
    high = equity_invested * 50  # reasonable upper bound

    for _ in range(100):
        mid = (low + high) / 2
        # Construct cash flows: initial investment + annual flows + exit value
        test_cfs: list[float] = (
            [-equity_invested] + annual_cash_flows[:-1] + [annual_cash_flows[-1] + mid]
        )
        test_dates: list[float] = [float(i) for i in range(len(test_cfs))]

        try:
            irr = xirr(test_cfs, test_dates)
        except Exception:
            high = mid
            continue

        if abs(irr - target_irr) < 0.001:
            return mid
        if irr < target_irr:
            low = mid
        else:
            high = mid

    return mid


def npv(rate: float, cash_flows: list[float]) -> float:
    """Net Present Value."""
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
