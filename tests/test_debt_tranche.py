"""Unit tests for DebtTranche model."""

from __future__ import annotations

import pytest

from lbo_simulator.models.debt_tranche import DebtTranche


class TestDebtTranche:
    """Tests for DebtTranche calculations."""

    def test_basic_tranche_creation(self):
        tranche = DebtTranche(
            name="Test Senior",
            tranche_type="senior_term_b",
            principal=100_000_000,
            interest_rate=0.075,
            amortization_rate=0.01,
            maturity_years=7.0,
        )
        assert tranche.outstanding_balance == 100_000_000
        assert tranche.paid_down == 0

    def test_simple_interest_calculation(self):
        tranche = DebtTranche(
            name="Test",
            tranche_type="senior_term_b",
            principal=100_000_000,
            interest_rate=0.075,
            amortization_rate=0.01,
            maturity_years=7.0,
        )
        result = tranche.calculate_interest()

        assert result["interest_paid"] == pytest.approx(7_500_000)
        assert result["mandatory_amortization"] == pytest.approx(1_000_000)
        assert result["optional_sweep"] == 0
        assert result["pik_accrued"] == 0
        assert result["ending_balance"] == pytest.approx(99_000_000)

    def test_cash_sweep(self):
        tranche = DebtTranche(
            name="Test",
            tranche_type="senior_term_b",
            principal=100_000_000,
            interest_rate=0.075,
            amortization_rate=0.01,
            maturity_years=7.0,
            cash_sweep_rate=0.50,
        )
        result = tranche.calculate_interest(excess_cash=20_000_000)

        mandatory = 1_000_000
        sweep = min(20_000_000 * 0.50, 99_000_000)
        assert result["optional_sweep"] == pytest.approx(sweep)
        assert result["ending_balance"] == pytest.approx(100_000_000 - mandatory - sweep)

    def test_pik_toggle(self):
        tranche = DebtTranche(
            name="PIK Mezz",
            tranche_type="mezzanine",
            principal=50_000_000,
            interest_rate=0.10,
            amortization_rate=0.0,
            maturity_years=5.0,
            pik_toggle=True,
            pik_rate=0.02,
        )
        result = tranche.calculate_interest()

        assert result["interest_paid"] == pytest.approx(5_000_000)  # cash
        assert result["pik_accrued"] == pytest.approx(1_000_000)  # PIK
        # PIK accrues to balance
        assert result["ending_balance"] == pytest.approx(51_000_000)

    def test_100_percent_pik(self):
        """100% PIK structure — no cash interest."""
        tranche = DebtTranche(
            name="Pure PIK",
            tranche_type="mezzanine",
            principal=50_000_000,
            interest_rate=0.0,
            amortization_rate=0.0,
            maturity_years=5.0,
            pik_toggle=True,
            pik_rate=0.12,
        )
        result = tranche.calculate_interest()

        assert result["interest_paid"] == 0
        assert result["pik_accrued"] == pytest.approx(6_000_000)
        assert result["ending_balance"] == pytest.approx(56_000_000)

    def test_maturity_check(self):
        tranche = DebtTranche(
            name="Test",
            tranche_type="senior_term_b",
            principal=100_000_000,
            interest_rate=0.075,
            maturity_years=7.0,
        )
        assert not tranche.is_matured(5.0)
        assert tranche.is_matured(7.0)
        assert tranche.is_matured(8.0)

    def test_commitment_fee(self):
        tranche = DebtTranche(
            name="Revolver",
            tranche_type="revolver",
            principal=50_000_000,
            interest_rate=0.07,
            commitment_fee=0.005,
        )
        fee = tranche.calculate_commitment_fee(30_000_000)
        assert fee == pytest.approx(150_000)  # 30M * 0.5%

    def test_non_revolver_no_commitment_fee(self):
        tranche = DebtTranche(
            name="Senior",
            tranche_type="senior_term_b",
            principal=100_000_000,
            interest_rate=0.075,
            commitment_fee=0.005,
        )
        assert tranche.calculate_commitment_fee(50_000_000) == 0

    def test_reset(self):
        tranche = DebtTranche(
            name="Test",
            tranche_type="senior_term_b",
            principal=100_000_000,
            interest_rate=0.075,
            amortization_rate=0.10,  # Higher amortization to ensure balance change
            maturity_years=7.0,
        )
        tranche.calculate_interest()
        # Balance should decrease by amortization_rate * original_principal = 10M
        assert tranche.outstanding_balance == pytest.approx(90_000_000)

        tranche.reset()
        assert tranche.outstanding_balance == 100_000_000

    def test_balance_never_negative(self):
        """Ensure balance never goes below zero even with aggressive sweep."""
        tranche = DebtTranche(
            name="Test",
            tranche_type="senior_term_b",
            principal=10_000_000,
            interest_rate=0.075,
            amortization_rate=0.50,
            maturity_years=7.0,
            cash_sweep_rate=1.0,
        )
        result = tranche.calculate_interest(excess_cash=100_000_000)
        assert result["ending_balance"] >= 0

    def test_repr(self):
        tranche = DebtTranche(
            name="Senior TLB",
            tranche_type="senior_term_b",
            principal=75_000_000,
            interest_rate=0.075,
        )
        assert "Senior TLB" in repr(tranche)
        assert "senior_term_b" in repr(tranche)
