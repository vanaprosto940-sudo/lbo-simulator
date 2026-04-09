"""Streamlit Dashboard for interactive LBO modeling."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lbo_simulator.data.synthetic import SyntheticCompanyGenerator
from lbo_simulator.models.covenants import CovenantEngine
from lbo_simulator.models.lbo_engine import LBOEngine
from lbo_simulator.models.schemas import (
    CompanyProfileSchema,
    CovenantThresholdsSchema,
    DebtTrancheSchema,
    ExitAssumptionsSchema,
    LBOConfigSchema,
    SourcesAndUsesSchema,
)
from lbo_simulator.optimization.capital_structure import CapitalStructureOptimizer
from lbo_simulator.reporting.excel_export import ExcelExporter


st.set_page_config(
    page_title="LBO Simulator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 LBO Simulator — Interactive Dashboard")
st.caption("Leveraged Buyout Modeling & Capital Structure Optimizer")


# ─── Sidebar: Inputs ───────────────────────────────────────────────
with st.sidebar:
    st.header("Deal Parameters")

    # Company
    sector = st.selectbox("Sector", ["SaaS", "Industrials", "Healthcare", "Consumer", "TMT"])
    revenue = st.number_input("Initial Revenue ($M)", min_value=10, value=100, step=10) * 1_000_000

    # Purchase
    entry_multiple = st.slider("Entry EBITDA Multiple", 4.0, 15.0, 8.0, 0.5)
    exit_multiple = st.slider("Exit EBITDA Multiple", 4.0, 15.0, 9.0, 0.5)
    hold_period = st.slider("Hold Period (years)", 3, 10, 5)

    # Leverage
    st.header("Capital Structure")
    leverage_pct = st.slider("Leverage (% of Purchase Price)", 0.2, 0.8, 0.55, 0.05)

    # Growth & Margins
    st.header("Operating Assumptions")
    revenue_growth = st.slider("Revenue Growth Rate", 0.0, 0.5, 0.10, 0.01)
    margin_expansion = st.slider("Annual Margin Expansion (bps)", 0, 300, 100, 25)


# ─── Build Configuration ───────────────────────────────────────────
@st.cache_data(ttl=60)
def build_and_run_lbo(
    sector: str,
    revenue: float,
    entry_multiple: float,
    exit_multiple: float,
    hold_period: int,
    leverage_pct: float,
    revenue_growth: float,
    margin_expansion: int,
) -> dict:
    """Build config, run LBO, covenant check, and return results."""
    # Company
    gen = SyntheticCompanyGenerator(seed=42)
    company = gen.get_company_profile("InteractiveCo", sector, revenue)
    company.revenue_growth_rates = [revenue_growth] * hold_period
    company.margin_expansion_bps = [margin_expansion] * hold_period

    # Implied EBITDA & Purchase Price
    initial_ebitda = revenue * company.initial_ebitda_margin
    purchase_price = initial_ebitda * entry_multiple

    # Capital Structure
    total_debt = purchase_price * leverage_pct
    senior_debt = total_debt * 0.55
    mezz_debt = total_debt * 0.25
    hy_debt = total_debt * 0.20
    equity = purchase_price - total_debt

    sources_uses = SourcesAndUsesSchema(
        equity_contribution=equity,
        senior_debt=senior_debt,
        mezzanine_debt=mezz_debt,
        high_yield_debt=hy_debt,
        purchase_price=purchase_price,
        transaction_fees=purchase_price * 0.01,
    )

    tranches = [
        DebtTrancheSchema(
            name="Senior Term Loan B",
            tranche_type="senior_term_b",
            principal=senior_debt,
            interest_rate=0.075,
            amortization_rate=0.01,
            maturity_years=7.0,
            cash_sweep_rate=0.50,
        ),
        DebtTrancheSchema(
            name="Mezzanine Debt",
            tranche_type="mezzanine",
            principal=mezz_debt,
            interest_rate=0.10,
            amortization_rate=0.0,
            maturity_years=float(hold_period),
            pik_toggle=True,
            pik_rate=0.02,
        ),
        DebtTrancheSchema(
            name="High Yield Bonds",
            tranche_type="high_yield",
            principal=hy_debt,
            interest_rate=0.09,
            amortization_rate=0.0,
            maturity_years=float(hold_period + 1),
        ),
    ]

    exit_assumptions = ExitAssumptionsSchema(
        hold_period_years=hold_period,
        exit_ebitda_multiple=exit_multiple,
        entry_ebitda_multiple=entry_multiple,
    )

    covenants = CovenantThresholdsSchema(
        max_total_leverage=5.5,
        min_fixed_charge_coverage=1.1,
        min_interest_coverage=1.8,
    )

    config = LBOConfigSchema(
        company=company,
        sources_and_uses=sources_uses,
        tranches=tranches,
        exit_assumptions=exit_assumptions,
        covenants=covenants,
    )

    # Run LBO
    engine = LBOEngine(config)
    results = engine.run()

    # Covenant Check
    covenant_engine = CovenantEngine(covenants)
    breaches = covenant_engine.test_covenants(
        results.annual_cash_flows,
        results.debt_schedule,
        results.remaining_debt_at_exit,
    )
    results.covenant_breaches = breaches

    return {
        "config": config,
        "results": results,
    }


# ─── Run Simulation ─────────────────────────────────────────────────
data = build_and_run_lbo(
    sector, revenue, entry_multiple, exit_multiple, hold_period,
    leverage_pct, revenue_growth, margin_expansion,
)

config = data["config"]
results = data["results"]


# ─── Main Dashboard ─────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Equity IRR", f"{results.irr:.1%}")
col2.metric("MOIC", f"{results.moic:.2f}x")
col3.metric("Payback", f"{results.payback_period_years:.1f} years")
col4.metric("Exit EV", f"${results.exit_enterprise_value / 1e6:.0f}M")

# Tabs
tab_overview, tab_cashflows, tab_debt, tab_covenants, tab_sensitivity, tab_export = st.tabs(
    ["📋 Overview", "💰 Cash Flows", "🏦 Debt Schedule", "⚠️ Covenants", "📈 Sensitivity", "📤 Export"]
)

with tab_overview:
    st.subheader("Sources & Uses")
    su = config.sources_and_uses
    sources_df = pd.DataFrame({
        "Source": ["Equity", "Senior Debt", "Mezzanine", "High Yield"],
        "Amount ($M)": [
            su.equity_contribution / 1e6,
            su.senior_debt / 1e6,
            su.mezzanine_debt / 1e6,
            su.high_yield_debt / 1e6,
        ],
    })
    fig_sources = go.Figure(data=[
        go.Pie(labels=sources_df["Source"], values=sources_df["Amount ($M)"], hole=0.4)
    ])
    fig_sources.update_layout(showlegend=False)
    st.plotly_chart(fig_sources, use_container_width=True)

    st.subheader("Annual EBITDA & Revenue Growth")
    cf_df = pd.DataFrame([
        {"Year": cf.year, "Revenue ($M)": cf.revenue / 1e6, "EBITDA ($M)": cf.ebitda / 1e6}
        for cf in results.annual_cash_flows
    ])
    fig_growth = go.Figure()
    fig_growth.add_trace(go.Bar(x=cf_df["Year"], y=cf_df["Revenue ($M)"], name="Revenue"))
    fig_growth.add_trace(go.Bar(x=cf_df["Year"], y=cf_df["EBITDA ($M)"], name="EBITDA"))
    fig_growth.update_layout(barmode="group")
    st.plotly_chart(fig_growth, use_container_width=True)


with tab_cashflows:
    st.subheader("Cash Flow Waterfall")
    cf_data = []
    for cf in results.annual_cash_flows:
        cf_data.append({
            "Year": cf.year,
            "Unlevered FCF ($M)": cf.unlevered_fcf / 1e6,
            "Debt Service ($M)": (cf.mandatory_amortization + cf.optional_sweep) / 1e6,
            "Equity Distribution ($M)": cf.equity_distribution / 1e6,
        })
    cf_df = pd.DataFrame(cf_data)
    st.dataframe(cf_df, use_container_width=True)

    fig_waterfall = go.Figure()
    fig_waterfall.add_trace(go.Bar(x=cf_df["Year"], y=cf_df["Unlevered FCF ($M)"], name="Unlevered FCF"))
    fig_waterfall.add_trace(go.Bar(x=cf_df["Year"], y=cf_df["Debt Service ($M)"], name="Debt Service"))
    fig_waterfall.add_trace(go.Bar(x=cf_df["Year"], y=cf_df["Equity Distribution ($M)"], name="Equity Dist"))
    fig_waterfall.update_layout(barmode="group")
    st.plotly_chart(fig_waterfall, use_container_width=True)


with tab_debt:
    st.subheader("Debt Schedule by Tranche")
    debt_df = pd.DataFrame([
        {
            "Year": ds.year,
            "Tranche": ds.tranche_name,
            "Beg Balance ($M)": ds.beginning_balance / 1e6,
            "Interest ($M)": ds.interest_paid / 1e6,
            "Mandatory Amort ($M)": ds.mandatory_amortization / 1e6,
            "End Balance ($M)": ds.ending_balance / 1e6,
        }
        for ds in results.debt_schedule
    ])
    st.dataframe(debt_df, use_container_width=True)


with tab_covenants:
    if results.covenant_breaches:
        st.warning(f"⚠️ {len(results.covenant_breaches)} covenant breach(es) detected!")
        breach_df = pd.DataFrame([
            {
                "Year": b.year,
                "Covenant": b.covenant_name,
                "Actual": b.actual_value,
                "Threshold": b.threshold_value,
                "Severity": b.severity,
                "Remediation": b.remediation_applied,
            }
            for b in results.covenant_breaches
        ])
        st.dataframe(breach_df, use_container_width=True)
    else:
        st.success("✅ All covenants compliant throughout hold period")


with tab_sensitivity:
    st.subheader("IRR Sensitivity to Exit Multiple & Leverage")

    opt = CapitalStructureOptimizer(config)
    sensitivity = opt._run_sensitivity_analysis(n_points=7)
    sens_df = pd.DataFrame(sensitivity).dropna()

    if not sens_df.empty:
        fig_sens = go.Figure()
        fig_sens.add_trace(
            go.Scatter(x=sens_df["leverage_shift_pct"], y=sens_df["irr"] * 100, mode="lines+markers", name="IRR")
        )
        fig_sens.update_layout(
            xaxis_title="Leverage Shift (%)",
            yaxis_title="IRR (%)",
            showlegend=False,
        )
        st.plotly_chart(fig_sens, use_container_width=True)


with tab_export:
    st.subheader("Export Reports")
    if st.button("📥 Download Excel"):
        exporter = ExcelExporter(config, results)
        output_path = exporter.export("reports/LBO_Report.xlsx")
        with open(output_path, "rb") as f:
            st.download_button("Download Excel", f, file_name="LBO_Report.xlsx")
        st.success(f"Excel saved to `{output_path}`")
