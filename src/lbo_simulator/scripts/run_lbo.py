"""CLI script for running LBO simulations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lbo_simulator.models.covenants import CovenantEngine
from lbo_simulator.models.lbo_engine import LBOEngine
from lbo_simulator.reporting.excel_export import ExcelExporter
from lbo_simulator.reporting.pdf_export import PDFExporter
from lbo_simulator.utils.config_loader import load_config
from lbo_simulator.utils.logging_config import setup_logging


def main() -> None:
    """Run LBO simulation from CLI."""
    parser = argparse.ArgumentParser(description="LBO Simulator CLI")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config/lbo_config.yaml",
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--company",
        type=str,
        default=None,
        help="Override company name (uses synthetic profile)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["full", "quick", "optimize"],
        default="full",
        help="Simulation mode",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output report path (PDF or Excel)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["pdf", "excel", "both"],
        default="excel",
        help="Export format",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
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

    if args.company:
        config.company.name = args.company

    print(f"\n{'='*60}")
    print(f"LBO Simulation: {config.company.name}")
    print(f"Audit ID: {audit_id}")
    print(f"{'='*60}\n")

    # Run LBO
    engine = LBOEngine(config)
    results = engine.run()

    # Covenant check
    covenant_engine = CovenantEngine(config.covenants)
    breaches = covenant_engine.test_covenants(
        results.annual_cash_flows,
        results.debt_schedule,
        results.remaining_debt_at_exit,
    )
    results.covenant_breaches = breaches

    # Print summary
    print("\nResults Summary:")
    print(f"  Equity IRR:        {results.irr:.1%}")
    print(f"  MOIC:              {results.moic:.2f}x")
    print(f"  Payback Period:    {results.payback_period_years:.1f} years")
    print(f"  Exit Enterprise Value: ${results.exit_enterprise_value / 1e6:.1f}M")
    print(f"  Exit Equity Value:     ${results.exit_equity_value / 1e6:.1f}M")
    print(f"  Remaining Debt:        ${results.remaining_debt_at_exit / 1e6:.1f}M")
    print(f"  Total Interest Paid:   ${results.total_interest_paid / 1e6:.1f}M")

    if breaches:
        print(f"\n⚠️  Covenant Breaches: {len(breaches)}")
        for b in breaches:
            print(
                f"  Year {b}: {b.covenant_name} = {b.actual_value:.2f} vs {b.threshold_value:.2f} ({b.severity})"
            )
    else:
        print("\nAll covenants compliant")

    # Export
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if args.format in ("pdf", "both"):
            pdf_exporter = PDFExporter(config, results)
            pdf_path = output_path.with_suffix(".pdf")
            pdf_exporter.export(pdf_path)
            print(f"\n📄 PDF report: {pdf_path}")

        if args.format in ("excel", "both"):
            excel_exporter = ExcelExporter(config, results)
            excel_path = output_path.with_suffix(".xlsx")
            excel_exporter.export(excel_path)
            print(f"📊 Excel report: {excel_path}")

    print(f"\n{'='*60}")
    print("Simulation complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
