"""CLI script for optimizing capital structure."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lbo_simulator.models.covenants import CovenantEngine
from lbo_simulator.models.lbo_engine import LBOEngine
from lbo_simulator.optimization.capital_structure import CapitalStructureOptimizer
from lbo_simulator.utils.config_loader import load_config
from lbo_simulator.utils.logging_config import setup_logging


def main() -> None:
    """Run capital structure optimization from CLI."""
    parser = argparse.ArgumentParser(description="LBO Capital Structure Optimizer")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config/lbo_config.yaml",
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--objective",
        type=str,
        choices=["max_irr", "min_wacc"],
        default="max_irr",
        help="Optimization objective",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Setup logging
    audit_id = setup_logging()

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(config_path)

    print(f"\n{'='*60}")
    print(f"Capital Structure Optimization: {config.company.name}")
    print(f"Objective: {args.objective}")
    print(f"Audit ID: {audit_id}")
    print(f"{'='*60}\n")

    # Run base case
    print("Running base case...")
    base_engine = LBOEngine(config)
    base_results = base_engine.run()

    covenant_engine = CovenantEngine(config.covenants)
    base_breaches = covenant_engine.test_covenants(
        base_results.annual_cash_flows,
        base_results.debt_schedule,
        base_results.remaining_debt_at_exit,
    )

    print(f"\n📊 Base Case:")
    print(f"  Equity IRR:  {base_results.irr:.1%}")
    print(f"  MOIC:        {base_results.moic:.2f}x")
    if base_breaches:
        print(f"  ⚠️  Breaches: {len(base_breaches)}")
    else:
        print(f"  ✅ Covenants: Compliant")

    # Optimize
    print(f"\n⚙️  Optimizing capital structure...")
    optimizer = CapitalStructureOptimizer(config)

    if args.objective == "max_irr":
        result = optimizer.maximize_irr()
    else:
        result = optimizer.minimize_wacc()

    # Print results
    print(f"\n{'='*60}")
    print("OPTIMIZATION RESULTS")
    print(f"{'='*60}")

    print(f"\n  Success: {result.success}")
    print(f"  Message: {result.message}")
    print(f"\n  Optimal IRR:  {result.optimal_irr:.1%}")
    print(f"  Optimal MOIC: {result.optimal_moic:.2f}x")
    print(f"  Blended WACC: {result.blended_cost_of_capital:.1%}")

    print(f"\n  Optimal Tranche Sizes:")
    for name, size in result.optimal_tranche_sizes.items():
        print(f"    {name}: ${size / 1e6:.1f}M")

    print(f"\n  Constraint Binding:")
    for constraint, is_binding in result.constraint_binding_report.items():
        status = "BINDING" if is_binding else "Not binding"
        print(f"    {constraint}: {status}")

    print(f"\n  Sensitivity Analysis:")
    print(f"    {'Leverage Shift':>15} | {'IRR':>8} | {'MOIC':>8}")
    print(f"    {'-'*15}-+-{'-'*8}-+-{'-'*8}")
    for row in result.sensitivity_table[:5]:
        print(
            f"    {row['leverage_shift_pct']:>14.0f}% | "
            f"{row['irr']:>7.1%} | "
            f"{row['moic']:>7.2f}x"
        )

    irr_improvement = result.optimal_irr - base_results.irr
    print(f"\n  IRR Improvement: {irr_improvement:+.1%}")

    print(f"\n{'='*60}")
    print("Optimization complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
