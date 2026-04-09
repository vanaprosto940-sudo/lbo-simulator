"""Debt tranche modeling with amortization, PIK, and cash sweep logic."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DebtTranche:
    """Represents a single debt tranche with full amortization and interest modeling.

    Supports:
    - Linear amortization (Term A/B style)
    - Bullet payment (Mezzanine / High Yield)
    - PIK toggle (interest accrues and adds to principal)
    - Cash sweep (percentage of excess cash applied to principal)
    """

    name: str
    tranche_type: str  # senior_term_a, senior_term_b, mezzanine, high_yield, revolver
    principal: float
    interest_rate: float
    amortization_rate: float = 0.0  # fraction of original principal per year
    maturity_years: float = 1.0
    cash_sweep_rate: float = 0.0
    pik_toggle: bool = False
    pik_rate: float = 0.0
    commitment_fee: float = 0.0  # for revolver

    # Internal state
    _outstanding_balance: float = field(init=False)
    _original_principal: float = field(init=False)

    def __post_init__(self) -> None:
        self._outstanding_balance = self.principal
        self._original_principal = self.principal

    def reset(self) -> None:
        """Reset tranche to initial state."""
        self._outstanding_balance = self.principal
        self._original_principal = self.principal

    def calculate_interest(self, excess_cash: float = 0.0) -> dict:
        """Calculate interest, amortization, and optional sweep for one period.

        Returns dict with:
            - interest_paid: cash interest paid
            - interest_accrued: total interest (including PIK)
            - mandatory_amortization: required principal repayment
            - optional_sweep: extra principal from cash sweep
            - pik_accrued: PIK interest added to principal
            - ending_balance: outstanding balance after payments
        """
        # Cash interest
        cash_interest = self._outstanding_balance * self.interest_rate

        # PIK interest
        pik_interest = self._outstanding_balance * self.pik_rate if self.pik_toggle else 0.0
        total_interest = cash_interest + pik_interest

        # Mandatory amortization (linear % of original principal)
        mandatory_amort = self._original_principal * self.amortization_rate

        # Cap amortization to outstanding balance
        mandatory_amort = min(mandatory_amort, self._outstanding_balance)

        # Cash sweep from excess cash
        optional_sweep = 0.0
        if self.cash_sweep_rate > 0 and excess_cash > 0:
            optional_sweep = excess_cash * self.cash_sweep_rate
            # Cap sweep to remaining balance after mandatory amort
            remaining_after_mandatory = self._outstanding_balance - mandatory_amort
            optional_sweep = min(optional_sweep, remaining_after_mandatory)

        # Update balance
        ending_balance = self._outstanding_balance - mandatory_amort - optional_sweep

        # If PIK toggle, PIK interest accrues to principal
        if self.pik_toggle and pik_interest > 0:
            ending_balance += pik_interest

        ending_balance = max(ending_balance, 0.0)

        # Update internal state
        self._outstanding_balance = ending_balance

        return {
            "interest_paid": cash_interest,
            "interest_accrued": total_interest,
            "mandatory_amortization": mandatory_amort,
            "optional_sweep": optional_sweep,
            "pik_accrued": pik_interest if self.pik_toggle else 0.0,
            "ending_balance": ending_balance,
        }

    def is_matured(self, years_elapsed: float) -> bool:
        """Check if tranche has reached maturity."""
        return years_elapsed >= self.maturity_years

    def calculate_commitment_fee(self, undrawn_amount: float) -> float:
        """Calculate commitment fee on undrawn revolver amount."""
        if self.tranche_type == "revolver":
            return undrawn_amount * self.commitment_fee
        return 0.0

    @property
    def outstanding_balance(self) -> float:
        return self._outstanding_balance

    @property
    def paid_down(self) -> float:
        """Total principal paid down."""
        return self._original_principal - self._outstanding_balance

    def __repr__(self) -> str:
        return (
            f"DebtTranche(name={self.name!r}, type={self.tranche_type!r}, "
            f"principal={self.principal:,.0f}, balance={self._outstanding_balance:,.0f})"
        )
