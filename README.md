# LBO Simulator — Leveraged Buyout Modeling & Capital Structure Optimizer

[![CI](https://github.com/vanaprosto940-sudo/lbo-simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/vanaprosto940-sudo/lbo-simulator/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Production-grade Python package for institutional LBO modeling, debt scheduling, and capital structure optimization.**

![Dashboard Preview](https://via.placeholder.com/800x400/2F5496/FFFFFF?text=LBO+Simulator+Dashboard)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🏦 **Multi-Tranche Debt Modeling** | Senior Term A/B, Mezzanine, High Yield, Revolver with amortization, cash sweep, PIK toggle |
| 💰 **Cash Flow Waterfall** | EBITDA → Taxes → Capex → ΔNWC → FCF → Debt Service → Equity Distributions |
| 📊 **Returns Analysis** | XIRR, MOIC, Payback Period, Break-even Exit Multiple |
| ⚠️ **Covenant Compliance** | Real-time leverage, FCCR, ICR testing with auto-remediation |
| ⚙️ **Capital Structure Optimizer** | Maximize IRR or minimize WACC via SLSQP solver |
| 🌐 **Interactive Dashboard** | Streamlit app with sliders, tornado charts, live debt schedule |
| 📤 **Audit-Ready Exports** | PDF reports & formatted Excel workbooks |
| 🧪 **Synthetic Data Generator** | Realistic company profiles per sector (SaaS, Industrials, Healthcare) |
| 🔄 **Deterministic Execution** | Seeded randomness, full reproducibility |

---

## 🚀 Quick Start

### Installation

```bash
# From source
git clone https://github.com/vanaprosto940-sudo/lbo-simulator.git
cd lbo-simulator
pip install -e ".[dev]"

# Or directly from pip (once published)
pip install lbo-simulator
```

### Run Your First LBO

```python
from lbo_simulator.data.synthetic import SyntheticCompanyGenerator
from lbo_simulator.models.lbo_engine import LBOEngine
from lbo_simulator.models.schemas import LBOConfigSchema

# Generate a synthetic SaaS company
gen = SyntheticCompanyGenerator(seed=42)
config = gen.get_company_profile("TechCo", sector="SaaS", initial_revenue=100_000_000)

# Build config and run
engine = LBOEngine(config)
results = engine.run()

print(f"IRR: {results.irr:.1%}")
print(f"MOIC: {results.moic:.2f}x")
```

### CLI

```bash
# Run full LBO simulation
lbo-run --config config/lbo_config.yaml --output reports/TechCo_LBO.pdf --format both

# Optimize capital structure
lbo-optimize --config config/lbo_config.yaml --objective max_irr
```

### Streamlit Dashboard

```bash
streamlit run streamlit_app/app.py
```

---

## 📖 Documentation

### Core Components

#### 1. LBO Engine (`lbo_simulator.models.lbo_engine`)

The heart of the simulator. Constructs multi-tranche debt schedules and runs year-by-year cash flow waterfalls.

```python
from lbo_simulator.models.lbo_engine import LBOEngine

engine = LBOEngine(config)
results = engine.run()

# Access results
print(results.annual_cash_flows)  # Year-by-year breakdown
print(results.debt_schedule)      # Tranche-level detail
print(results.covenant_breaches)  # Compliance flags
```

#### 2. Covenant Engine (`lbo_simulator.models.covenants`)

Tests financial covenants per period and flags breaches with severity classification.

```python
from lbo_simulator.models.covenants import CovenantEngine

covenant_engine = CovenantEngine(config.covenants)
breaches = covenant_engine.test_covenants(
    results.annual_cash_flows,
    results.debt_schedule,
    results.remaining_debt_at_exit,
)

# Get implied rating
rating = covenant_engine.get_implied_rating(
    leverage_ratio=4.5,
    interest_coverage=2.5,
)
```

#### 3. Capital Structure Optimizer (`lbo_simulator.optimization.capital_structure`)

Maximizes equity IRR or minimizes WACC under constraint boundaries.

```python
from lbo_simulator.optimization.capital_structure import CapitalStructureOptimizer

optimizer = CapitalStructureOptimizer(config)
result = optimizer.maximize_irr()

print(f"Optimal IRR: {result.optimal_irr:.1%}")
print(f"Tranche sizes: {result.optimal_tranche_sizes}")
```

---

## 📁 Project Structure

```
lbo-simulator/
├── pyproject.toml              # Package configuration
├── README.md
├── config/
│   ├── lbo_config.yaml         # Main LBO config
│   └── default_tranches.yaml   # Tranche templates
├── src/lbo_simulator/
│   ├── models/
│   │   ├── lbo_engine.py       # Core LBO simulation
│   │   ├── covenants.py        # Covenant compliance
│   │   ├── debt_tranche.py     # Tranche modeling
│   │   └── schemas.py          # Pydantic schemas
│   ├── optimization/
│   │   └── capital_structure.py # IRR/WACC optimizer
│   ├── data/
│   │   ├── synthetic.py        # Synthetic company generator
│   │   └── providers.py        # Abstract data provider
│   ├── reporting/
│   │   ├── excel_export.py     # Excel export
│   │   └── pdf_export.py       # PDF report generation
│   ├── scripts/
│   │   ├── run_lbo.py          # CLI for LBO runs
│   │   └── optimize_structure.py  # CLI for optimization
│   └── utils/
│       ├── financial_math.py   # IRR, MOIC, NPV, etc.
│       ├── config_loader.py    # YAML config loader
│       └── logging_config.py   # Audit trail logging
├── streamlit_app/
│   ├── app.py                  # Interactive dashboard
│   └── .streamlit/config.toml
├── tests/
├── examples/
└── .github/workflows/ci.yml
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src/lbo_simulator --cov-report=term-missing

# Run specific test file
pytest tests/test_lbo_engine.py -v
```

**Coverage: >85%**

---

## 🚀 Publishing to GitHub

To push this repository to GitHub:

```bash
# Make sure you have a GitHub repository created at:
# https://github.com/vanaprosto940-sudo/lbo-simulator

# Push to GitHub
git push -u origin main

# After pushing, the GitHub Actions CI will automatically:
# - Run linters (black, isort, flake8, mypy)
# - Execute all tests
# - Build the package
# - Check package distribution
```

## 📊 Configuration

All inputs are validated via Pydantic v2 schemas. Main config file:

```yaml
# config/lbo_config.yaml
company:
  name: TechCo_Synthetic
  sector: SaaS
  initial_revenue: 100000000
  initial_ebitda_margin: 0.25
  revenue_growth_rates: [0.30, 0.25, 0.20, 0.18, 0.15]
  margin_expansion_bps: [200, 150, 100, 50, 50]

sources_and_uses:
  equity_contribution: 112500000
  senior_debt: 75625000
  mezzanine_debt: 34375000
  purchase_price: 206250000

tranches:
  - name: Senior Term Loan B
    tranche_type: senior_term_b
    principal: 75625000
    interest_rate: 0.075
    amortization_rate: 0.01
    cash_sweep_rate: 0.50

exit_assumptions:
  hold_period_years: 5
  exit_ebitda_multiple: 9.5
  entry_ebitda_multiple: 8.25
```

---

## 🔧 Development

### Pre-commit Hooks

```bash
pre-commit install
```

### Code Formatting

```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/lbo_simulator/
```

---

## 📝 License

MIT License — see [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## ⚠️ Disclaimer

**This software is for educational and modeling purposes only.** It should not be relied upon for actual investment decisions. All financial projections are illustrative and based on user-defined assumptions.

---

## 📧 Author

**vanaprosto940-sudo**

Built with ❤️ for the quantitative finance community.
