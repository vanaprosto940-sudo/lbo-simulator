"""PDF report generator using WeasyPrint."""

from __future__ import annotations

from pathlib import Path

from lbo_simulator.models.schemas import LBOConfigSchema, LBOResultsSchema


class PDFExporter:
    """Exports LBO results to audit-ready PDF report."""

    def __init__(self, config: LBOConfigSchema, results: LBOResultsSchema) -> None:
        self.config = config
        self.results = results

    def export(self, output_path: str | Path) -> Path:
        """Generate and save PDF report.

        Args:
            output_path: Output file path.

        Returns:
            Path to saved PDF.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html = self._build_html()

        try:
            from weasyprint import HTML

            HTML(string=html).write_pdf(str(output_path))
        except (ImportError, OSError):
            # WeasyPrint requires GTK libraries which may not be installed
            # Fallback: save as HTML instead
            output_path = output_path.with_suffix(".html")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            print("WeasyPrint unavailable, saved as HTML instead.")
            print(
                "   To enable PDF on Windows, install GTK: "
                "https://github.com/tschoonj/GTK-for-Windows-Runtime-Installer"
            )

        return output_path

    def _build_html(self) -> str:
        """Build HTML content for PDF."""
        company = self.config.company
        r = self.results

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{
                    size: A4;
                    margin: 2cm;
                    @bottom-right {{
                        content: "Page " counter(page) " of " counter(pages);
                        font-size: 9pt;
                        color: #666;
                    }}
                }}
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.5;
                    color: #333;
                }}
                h1 {{
                    color: #2F5496;
                    font-size: 22pt;
                    border-bottom: 3px solid #2F5496;
                    padding-bottom: 8px;
                }}
                h2 {{
                    color: #2F5496;
                    font-size: 16pt;
                    margin-top: 24px;
                }}
                .metrics {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                    margin: 16px 0;
                }}
                .metric {{
                    background: #f0f4f8;
                    padding: 12px 16px;
                    border-radius: 6px;
                    border-left: 4px solid #2F5496;
                }}
                .metric-label {{
                    font-size: 9pt;
                    color: #666;
                    text-transform: uppercase;
                }}
                .metric-value {{
                    font-size: 18pt;
                    font-weight: bold;
                    color: #2F5496;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 12px 0;
                    font-size: 9pt;
                }}
                th {{
                    background: #2F5496;
                    color: white;
                    padding: 8px;
                    text-align: right;
                }}
                th:first-child {{
                    text-align: left;
                }}
                td {{
                    padding: 6px 8px;
                    border-bottom: 1px solid #e0e0e0;
                    text-align: right;
                }}
                td:first-child {{
                    text-align: left;
                }}
                tr:nth-child(even) {{
                    background: #f8f8f8;
                }}
                .breach-warning {{
                    background: #fff3cd !important;
                }}
                .breach-critical {{
                    background: #f8d7da !important;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 12px;
                    border-top: 1px solid #ccc;
                    font-size: 8pt;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <h1>LBO Simulation Report</h1>
            <p><strong>Company:</strong> {company.name} | <strong>Sector:</strong> {company.sector}</p>
            <p><strong>Entry Multiple:</strong> {self.config.exit_assumptions.entry_ebitda_multiple:.1f}x |
               <strong>Exit Multiple:</strong> {self.config.exit_assumptions.exit_ebitda_multiple:.1f}x |
               <strong>Hold Period:</strong> {self.config.exit_assumptions.hold_period_years} years</p>

            <h2>Key Returns</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">Equity IRR</div>
                    <div class="metric-value">{r.irr:.1%}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">MOIC</div>
                    <div class="metric-value">{r.moic:.2f}x</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Payback Period</div>
                    <div class="metric-value">{r.payback_period_years:.1f} years</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Exit Equity Value</div>
                    <div class="metric-value">${r.exit_equity_value:,.0f}</div>
                </div>
            </div>

            <h2>Sources & Uses</h2>
            <table>
                <tr><th>Source</th><th>Amount</th></tr>
                <tr><td>Equity Contribution</td><td>${self.config.sources_and_uses.equity_contribution:,.0f}</td></tr>
                <tr><td>Senior Debt</td><td>${self.config.sources_and_uses.senior_debt:,.0f}</td></tr>
                <tr><td>Mezzanine Debt</td><td>${self.config.sources_and_uses.mezzanine_debt:,.0f}</td></tr>
                <tr><td>High Yield Debt</td><td>${self.config.sources_and_uses.high_yield_debt:,.0f}</td></tr>
                <tr>
                    <td><strong>Total Sources</strong></td>
                    <td><strong>${self.config.sources_and_uses.total_sources:,.0f}</strong></td>
                </tr>
            </table>

            <h2>Annual Cash Flows</h2>
            <table>
                <tr>
                    <th>Year</th><th>Revenue</th><th>EBITDA</th><th>Unlevered FCF</th>
                    <th>Debt Service</th><th>Equity Dist.</th>
                </tr>
        """

        for cf in r.annual_cash_flows:
            debt_service = cf.mandatory_amortization + cf.optional_sweep
            html += f"""
                <tr>
                    <td>{cf.year}</td>
                    <td>${cf.revenue:,.0f}</td>
                    <td>${cf.ebitda:,.0f}</td>
                    <td>${cf.unlevered_fcf:,.0f}</td>
                    <td>${debt_service:,.0f}</td>
                    <td>${cf.equity_distribution:,.0f}</td>
                </tr>
            """

        html += """
            </table>

            <h2>Covenant Compliance</h2>
        """

        if not r.covenant_breaches:
            html += (
                '<p style="color: #006400; font-weight: bold;">✓ No covenant breaches detected</p>'
            )
        else:
            html += "<table><tr><th>Year</th><th>Covenant</th><th>Actual</th><th>Threshold</th><th>Severity</th></tr>"
            for b in r.covenant_breaches:
                row_class = "breach-critical" if b.severity == "critical" else "breach-warning"
                html += f"""
                    <tr class="{row_class}">
                        <td>{b.year}</td>
                        <td>{b.covenant_name}</td>
                        <td>{b.actual_value:.2f}</td>
                        <td>{b.threshold_value:.2f}</td>
                        <td>{b.severity.upper()}</td>
                    </tr>
                """
            html += "</table>"

        html += f"""
            <h2>Debt Summary</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Interest Paid</td><td>${r.total_interest_paid:,.0f}</td></tr>
                <tr><td>Total Principal Repaid</td><td>${r.total_principal_repaid:,.0f}</td></tr>
                <tr><td>Remaining Debt at Exit</td><td>${r.remaining_debt_at_exit:,.0f}</td></tr>
            </table>

            <div class="footer">
                <p>
                    Generated by LBO Simulator v0.1.0 |
                    Data Version: {self.config.data_version} |
                    Audit ID: {getattr(self, '_audit_id', 'N/A')}
                </p>
                <p>
                    This report is for illustrative purposes only
                    and should not be relied upon for investment decisions.
                </p>
            </div>
        </body>
        </html>
        """

        return html
