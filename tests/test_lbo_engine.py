"""Integration tests for LBO Engine."""

from __future__ import annotations

import math

import pytest

from lbo_simulator.models.lbo_engine import LBOEngine


class TestLBOEngine:
    """End-to-end LBO simulation tests."""

    def test_full_lbo_run(self, sample_config):
        """Test complete LBO simulation."""
        engine = LBOEngine(sample_config)
        results = engine.run()

        assert math.isfinite(results.irr)
        assert results.irr > 0  # Should be positive return
        assert results.moic > 0
        assert results.payback_period_years > 0
        assert results.exit_enterprise_value > 0
        assert results.exit_equity_value >= 0

    def test_cash_flows_generated(self, sample_config):
        """Ensure annual cash flows are populated."""
        engine = LBOEngine(sample_config)
        results = engine.run()

        hold_period = sample_config.exit_assumptions.hold_period_years
        assert len(results.annual_cash_flows) == hold_period

        # Each year should have positive EBITDA
        for cf in results.annual_cash_flows:
            assert cf.ebitda > 0
            assert cf.revenue > 0

    def test_debt_schedule_generated(self, sample_config):
        """Ensure debt schedule is populated for all tranches."""
        engine = LBOEngine(sample_config)
        results = engine.run()

        hold_period = sample_config.exit_assumptions.hold_period_years
        n_tranches = len(sample_config.tranches)
        assert len(results.debt_schedule) == hold_period * n_tranches

    def test_remaining_debt_non_negative(self, sample_config):
        """Remaining debt at exit should be non-negative."""
        engine = LBOEngine(sample_config)
        results = engine.run()

        assert results.remaining_debt_at_exit >= 0

    def test_moic_consistency(self, sample_config):
        """MOIC should equal total returned / invested."""
        engine = LBOEngine(sample_config)
        results = engine.run()

        expected_moic = results.total_equity_returned / results.total_equity_invested
        assert results.moic == pytest.approx(expected_moic, rel=0.01)

    def test_positive_ebitda_growth(self, sample_config):
        """EBITDA should grow if revenue growth and margin expansion are positive."""
        engine = LBOEngine(sample_config)
        results = engine.run()

        cash_flows = results.annual_cash_flows
        if len(cash_flows) >= 2:
            # With 10% growth + margin expansion, EBITDA should increase
            assert cash_flows[-1].ebitda > cash_flows[0].ebitda

    def test_reset_engine(self, sample_config):
        """Test that engine can be reset and re-run."""
        engine = LBOEngine(sample_config)
        results1 = engine.run()

        engine.reset()
        results2 = engine.run()

        assert results1.irr == pytest.approx(results2.irr)
        assert results1.moic == pytest.approx(results2.moic)

    def test_high_leverage_stress(self, sample_config):
        """Test LBO with very high leverage."""
        # Increase debt, decrease equity
        config = sample_config.model_copy(
            update={
                "sources_and_uses": sample_config.sources_and_uses.model_copy(
                    update={
                        "equity_contribution": 50_000_000,
                        "senior_debt": 120_000_000,
                    }
                )
            }
        )
        # Update tranche
        tranches = list(config.tranches)
        tranches[0] = tranches[0].model_copy(update={"principal": 120_000_000})
        config = config.model_copy(update={"tranches": tranches})

        engine = LBOEngine(config)
        results = engine.run()

        # Should still run without errors
        assert math.isfinite(results.irr)

    def test_negative_ebitda_edge_case(self):
        """Test handling of negative EBITDA scenario."""
        config = self._create_negative_ebitda_config()
        engine = LBOEngine(config)
        results = engine.run()

        # Should handle gracefully (no crash)
        assert math.isfinite(results.irr) or results.irr == float("-inf")

    def _create_negative_ebitda_config(self):
        """Create a config with declining EBITDA."""
        from lbo_simulator.models.schemas import (
            CompanyProfileSchema,
            DebtTrancheSchema,
            ExitAssumptionsSchema,
            LBOConfigSchema,
            SourcesAndUsesSchema,
        )

        company = CompanyProfileSchema(
            name="DecliningCo",
            sector="Industrials",
            initial_revenue=100_000_000,
            initial_ebitda_margin=0.15,
            initial_depreciation=5_000_000,
            revenue_growth_rates=[-0.10, -0.10, -0.08, -0.05, -0.03],
            margin_expansion_bps=[-200, -150, -100, -50, -25],
            capex_pct_revenue=0.08,
            nwc_pct_revenue=0.15,
            tax_rate=0.25,
        )

        ebitda = company.initial_revenue * company.initial_ebitda_margin
        purchase_price = ebitda * 6.0
        equity = purchase_price * 0.40
        debt = purchase_price * 0.60

        return LBOConfigSchema(
            company=company,
            sources_and_uses=SourcesAndUsesSchema(
                equity_contribution=equity,
                senior_debt=debt,
                purchase_price=purchase_price,
                transaction_fees=purchase_price * 0.01,
            ),
            tranches=[
                DebtTrancheSchema(
                    name="Senior",
                    tranche_type="senior_term_b",
                    principal=debt,
                    interest_rate=0.08,
                    amortization_rate=0.01,
                    maturity_years=7.0,
                )
            ],
            exit_assumptions=ExitAssumptionsSchema(
                hold_period_years=5,
                exit_ebitda_multiple=5.0,
                entry_ebitda_multiple=6.0,
            ),
        )
