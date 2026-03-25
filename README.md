# 🌉 The Eurasian Bridge: BIST vs. MOEX Analyzer

Multilingual comparative analytics dashboard for sector leaders in Turkey and Russia.

This application compares BIST and MOEX equities through a single Streamlit interface, normalizes cross-market data, and presents return/risk metrics in English, Turkish, and Russian.

## What The Application Does

- fetches BIST prices from Yahoo Finance,
- fetches MOEX prices from the official MOEX ISS API,
- optionally converts both assets into USD,
- computes period change, YTD, volatility, Sharpe, drawdown, CAGR, and correlation,
- renders a fail-closed dashboard that hides unsafe comparisons instead of showing misleading numbers.

## Current Data Sources

- **BIST source:** [Yahoo Finance](https://finance.yahoo.com/)
- **MOEX source:** [MOEX ISS API](https://iss.moex.com/)
- **FX conversion:** Yahoo Finance FX series aligned to the shared trading window
- **Market-cap comparison:** curated snapshot from `config.yaml`

## Architecture

```text
BistvsMoex/
├── app.py                    # Streamlit entry point
├── config.yaml               # Runtime configuration, sectors, events, metadata
├── src/
│   ├── analysis.py           # Financial calculations with fail-closed semantics
│   ├── config.py             # Config loading and translations
│   ├── dashboard.py          # Dashboard orchestration helpers
│   ├── data.py               # Upstream fetchers and typed data contracts
│   ├── exceptions.py         # Domain exceptions
│   ├── models.py             # Shared typed result models
│   └── ui.py                 # Reusable rendering helpers
├── scripts/                  # Manual diagnostics and verification scripts
└── tests/                    # Offline test suite + optional live-provider tests
```

## Runtime Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at [http://localhost:8501](http://localhost:8501).

## Development / CI Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

Quality gates:

```bash
ruff check .
mypy app.py src
pytest tests
pip-audit -r requirements.txt
```

By default, `pytest` excludes live-provider tests and runs only the deterministic offline suite.

Run optional live tests explicitly:

```bash
pytest -m live
```

## Docker

Build:

```bash
docker build -t bist-vs-moex .
```

Run:

```bash
docker run --rm -p 8501:8501 \
  -e PORT=8501 \
  -e BM_TIMEOUT=15 \
  -e BM_MOEX_DELAY=2 \
  bist-vs-moex
```

## Environment Contract

Supported application overrides:

| Variable | Purpose | Default |
|----------|---------|---------|
| `BM_TIMEOUT` | Upstream request timeout in seconds | `15` |
| `BM_MOEX_DELAY` | Expected MOEX publication lag in days | `2` |
| `PORT` | Streamlit server port in Docker/server mode | `8501` |

## Manual Diagnostics

Scripts were moved under `scripts/` and are not part of the default test suite.

Examples:

```bash
python scripts/debug_data_sources.py
python scripts/debug_ytd.py
python scripts/verify_data_integrity.py
```

## Production Behaviour

- Invalid or unsupported windows are rejected explicitly.
- YTD is tied to the selected end-year, not the machine’s current year.
- USD comparison uses only the shared FX-covered overlap.
- Unsafe comparisons fail closed and render an unavailable state instead of `NaN`, `0.0`, or raw upstream errors.

## Disclaimer

This application is for educational and comparative analysis purposes only. It does not constitute investment advice.
