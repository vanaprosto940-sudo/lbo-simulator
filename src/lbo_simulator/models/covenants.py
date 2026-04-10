"""Covenant compliance engine — detects breaches and triggers remediation."""

from __future__ import annotations

from loguru import logger

from lbo_simulator.models.schemas import (
    AnnualCashFlowSchema,
    CovenantBreachSchema,
    CovenantThresholdsSchema,
    DebtScheduleYearSchema,
)


class CovenantEngine:
    """Tests financial covenants per period and flags breaches.

    Covenants tested:
    - Total Leverage Ratio: Net Debt / LTM EBITDA
    - Fixed Charge Coverage Ratio: EBITDA / (Interest + Mandatory Amort + Taxes)
    - Interest Coverage Ratio: EBITDA / Interest

    Auto-remediation:
    - PIK switch (if available)
    - Cash holdback (block distributions)
    - Dividend block
    """

    def __init__(self, thresholds: CovenantThresholdsSchema) -> None:
        self.thresholds = thresholds

    def test_covenants(
        self,
        cash_flows: list[AnnualCashFlowSchema],
        debt_schedule: list[DebtScheduleYearSchema],
        remaining_debt_at_exit: float,
    ) -> list[CovenantBreachSchema]:
        """Test all covenants for all periods.

        Args:
            cash_flows: Annual cash flow projections.
            debt_schedule: Debt schedule by tranche and year.
            remaining_debt_at_exit: Outstanding debt at exit.

        Returns:
            List of covenant breaches found.
        """
        breaches: list[CovenantBreachSchema] = []

        # Aggregate debt schedule by year
        debt_by_year = self._aggregate_debt_by_year(debt_schedule)

        for cf in cash_flows:
            year = cf.year
            year_debt = debt_by_year.get(year, {})

            # Net debt = total outstanding debt (simplified: no cash offset)
            net_debt = year_debt.get("ending_balance", 0.0)
            if year == len(cash_flows):
                net_debt = remaining_debt_at_exit

            ebitda = cf.ebitda
            interest = year_debt.get("interest_paid", 0.0)
            mandatory_amort = year_debt.get("mandatory_amortization", 0.0)
            taxes = cf.taxes

            # 1. Total Leverage Ratio
            if ebitda > 0:
                leverage_ratio = net_debt / ebitda
                if leverage_ratio > self.thresholds.max_total_leverage:
                    severity = self._classify_severity(
                        leverage_ratio, self.thresholds.max_total_leverage
                    )
                    breach = CovenantBreachSchema(
                        year=year,
                        covenant_name="Total Leverage Ratio",
                        actual_value=leverage_ratio,
                        threshold_value=self.thresholds.max_total_leverage,
                        severity=severity,  # type: ignore[arg-type]
                        remediation_applied=self._suggest_remediation("leverage"),
                    )
                    breaches.append(breach)
                    logger.warning(
                        f"Year {year}: Leverage breach {leverage_ratio:.2f}x vs "
                        f"{self.thresholds.max_total_leverage:.2f}x max"
                    )

            # 2. Fixed Charge Coverage Ratio
            fixed_charges = interest + mandatory_amort + taxes
            if fixed_charges > 0 and ebitda > 0:
                fccr = ebitda / fixed_charges
                if fccr < self.thresholds.min_fixed_charge_coverage:
                    severity = self._classify_severity(
                        self.thresholds.min_fixed_charge_coverage, fccr, inverse=True
                    )
                    breach = CovenantBreachSchema(
                        year=year,
                        covenant_name="Fixed Charge Coverage",
                        actual_value=fccr,
                        threshold_value=self.thresholds.min_fixed_charge_coverage,
                        severity=severity,  # type: ignore[arg-type]
                        remediation_applied=self._suggest_remediation("fccr"),
                    )
                    breaches.append(breach)
                    logger.warning(
                        f"Year {year}: FCCR breach {fccr:.2f}x vs "
                        f"{self.thresholds.min_fixed_charge_coverage:.2f}x min"
                    )

            # 3. Interest Coverage Ratio
            if interest > 0 and ebitda > 0:
                icr = ebitda / interest
                if icr < self.thresholds.min_interest_coverage:
                    severity = self._classify_severity(
                        self.thresholds.min_interest_coverage, icr, inverse=True
                    )
                    breach = CovenantBreachSchema(
                        year=year,
                        covenant_name="Interest Coverage",
                        actual_value=icr,
                        threshold_value=self.thresholds.min_interest_coverage,
                        severity=severity,  # type: ignore[arg-type]
                        remediation_applied=self._suggest_remediation("icr"),
                    )
                    breaches.append(breach)
                    logger.warning(
                        f"Year {year}: ICR breach {icr:.2f}x vs "
                        f"{self.thresholds.min_interest_coverage:.2f}x min"
                    )

        return breaches

    def _aggregate_debt_by_year(
        self, debt_schedule: list[DebtScheduleYearSchema]
    ) -> dict[int, dict]:
        """Aggregate debt schedule entries by year."""
        by_year: dict[int, dict] = {}
        for entry in debt_schedule:
            if entry.year not in by_year:
                by_year[entry.year] = {
                    "interest_paid": 0.0,
                    "mandatory_amortization": 0.0,
                    "optional_sweep": 0.0,
                    "pik_accrued": 0.0,
                    "ending_balance": 0.0,
                }
            by_year[entry.year]["interest_paid"] += entry.interest_paid
            by_year[entry.year]["mandatory_amortization"] += entry.mandatory_amortization
            by_year[entry.year]["optional_sweep"] += entry.optional_sweep
            by_year[entry.year]["pik_accrued"] += entry.pik_accrued
            by_year[entry.year]["ending_balance"] += entry.ending_balance
        return by_year

    def _classify_severity(self, actual: float, threshold: float, inverse: bool = False) -> str:
        """Classify breach severity.

        'warning': within 10% of threshold
        'breach': within 20% of threshold
        'critical': beyond 20%
        """
        if inverse:
            ratio = threshold / actual if actual > 0 else float("inf")
        else:
            ratio = actual / threshold if threshold > 0 else float("inf")

        if ratio < 1.1:
            return "warning"
        elif ratio < 1.2:
            return "breach"
        else:
            return "critical"

    def _suggest_remediation(self, covenant_type: str) -> str:
        """Suggest remediation action for the breach type."""
        remediations = {
            "leverage": "Block dividends, increase cash sweep, consider PIK toggle",
            "fccr": "Reduce mandatory amortization via refinancing, switch to PIK",
            "icr": "Negotiate lower spread, PIK toggle, or equity cure",
        }
        return remediations.get(covenant_type, "Review capital structure")

    def get_implied_rating(self, leverage_ratio: float, interest_coverage: float) -> str:
        """Proxy rating based on leverage and coverage ratios.

        Maps to implied S&P/Fitch bands.
        """
        if leverage_ratio < 2.0 and interest_coverage > 5.0:
            return "BBB"
        elif leverage_ratio < 3.0 and interest_coverage > 4.0:
            return "BB+"
        elif leverage_ratio < 4.0 and interest_coverage > 3.0:
            return "BB"
        elif leverage_ratio < 5.0 and interest_coverage > 2.0:
            return "BB-"
        elif leverage_ratio < 6.0 and interest_coverage > 1.5:
            return "B+"
        elif leverage_ratio < 7.0 and interest_coverage > 1.2:
            return "B"
        else:
            return "CCC or below"
