# 🌉 The Eurasian Bridge: BIST vs. MOEX Analyzer

**A multilingual financial analytics project built to compare sector leaders in Turkey and Russia through one reproducible interface.**

This project was designed as a portfolio piece at the intersection of Management Information Systems and Economics. Its purpose is not to predict prices or simulate trading, but to demonstrate the ability to:

- combine heterogeneous financial data sources,
- normalize cross-market comparisons,
- present results in a clear decision-oriented dashboard,
- and communicate findings across English, Turkish, and Russian.

## Project Thesis

How can sector leaders from Borsa Istanbul and the Moscow Exchange be compared fairly when they trade in different currencies, under different market calendars, and under different macroeconomic conditions?

The application answers that question through a compact analytics workflow:

- fetch daily close data from separate upstream providers,
- normalize series to a common base,
- compute cross-market risk and return metrics,
- annotate analysis with macro events,
- and present the results in a multilingual dashboard.

## What The Application Demonstrates

- **Cross-market financial analysis** between BIST and MOEX sector leaders.
- **Asynchronous data ingestion** for a responsive dashboard experience.
- **Precision-safe calculations** using `decimal.Decimal` where pricing precision matters.
- **Resilience against upstream issues** through error handling, retries, and fallback behavior.
- **Presentation discipline** through multilingual UX and explicit methodology notes.

## Covered Sector Pairs

| Sector | 🇹🇷 BIST | 🇷🇺 MOEX |
|--------|---------|---------|
| Aviation | THYAO | AFLT |
| Energy | TUPRS | LKOH |
| Banking | AKBNK | SBER |
| Retail | BIMAS | MGNT |
| Steel | EREGL | NLMK |

## Analytics Included

- Period return
- YTD performance
- Annualized volatility
- Sharpe ratio
- Maximum drawdown
- CAGR
- Return-based Pearson correlation
- Base-100 normalized performance chart
- Optional USD-denominated comparison

## Data Integrity Choices

- **BIST source:** [Yahoo Finance](https://finance.yahoo.com/)
- **MOEX source:** [Finam Export API](https://export.finam.ru/)
- **FX conversion:** aligned to trading dates with forward-filled exchange-rate gaps inside the selected window
- **Market-cap comparison:** curated snapshot from `config.yaml` for presentation consistency
- **MOEX lag handling:** the interface explicitly warns when the latest available date is earlier than the user-selected end date

These choices are intentional. The goal is a transparent comparative analytics product, not an opaque “real-time” claim.

## Architecture

```text
BistvsMoex/
├── app.py              # Streamlit entry point and dashboard orchestration
├── config.yaml         # Sectors, colors, macro events, and market-cap snapshot metadata
├── src/
│   ├── data.py         # External data access and currency conversion
│   ├── analysis.py     # Financial metrics and normalization logic
│   ├── config.py       # Config loading and translation layer
│   ├── exceptions.py   # Custom domain exceptions
│   └── ui.py           # Reusable UI rendering helpers
└── tests/              # Automated test suite
```

## Run Locally

1. Create a virtual environment.
2. Install dependencies.
3. Start the dashboard.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Configuration

Two environment overrides are supported:

| Variable | Purpose | Default |
|----------|---------|---------|
| `BM_TIMEOUT` | Finam request timeout in seconds | `15` |
| `BM_MOEX_DELAY` | Expected MOEX publication lag in days | `2` |

Example:

```bash
BM_TIMEOUT=30 streamlit run app.py
```

## Testing

The repository includes unit and robustness tests for:

- financial calculations,
- Finam URL generation and parsing,
- async fetching behavior,
- currency conversion,
- defensive handling of invalid or future inputs.

Run everything with:

```bash
python -m pytest tests -v
```

## Why This Matters In A Portfolio

This project signals more than dashboard-building. It shows the ability to work across:

- finance and software architecture,
- Turkish and Russian market context,
- data reliability and user-facing communication,
- technical implementation and analytical framing.

That combination is the core reason this project belongs in a graduate application portfolio.

## Disclaimer

This application is for educational and comparative analysis purposes only. It does not constitute investment advice.
