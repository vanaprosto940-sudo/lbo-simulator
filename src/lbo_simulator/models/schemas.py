"""Pydantic schemas for LBO modeling inputs and outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DebtTrancheSchema(BaseModel):
    """Schema for a single debt tranche."""

    name: str
    tranche_type: Literal["senior_term_a", "senior_term_b", "mezzanine", "high_yield", "revolver"]
    principal: float = Field(..., gt=0, description="Initial principal amount")
    interest_rate: float = Field(..., gt=0, description="Annual interest rate (decimal, e.g. 0.075)")
    amortization_rate: float = Field(
        default=0.0, ge=0, le=1, description="Annual amortization rate (fraction of original principal)"
    )
    maturity_years: float = Field(..., gt=0, description="Maturity in years")
    cash_sweep_rate: float = Field(
        default=0.0, ge=0, le=1, description="Percentage of excess cash applied to this tranche"
    )
    pik_toggle: bool = Field(default=False, description="Payment-in-kind toggle option")
    pik_rate: float = Field(default=0.0, ge=0, description="Additional PIK interest rate")
    commitment_fee: float = Field(default=0.0, ge=0, description="Commitment fee on undrawn amount (revolver)")

    @field_validator("interest_rate", "amortization_rate", "cash_sweep_rate", "pik_rate", "commitment_fee")
    @classmethod
    def check_rate_range(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Rates must be non-negative")
        return v


class SourcesAndUsesSchema(BaseModel):
    """Sources and uses of funds for the LBO transaction."""

    # Sources
    equity_contribution: float = Field(..., gt=0, description="Sponsor equity contribution")
    senior_debt: float = Field(default=0, ge=0, description="Senior debt amount")
    mezzanine_debt: float = Field(default=0, ge=0, description="Mezzanine debt amount")
    high_yield_debt: float = Field(default=0, ge=0, description="High yield debt amount")
    revolver_commitment: float = Field(default=0, ge=0, description="Revolver commitment")
    cash_on_balance_sheet: float = Field(default=0, ge=0, description="Company cash available")

    # Uses
    purchase_price: float = Field(..., gt=0, description="Total purchase price")
    transaction_fees: float = Field(default=0, ge=0, description="Transaction fees")
    refinancing_debt: float = Field(default=0, ge=0, description="Debt refinanced")
    capex: float = Field(default=0, ge=0, description="Immediate capex required")

    @field_validator("equity_contribution", "purchase_price")
    @classmethod
    def check_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

    @property
    def total_sources(self) -> float:
        return (
            self.equity_contribution
            + self.senior_debt
            + self.mezzanine_debt
            + self.high_yield_debt
            + self.revolver_commitment
            + self.cash_on_balance_sheet
        )

    @property
    def total_uses(self) -> float:
        return self.purchase_price + self.transaction_fees + self.refinancing_debt + self.capex

    def is_balanced(self, tolerance: float = 1.0) -> bool:
        return abs(self.total_sources - self.total_uses) <= tolerance


class ExitAssumptionsSchema(BaseModel):
    """Exit modeling assumptions."""

    hold_period_years: int = Field(default=5, ge=1, le=15, description="Hold period in years")
    exit_ebitda_multiple: float = Field(..., gt=0, description="Exit EBITDA multiple")
    entry_ebitda_multiple: float = Field(..., gt=0, description="Entry EBITDA multiple")
    terminal_growth_rate: float = Field(default=0.02, ge=0, le=0.05, description="Terminal growth rate (Gordon)")
    use_terminal_value: bool = Field(default=False, description="Use Gordon terminal value instead of multiple")


class CovenantThresholdsSchema(BaseModel):
    """Financial covenant thresholds."""

    max_total_leverage: float = Field(default=6.0, gt=0, description="Max Net Debt / LTM EBITDA")
    min_fixed_charge_coverage: float = Field(
        default=1.0, gt=0, description="Min EBITDA / (Interest + Mandatory Amort + Taxes)"
    )
    min_interest_coverage: float = Field(default=1.5, gt=0, description="Min EBITDA / Interest")


class CompanyProfileSchema(BaseModel):
    """Synthetic or real company financial profile."""

    name: str
    sector: Literal["SaaS", "Industrials", "Healthcare", "Consumer", "TMT", "Other"]
    initial_revenue: float = Field(..., gt=0, description="Initial annual revenue")
    initial_ebitda_margin: float = Field(..., gt=0, le=1, description="Initial EBITDA margin")
    initial_depreciation: float = Field(default=0, ge=0, description="Initial annual depreciation")
    revenue_growth_rates: list[float] = Field(default_factory=list, description="Annual revenue growth rates")
    margin_expansion_bps: list[int] = Field(default_factory=list, description="Annual EBITDA margin expansion in bps")
    capex_pct_revenue: float = Field(default=0.05, ge=0, le=1, description="Capex as % of revenue")
    nwc_pct_revenue: float = Field(default=0.10, ge=0, le=1, description="Net working capital as % of revenue")
    tax_rate: float = Field(default=0.25, ge=0, le=1, description="Corporate tax rate")


class LBOConfigSchema(BaseModel):
    """Main LBO configuration combining all components."""

    company: CompanyProfileSchema
    sources_and_uses: SourcesAndUsesSchema
    tranches: list[DebtTrancheSchema]
    exit_assumptions: ExitAssumptionsSchema
    covenants: CovenantThresholdsSchema = Field(default_factory=CovenantThresholdsSchema)
    seed: int = Field(default=42, description="Random seed for reproducibility")
    data_version: str = Field(default="0.1.0", description="Data version tag for auditability")


class AnnualCashFlowSchema(BaseModel):
    """Annual unlevered free cash flow breakdown."""

    year: int
    revenue: float
    ebitda: float
    taxes: float
    capex: float
    delta_nwc: float
    unlevered_fcf: float
    mandatory_amortization: float
    optional_sweep: float
    pik_accrued: float
    revolver_drawdown: float
    equity_distribution: float


class DebtScheduleYearSchema(BaseModel):
    """Annual debt schedule for each tranche."""

    year: int
    tranche_name: str
    beginning_balance: float
    interest_paid: float
    mandatory_amortization: float
    optional_sweep: float
    pik_accrued: float
    ending_balance: float


class CovenantBreachSchema(BaseModel):
    """Covenant breach record."""

    year: int
    covenant_name: str
    actual_value: float
    threshold_value: float
    severity: Literal["warning", "breach", "critical"]
    remediation_applied: str | None = None


class LBOResultsSchema(BaseModel):
    """LBO simulation results."""

    irr: float = Field(description="Equity IRR (decimal)")
    moic: float = Field(description="Multiple on Invested Capital")
    payback_period_years: float = Field(description="Payback period in years")
    total_equity_invested: float = Field(description="Total equity invested")
    total_equity_returned: float = Field(description="Total equity distributions")
    total_interest_paid: float = Field(description="Total interest paid over hold period")
    total_principal_repaid: float = Field(description="Total principal repaid")
    remaining_debt_at_exit: float = Field(description="Outstanding debt at exit")
    exit_enterprise_value: float = Field(description="Enterprise value at exit")
    exit_equity_value: float = Field(description="Equity value at exit")
    covenant_breaches: list[CovenantBreachSchema] = Field(default_factory=list)
    annual_cash_flows: list[AnnualCashFlowSchema] = Field(default_factory=list)
    debt_schedule: list[DebtScheduleYearSchema] = Field(default_factory=list)

    @field_validator("irr", "moic")
    @classmethod
    def check_finite(cls, v: float) -> float:
        import math

        if not math.isfinite(v):
            raise ValueError("Value must be finite")
        return v
