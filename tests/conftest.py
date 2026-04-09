"""Common test fixtures."""

from __future__ import annotations

import pytest

from lbo_simulator.models.schemas import (
    CompanyProfileSchema,
    CovenantThresholdsSchema,
    DebtTrancheSchema,
    ExitAssumptionsSchema,
    LBOConfigSchema,
    SourcesAndUsesSchema,
)


@pytest.fixture()
def sample_company() -> CompanyProfileSchema:
    return CompanyProfileSchema(
        name="TestCo",
        sector="SaaS",
        initial_revenue=100_000_000,
        initial_ebitda_margin=0.25,
        initial_depreciation=3_000_000,
        revenue_growth_rates=[0.10, 0.08, 0.06, 0.05, 0.04],
        margin_expansion_bps=[100, 75, 50, 25, 25],
        capex_pct_revenue=0.03,
        nwc_pct_revenue=0.05,
        tax_rate=0.21,
    )


@pytest.fixture()
def sample_sources_uses() -> SourcesAndUsesSchema:
    return SourcesAndUsesSchema(
        equity_contribution=112_500_000,
        senior_debt=75_625_000,
        mezzanine_debt=34_375_000,
        high_yield_debt=27_500_000,
        purchase_price=206_250_000,
        transaction_fees=2_062_500,
    )


@pytest.fixture()
def sample_tranches() -> list[DebtTrancheSchema]:
    return [
        DebtTrancheSchema(
            name="Senior Term Loan B",
            tranche_type="senior_term_b",
            principal=75_625_000,
            interest_rate=0.075,
            amortization_rate=0.01,
            maturity_years=7.0,
            cash_sweep_rate=0.50,
        ),
        DebtTrancheSchema(
            name="Mezzanine",
            tranche_type="mezzanine",
            principal=34_375_000,
            interest_rate=0.10,
            amortization_rate=0.0,
            maturity_years=5.0,
            pik_toggle=True,
            pik_rate=0.02,
        ),
        DebtTrancheSchema(
            name="High Yield",
            tranche_type="high_yield",
            principal=27_500_000,
            interest_rate=0.09,
            amortization_rate=0.0,
            maturity_years=6.0,
        ),
    ]


@pytest.fixture()
def sample_exit_assumptions() -> ExitAssumptionsSchema:
    return ExitAssumptionsSchema(
        hold_period_years=5,
        exit_ebitda_multiple=9.5,
        entry_ebitda_multiple=8.25,
    )


@pytest.fixture()
def sample_covenants() -> CovenantThresholdsSchema:
    return CovenantThresholdsSchema(
        max_total_leverage=5.5,
        min_fixed_charge_coverage=1.1,
        min_interest_coverage=1.8,
    )


@pytest.fixture()
def sample_config(
    sample_company: CompanyProfileSchema,
    sample_sources_uses: SourcesAndUsesSchema,
    sample_tranches: list[DebtTrancheSchema],
    sample_exit_assumptions: ExitAssumptionsSchema,
    sample_covenants: CovenantThresholdsSchema,
) -> LBOConfigSchema:
    return LBOConfigSchema(
        company=sample_company,
        sources_and_uses=sample_sources_uses,
        tranches=sample_tranches,
        exit_assumptions=sample_exit_assumptions,
        covenants=sample_covenants,
    )
