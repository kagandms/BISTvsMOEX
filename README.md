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
- **Real-return comparison:** curated monthly CPI snapshot from `config.yaml`
- **Market-cap comparison:** curated snapshot from `config.yaml` rather than a live provider feed

Curated snapshot metadata, source URLs, coverage, and methodology notes are declared in
`config.yaml`. Snapshot values are intentionally separated from live providers so the
dashboard can fail closed instead of mixing live prices with stale reference data.

## Snapshot Governance

Curated values are treated as reproducible reference data, not live quotes:

- market-cap values are stored in USD billions, rounded to one decimal place, and timestamped in `market_cap_metadata`,
- CPI values are official month-over-month rates compounded into a local CPI index at runtime,
- the snapshot source links and access date are versioned in `config.yaml`,
- numerical claims should be refreshed before a new public release or LinkedIn post that emphasizes current valuations.

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

This project is tested with **Python 3.13.9**. Any Python 3.13 patch release should work.
If your machine does not expose a `python3.13` command, install Python 3.13 with your
preferred version manager (`pyenv`, `uv`, Homebrew, or the official installer), or use
the Docker path below.

```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at [http://localhost:8501](http://localhost:8501).
Supported baseline: **Python 3.13**.

Quick interpreter check:

```bash
python3.13 --version
```

## Development / CI Installation

```bash
python3.13 -m venv venv
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
| `BM_TIMEOUT` | Upstream request timeout in seconds. Allowed range: `1-120`. | `15` |
| `BM_MOEX_DELAY` | Expected MOEX publication lag in days. Allowed range: `1-14`. | `2` |
| `BM_SENTRY_TRACE_SAMPLE_RATE` | Optional Sentry trace sampling rate. Allowed range: `0.0-1.0`. | `0.1` |
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
- Real comparison uses the curated shared CPI window and stops at the latest safely covered month instead of extrapolating unpublished inflation data.
- The current curated CPI coverage in `config.yaml` ends at **2026-03**, so later end dates surface a partial/unavailable real-return state by design.
- Market-cap cards use the curated snapshot date declared in `config.yaml`; they should be treated as reference metadata, not live quotes.
- Curated CPI and market-cap snapshots include source metadata in `config.yaml`; refresh them before publishing updated numerical claims.
- Unsafe comparisons fail closed and render an unavailable state instead of `NaN`, `0.0`, or raw upstream errors.

## License

Licensed under the MIT License. See `LICENSE` for details.

## Disclaimer

This application is for educational and comparative analysis purposes only. It does not constitute investment advice.
