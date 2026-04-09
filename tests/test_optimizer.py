"""Tests for Capital Structure Optimizer."""

from __future__ import annotations

import pytest

from lbo_simulator.optimization.capital_structure import CapitalStructureOptimizer


class TestCapitalStructureOptimizer:
    """Tests for capital structure optimization."""

    def test_optimizer_initialization(self, sample_config):
        """Test optimizer creation."""
        optimizer = CapitalStructureOptimizer(sample_config)
        assert optimizer.debt_capacity > 0
        assert optimizer.sector_multiplier > 0

    def test_sector_multipliers(self, sample_config):
        """Test sector multiplier lookup."""
        optimizer = CapitalStructureOptimizer(sample_config)
        assert optimizer.SECTOR_MULTIPLIERS["SaaS"] == 7.0
        assert optimizer.SECTOR_MULTIPLIERS["Industrials"] == 5.0

    def test_maximize_irr(self, sample_config):
        """Test IRR maximization runs without error."""
        optimizer = CapitalStructureOptimizer(sample_config)
        result = optimizer.maximize_irr(max_iterations=20)

        assert result.optimal_irr > 0
        assert len(result.optimal_tranche_sizes) > 0
        assert len(result.sensitivity_table) > 0

    def test_optimal_tranche_sizes_positive(self, sample_config):
        """Optimal tranche sizes should be non-negative."""
        optimizer = CapitalStructureOptimizer(sample_config)
        result = optimizer.maximize_irr(max_iterations=15)

        for name, size in result.optimal_tranche_sizes.items():
            assert size >= 0, f"{name} has negative size: {size}"

    def test_sensitivity_analysis(self, sample_config):
        """Test sensitivity analysis generation."""
        optimizer = CapitalStructureOptimizer(sample_config)
        sensitivity = optimizer._run_sensitivity_analysis(n_points=5)

        assert len(sensitivity) == 5
        for row in sensitivity:
            assert "leverage_shift_pct" in row
            assert "irr" in row
            assert "moic" in row

    def test_wacc_calculation(self, sample_config):
        """Test WACC calculation."""
        optimizer = CapitalStructureOptimizer(sample_config)
        from lbo_simulator.models.lbo_engine import LBOEngine

        engine = LBOEngine(sample_config)
        results = engine.run()

        wacc_val = optimizer._calculate_wacc(sample_config, results)
        assert wacc_val > 0
        assert wacc_val < 1.0  # Should be reasonable

    def test_constraint_binding_report(self, sample_config):
        """Test constraint binding report generation."""
        optimizer = CapitalStructureOptimizer(sample_config)
        import numpy as np

        x = np.array([t.principal * 0.5 for t in sample_config.tranches])
        report = optimizer._check_constraint_binding(x)

        assert "debt_capacity" in report
        assert "tranche_limits" in report
        assert "non_negative" in report

    def test_build_config_from_weights(self, sample_config):
        """Test config reconstruction from weights."""
        optimizer = CapitalStructureOptimizer(sample_config)
        import numpy as np

        weights = np.array([t.principal * 0.6 for t in sample_config.tranches])
        new_config = optimizer._build_config_from_weights(weights)

        # New config should have adjusted tranche sizes
        for i, t in enumerate(new_config.tranches):
            assert t.principal == pytest.approx(weights[i], rel=0.01)
