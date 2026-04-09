"""Synthetic company generator — realistic profiles per sector."""

from __future__ import annotations

import numpy as np

from lbo_simulator.data.providers import DataProvider
from lbo_simulator.models.schemas import CompanyProfileSchema


# Sector-typical profiles
SECTOR_PROFILES = {
    "SaaS": {
        "initial_ebitda_margin": 0.25,
        "revenue_growth": [0.30, 0.25, 0.20, 0.18, 0.15],
        "margin_expansion_bps": [200, 150, 100, 50, 50],
        "capex_pct_revenue": 0.03,
        "nwc_pct_revenue": 0.05,
        "tax_rate": 0.21,
    },
    "Industrials": {
        "initial_ebitda_margin": 0.15,
        "revenue_growth": [0.05, 0.05, 0.04, 0.04, 0.03],
        "margin_expansion_bps": [50, 50, 25, 25, 25],
        "capex_pct_revenue": 0.08,
        "nwc_pct_revenue": 0.15,
        "tax_rate": 0.25,
    },
    "Healthcare": {
        "initial_ebitda_margin": 0.20,
        "revenue_growth": [0.10, 0.09, 0.08, 0.07, 0.06],
        "margin_expansion_bps": [100, 75, 50, 50, 25],
        "capex_pct_revenue": 0.05,
        "nwc_pct_revenue": 0.10,
        "tax_rate": 0.23,
    },
    "Consumer": {
        "initial_ebitda_margin": 0.12,
        "revenue_growth": [0.04, 0.04, 0.03, 0.03, 0.03],
        "margin_expansion_bps": [25, 25, 25, 25, 25],
        "capex_pct_revenue": 0.06,
        "nwc_pct_revenue": 0.12,
        "tax_rate": 0.25,
    },
    "TMT": {
        "initial_ebitda_margin": 0.22,
        "revenue_growth": [0.15, 0.12, 0.10, 0.08, 0.07],
        "margin_expansion_bps": [150, 100, 75, 50, 25],
        "capex_pct_revenue": 0.04,
        "nwc_pct_revenue": 0.08,
        "tax_rate": 0.22,
    },
}


class SyntheticCompanyGenerator(DataProvider):
    """Generates realistic synthetic company profiles per sector.

    Profiles are based on typical financial characteristics for each sector.
    """

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)

    def get_company_profile(
        self,
        company_name: str,
        sector: str = "SaaS",
        initial_revenue: float = 100_000_000,
    ) -> CompanyProfileSchema:
        """Generate a synthetic company profile.

        Args:
            company_name: Name of the company.
            sector: Sector (SaaS, Industrials, Healthcare, Consumer, TMT).
            initial_revenue: Initial annual revenue.

        Returns:
            CompanyProfileSchema with realistic parameters.
        """
        sector = sector if sector in SECTOR_PROFILES else "Other"
        profile = SECTOR_PROFILES.get(
            sector,
            {
                "initial_ebitda_margin": 0.15,
                "revenue_growth": [0.05] * 5,
                "margin_expansion_bps": [50] * 5,
                "capex_pct_revenue": 0.05,
                "nwc_pct_revenue": 0.10,
                "tax_rate": 0.25,
            },
        )

        # Add some randomness
        noise = self.rng.normal(0, 0.02)
        ebitda_margin = max(0.05, min(0.50, profile["initial_ebitda_margin"] + noise))

        return CompanyProfileSchema(
            name=company_name,
            sector=sector,
            initial_revenue=initial_revenue,
            initial_ebitda_margin=ebitda_margin,
            initial_depreciation=initial_revenue * 0.03,
            revenue_growth_rates=profile["revenue_growth"],
            margin_expansion_bps=profile["margin_expansion_bps"],
            capex_pct_revenue=profile["capex_pct_revenue"],
            nwc_pct_revenue=profile["nwc_pct_revenue"],
            tax_rate=profile["tax_rate"],
        )

    def get_macro_data(self) -> dict:
        """Return synthetic macro data.

        Returns:
            Dict with SOFR, GDP growth, credit spreads.
        """
        return {
            "sofr_rate": 0.053,
            "libor_proxy": 0.058,
            "gdp_growth": 0.025,
            "investment_grade_spread": 0.012,
            "high_yield_spread": 0.035,
            "leveraged_loan_spread": 0.025,
        }

    def generate_sample_portfolio(self) -> list[CompanyProfileSchema]:
        """Generate a sample portfolio of companies across sectors."""
        companies = []
        sectors = list(SECTOR_PROFILES.keys())
        revenues = [50e6, 100e6, 200e6, 500e6, 1e9]

        for i, sector in enumerate(sectors):
            name = f"Synthetic{sector}_{i+1}"
            revenue = revenues[i % len(revenues)]
            companies.append(self.get_company_profile(name, sector, revenue))

        return companies
