"""Core LBO Engine — constructs debt schedules, cash flow waterfalls, and returns."""

from __future__ import annotations

from loguru import logger

from lbo_simulator.models.debt_tranche import DebtTranche
from lbo_simulator.models.schemas import (
    AnnualCashFlowSchema,
    DebtScheduleYearSchema,
    LBOConfigSchema,
    LBOResultsSchema,
)
from lbo_simulator.utils.financial_math import moic, payback_period, xirr


class LBOEngine:
    """Core engine for running LBO simulations.

    Models:
    - Multi-tranche debt schedule with amortization, cash sweep, PIK
    - Cash flow waterfall: EBITDA → Taxes → Capex → ΔNWC → FCF → Debt Service → Equity
    - Returns: IRR, MOIC, payback period
    """

    def __init__(self, config: LBOConfigSchema) -> None:
        self.config = config
        self.tranches: list[DebtTranche] = []
        self.annual_cash_flows: list[AnnualCashFlowSchema] = []
        self.debt_schedule: list[DebtScheduleYearSchema] = []
        self.audit_id: str = ""

        # Build tranches from config
        for t in config.tranches:
            self.tranches.append(
                DebtTranche(
                    name=t.name,
                    tranche_type=t.tranche_type,
                    principal=t.principal,
                    interest_rate=t.interest_rate,
                    amortization_rate=t.amortization_rate,
                    maturity_years=t.maturity_years,
                    cash_sweep_rate=t.cash_sweep_rate,
                    pik_toggle=t.pik_toggle,
                    pik_rate=t.pik_rate,
                    commitment_fee=t.commitment_fee,
                )
            )

    def run(self) -> LBOResultsSchema:
        """Execute the full LBO simulation.

        Returns:
            LBOResultsSchema with IRR, MOIC, cash flows, debt schedule, etc.
        """
        self.audit_id = self._generate_audit_id()
        logger.info(f"[{self.audit_id}] Starting LBO simulation for {self.config.company.name}")

        hold_period = self.config.exit_assumptions.hold_period_years
        company = self.config.company

        # Build financial projections
        revenues = self._project_revenues()
        ebitdas = self._project_ebitdas()
        depreciations = self._project_depreciations()
        capex_list = self._project_capex()
        nwc_list = self._project_nwc()

        # Initialize results
        annual_cash_flows: list[AnnualCashFlowSchema] = []
        debt_schedule: list[DebtScheduleYearSchema] = []

        total_interest_paid = 0.0
        total_principal_repaid = 0.0
        total_pik_accrued = 0.0
        total_sweep = 0.0
        total_amort = 0.0

        # Equity cash flow tracking
        equity_flows = [
            -self.config.sources_and_uses.equity_contribution
        ]  # t=0: negative investment
        equity_distributions_list: list[float] = []

        # Run year-by-year simulation
        for year in range(1, hold_period + 1):
            revenue = revenues[year - 1]
            ebitda = ebitdas[year - 1]
            depreciation = depreciations[year - 1]
            capex = capex_list[year - 1]

            # ΔNWC (change from previous year)
            if year == 1:
                delta_nwc = nwc_list[year - 1]
            else:
                delta_nwc = nwc_list[year - 1] - nwc_list[year - 2]

            # Taxes (on EBIT - interest, but we'll approximate with EBITDA - Depreciation)
            ebt = ebitda - depreciation
            taxes = max(0, ebt * company.tax_rate)

            # Unlevered free cash flow
            unlevered_fcf = ebitda - taxes - capex - delta_nwc

            # Debt service
            mandatory_amort_total = 0.0
            optional_sweep_total = 0.0
            interest_total = 0.0
            pik_total = 0.0

            # Excess cash available for sweep (after mandatory payments)
            excess_cash = unlevered_fcf

            for tranche in self.tranches:
                result = tranche.calculate_interest(excess_cash)

                interest_total += result["interest_paid"]
                pik_total += result["pik_accrued"]
                mandatory_amort_total += result["mandatory_amortization"]
                optional_sweep_total += result["optional_sweep"]

                # Update excess cash after sweep
                excess_cash -= result["mandatory_amortization"] + result["optional_sweep"]

                # Record debt schedule
                debt_schedule.append(
                    DebtScheduleYearSchema(
                        year=year,
                        tranche_name=tranche.name,
                        beginning_balance=tranche.outstanding_balance
                        + result["mandatory_amortization"]
                        + result["optional_sweep"]
                        - result["pik_accrued"],
                        interest_paid=result["interest_paid"],
                        mandatory_amortization=result["mandatory_amortization"],
                        optional_sweep=result["optional_sweep"],
                        pik_accrued=result["pik_accrued"],
                        ending_balance=result["ending_balance"],
                    )
                )

            total_interest_paid += interest_total
            total_pik_accrued += pik_total
            total_sweep += optional_sweep_total
            total_amort += mandatory_amort_total
            total_principal_repaid += mandatory_amort_total + optional_sweep_total

            # Cash available for equity distributions
            remaining_cash = unlevered_fcf - mandatory_amort_total - optional_sweep_total
            equity_distribution = max(0, remaining_cash)

            equity_distributions_list.append(equity_distribution)
            equity_flows.append(equity_distribution)

            annual_cash_flows.append(
                AnnualCashFlowSchema(
                    year=year,
                    revenue=revenue,
                    ebitda=ebitda,
                    taxes=taxes,
                    capex=capex,
                    delta_nwc=delta_nwc,
                    unlevered_fcf=unlevered_fcf,
                    mandatory_amortization=mandatory_amort_total,
                    optional_sweep=optional_sweep_total,
                    pik_accrued=pik_total,
                    revolver_drawdown=0.0,  # Simplified
                    equity_distribution=equity_distribution,
                )
            )

        # Exit calculations
        exit_ebitda = ebitdas[-1]
        exit_ev = exit_ebitda * self.config.exit_assumptions.exit_ebitda_multiple

        # Remaining debt at exit
        remaining_debt = sum(t.outstanding_balance for t in self.tranches)

        # Net equity value at exit
        exit_equity_value = max(0, exit_ev - remaining_debt)

        # Add exit proceeds to equity flows
        equity_flows[-1] += exit_equity_value

        # Calculate returns
        dates = list(range(len(equity_flows)))
        irr = xirr(equity_flows, dates)

        total_equity_returned = sum(equity_distributions_list) + exit_equity_value
        equity_invested = self.config.sources_and_uses.equity_contribution
        moic_val = moic(total_equity_returned, equity_invested)

        payback = payback_period(equity_flows, dates)

        results = LBOResultsSchema(
            irr=irr,
            moic=moic_val,
            payback_period_years=payback,
            total_equity_invested=equity_invested,
            total_equity_returned=total_equity_returned,
            total_interest_paid=total_interest_paid,
            total_principal_repaid=total_principal_repaid,
            remaining_debt_at_exit=remaining_debt,
            exit_enterprise_value=exit_ev,
            exit_equity_value=exit_equity_value,
            annual_cash_flows=annual_cash_flows,
            debt_schedule=debt_schedule,
        )

        logger.info(
            f"[{self.audit_id}] LBO Complete: IRR={irr:.1%}, MOIC={moic_val:.2f}x, "
            f"Payback={payback:.1f}y"
        )

        return results

    def _project_revenues(self) -> list[float]:
        hold_period = self.config.exit_assumptions.hold_period_years
        growth_rates = self.config.company.revenue_growth_rates
        if not growth_rates:
            growth_rates = [0.05] * hold_period
        # Extend if needed
        while len(growth_rates) < hold_period:
            growth_rates.append(growth_rates[-1])

        revenues = []
        current = self.config.company.initial_revenue
        for g in growth_rates[:hold_period]:
            current *= 1 + g
            revenues.append(current)
        return revenues

    def _project_ebitdas(self) -> list[float]:
        revenues = self._project_revenues()
        margin_expansion = self.config.company.margin_expansion_bps
        if not margin_expansion:
            margin_expansion = [0] * len(revenues)
        while len(margin_expansion) < len(revenues):
            margin_expansion.append(0)

        ebitdas = []
        base_margin = self.config.company.initial_ebitda_margin
        for i, rev in enumerate(revenues):
            margin = base_margin + sum(margin_expansion[: i + 1]) / 10_000
            ebitdas.append(rev * margin)
        return ebitdas

    def _project_depreciations(self) -> list[float]:
        hold_period = self.config.exit_assumptions.hold_period_years
        base = self.config.company.initial_depreciation
        return [base] * hold_period

    def _project_capex(self) -> list[float]:
        revenues = self._project_revenues()
        pct = self.config.company.capex_pct_revenue
        return [rev * pct for rev in revenues]

    def _project_nwc(self) -> list[float]:
        revenues = self._project_revenues()
        pct = self.config.company.nwc_pct_revenue
        return [rev * pct for rev in revenues]

    def _generate_audit_id(self) -> str:
        import uuid

        return str(uuid.uuid4())[:8]

    def reset(self) -> None:
        """Reset all tranches to initial state."""
        for t in self.tranches:
            t.reset()
