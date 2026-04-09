"""Tests for configuration loader."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lbo_simulator.utils.config_loader import (
    load_config,
    load_config_from_dict,
    save_config,
)


class TestConfigLoader:
    """Tests for YAML config loading."""

    def test_load_config_from_dict(self, sample_config):
        """Test loading config from dictionary."""
        config_dict = sample_config.model_dump()
        loaded = load_config_from_dict(config_dict)

        assert loaded.company.name == sample_config.company.name
        assert loaded.sources_and_uses.equity_contribution == pytest.approx(
            sample_config.sources_and_uses.equity_contribution
        )

    def test_load_config_from_yaml(self, tmp_path: Path):
        """Test loading config from YAML file."""
        # Create a minimal config
        config_dict = {
            "company": {
                "name": "TestCo",
                "sector": "SaaS",
                "initial_revenue": 100_000_000,
                "initial_ebitda_margin": 0.25,
                "initial_depreciation": 3_000_000,
                "revenue_growth_rates": [0.10, 0.08, 0.06, 0.05, 0.04],
                "margin_expansion_bps": [100, 75, 50, 25, 25],
                "capex_pct_revenue": 0.03,
                "nwc_pct_revenue": 0.05,
                "tax_rate": 0.21,
            },
            "sources_and_uses": {
                "equity_contribution": 100_000_000,
                "senior_debt": 60_000_000,
                "purchase_price": 160_000_000,
            },
            "tranches": [
                {
                    "name": "Senior",
                    "tranche_type": "senior_term_b",
                    "principal": 60_000_000,
                    "interest_rate": 0.075,
                    "amortization_rate": 0.01,
                    "maturity_years": 7.0,
                }
            ],
            "exit_assumptions": {
                "hold_period_years": 5,
                "exit_ebitda_multiple": 9.0,
                "entry_ebitda_multiple": 8.0,
            },
        }

        yaml_path = tmp_path / "test_config.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(config_dict, f)

        config = load_config(yaml_path)
        assert config.company.name == "TestCo"
        assert len(config.tranches) == 1

    def test_save_and_reload_config(self, sample_config, tmp_path: Path):
        """Test saving config to YAML and reloading."""
        output_path = tmp_path / "saved_config.yaml"
        save_config(sample_config, output_path)

        assert output_path.exists()
        reloaded = load_config(output_path)

        assert reloaded.company.name == sample_config.company.name
        assert reloaded.exit_assumptions.hold_period_years == sample_config.exit_assumptions.hold_period_years

    def test_file_not_found(self):
        """Test error on missing config file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")
