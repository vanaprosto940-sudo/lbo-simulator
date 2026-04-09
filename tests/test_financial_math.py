"""Unit tests for financial math utilities."""

from __future__ import annotations

import math

import pytest

from lbo_simulator.utils.financial_math import (
    break_even_exit_multiple,
    gordon_terminal_value,
    moic,
    npv,
    payback_period,
    wacc,
    xirr,
)


class TestXIRR:
    """Tests for XIRR calculation."""

    def test_simple_investment(self):
        """Simple investment: -100 at t=0, +150 at t=1."""
        cfs = [-100, 150]
        dates = [0, 1]
        irr = xirr(cfs, dates)
        assert irr == pytest.approx(0.50, abs=0.01)

    def test_multi_year_investment(self):
        """Investment with multiple cash flows."""
        cfs = [-100, 20, 30, 40, 50]
        dates = [0, 1, 2, 3, 4]
        irr = xirr(cfs, dates)
        assert irr > 0
        assert math.isfinite(irr)

    def test_empty_cash_flows(self):
        """Empty cash flows should return inf."""
        assert xirr([], []) == float("inf")

    def test_single_cash_flow(self):
        """Single cash flow should return inf."""
        assert xirr([100], [0]) == float("inf")


class TestMOIC:
    """Tests for MOIC calculation."""

    def test_basic_moic(self):
        assert moic(250, 100) == pytest.approx(2.5)

    def test_moic_no_return(self):
        assert moic(0, 100) == pytest.approx(0.0)

    def test_moic_zero_investment(self):
        assert moic(100, 0) == float("inf")

    def test_moic_loss(self):
        assert moic(50, 100) == pytest.approx(0.5)


class TestPaybackPeriod:
    """Tests for payback period calculation."""

    def test_simple_payback(self):
        cfs = [-100, 50, 50, 50]
        years = [0, 1, 2, 3]
        payback = payback_period(cfs, years)
        assert payback == pytest.approx(2.0, abs=0.01)

    def test_fractional_payback(self):
        cfs = [-100, 40, 40, 40]
        years = [0, 1, 2, 3]
        payback = payback_period(cfs, years)
        assert 2.0 < payback < 3.0

    def test_no_payback(self):
        cfs = [-100, 10, 10]
        years = [0, 1, 2]
        assert payback_period(cfs, years) == -1.0


class TestWACC:
    """Tests for WACC calculation."""

    def test_basic_wacc(self):
        wacc_val = wacc(0.5, 0.5, 0.10, 0.06, 0.25)
        assert wacc_val == pytest.approx(0.0725, abs=0.001)

    def test_all_equity(self):
        wacc_val = wacc(1.0, 0.0, 0.10, 0.06, 0.25)
        assert wacc_val == pytest.approx(0.10)

    def test_all_debt(self):
        wacc_val = wacc(0.0, 1.0, 0.10, 0.06, 0.25)
        assert wacc_val == pytest.approx(0.045)  # 0.06 * (1 - 0.25)


class TestGordonTerminalValue:
    """Tests for Gordon Growth Model."""

    def test_basic_terminal_value(self):
        tv = gordon_terminal_value(100, 0.02, 0.08)
        assert tv == pytest.approx(1700.0, abs=1.0)  # 100 * 1.02 / (0.08 - 0.02)

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            gordon_terminal_value(100, 0.10, 0.08)  # growth > discount


class TestNPV:
    """Tests for NPV calculation."""

    def test_basic_npv(self):
        cfs = [-100, 50, 50, 50]
        assert npv(0.10, cfs) == pytest.approx(24.34, abs=0.01)

    def test_zero_rate(self):
        cfs = [-100, 50, 50]
        assert npv(0.0, cfs) == pytest.approx(0.0)


class TestBreakEvenExitMultiple:
    """Tests for break-even exit multiple solver."""

    def test_break_even_search(self):
        result = break_even_exit_multiple(
            target_irr=0.20,
            equity_invested=100,
            annual_cash_flows=[10, 15, 20, 25, 150],
            hold_period=5,
        )
        assert result > 0
        assert math.isfinite(result)
