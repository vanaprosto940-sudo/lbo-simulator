"""Tests for synthetic data generator."""

from __future__ import annotations

import pytest

from lbo_simulator.data.synthetic import SyntheticCompanyGenerator


class TestSyntheticCompanyGenerator:
    """Tests for synthetic company generation."""

    def test_generate_saas_company(self):
        gen = SyntheticCompanyGenerator(seed=42)
        company = gen.get_company_profile("TestSaaS", sector="SaaS", initial_revenue=100_000_000)

        assert company.name == "TestSaaS"
        assert company.sector == "SaaS"
        assert company.initial_revenue == 100_000_000
        assert 0.10 < company.initial_ebitda_margin < 0.40  # SaaS typical range
        assert len(company.revenue_growth_rates) > 0
        assert all(g > 0 for g in company.revenue_growth_rates)  # SaaS grows

    def test_generate_industrials_company(self):
        gen = SyntheticCompanyGenerator(seed=42)
        company = gen.get_company_profile("TestInd", sector="Industrials")

        assert company.sector == "Industrials"
        # Industrials have lower growth than SaaS
        assert company.revenue_growth_rates[0] < 0.10

    def test_all_sectors(self):
        """Test that all sectors can be generated."""
        gen = SyntheticCompanyGenerator(seed=42)
        sectors = ["SaaS", "Industrials", "Healthcare", "Consumer", "TMT"]

        for sector in sectors:
            company = gen.get_company_profile(f"Test{sector}", sector=sector)
            assert company.sector == sector
            assert company.initial_revenue > 0

    def test_unknown_sector_defaults(self):
        """Unknown sector should use default profile."""
        gen = SyntheticCompanyGenerator(seed=42)
        company = gen.get_company_profile("TestUnknown", sector="UnknownSector")

        assert company.sector == "Other"
        assert company.initial_revenue > 0

    def test_deterministic_with_seed(self):
        """Same seed should produce same results."""
        gen1 = SyntheticCompanyGenerator(seed=123)
        gen2 = SyntheticCompanyGenerator(seed=123)

        company1 = gen1.get_company_profile("Test", sector="SaaS", initial_revenue=100_000_000)
        company2 = gen2.get_company_profile("Test", sector="SaaS", initial_revenue=100_000_000)

        assert company1.initial_ebitda_margin == company2.initial_ebitda_margin

    def test_different_seeds_different_results(self):
        """Different seeds should (likely) produce different results."""
        gen1 = SyntheticCompanyGenerator(seed=1)
        gen2 = SyntheticCompanyGenerator(seed=999)

        company1 = gen1.get_company_profile("Test", sector="SaaS", initial_revenue=100_000_000)
        company2 = gen2.get_company_profile("Test", sector="SaaS", initial_revenue=100_000_000)

        # With different seeds, margins should differ
        assert company1.initial_ebitda_margin != company2.initial_ebitda_margin

    def test_macro_data(self):
        """Test macro data generation."""
        gen = SyntheticCompanyGenerator(seed=42)
        macro = gen.get_macro_data()

        assert "sofr_rate" in macro
        assert "libor_proxy" in macro
        assert "gdp_growth" in macro
        assert macro["sofr_rate"] > 0
        assert macro["gdp_growth"] > 0

    def test_sample_portfolio(self):
        """Test portfolio generation."""
        gen = SyntheticCompanyGenerator(seed=42)
        portfolio = gen.generate_sample_portfolio()

        assert len(portfolio) > 0
        for company in portfolio:
            assert company.initial_revenue > 0
            assert company.initial_ebitda_margin > 0
