"""
Analysis module for The Eurasian Bridge application.
Contains financial calculation and analysis functions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import DATA_CONFIG, get_text


def normalize_to_base_100(series: pd.Series) -> pd.Series:
    """Rebase a clean price series to 100 for comparison charts."""

    clean_series = _sanitize_numeric_series(series)
    if clean_series.empty:
        return clean_series

    initial_value = clean_series.iloc[0]
    if initial_value <= 0:
        return clean_series.iloc[0:0]

    return (clean_series / initial_value) * 100


def calculate_correlation(series1: pd.Series, series2: pd.Series) -> float | None:
    """Calculate the Pearson correlation coefficient between two series."""

    left = _sanitize_numeric_series(series1)
    right = _sanitize_numeric_series(series2)
    aligned = pd.concat([left, right], axis=1, join="inner").dropna()
    if len(aligned) < DATA_CONFIG.get("min_correlation_points", 10):
        return None

    correlation = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
    return _as_finite_float(correlation)


def interpret_correlation(corr: float | None, lang: str = "en") -> str:
    """Return a localized correlation interpretation."""

    if corr is None or (isinstance(corr, float) and np.isnan(corr)):
        return get_text("insufficient_data", lang)
    if corr >= 0.7:
        return get_text("strong_positive", lang)
    if corr >= 0.4:
        return get_text("moderate_positive", lang)
    if corr >= 0.1:
        return get_text("weak_positive", lang)
    if corr >= -0.1:
        return get_text("no_correlation", lang)
    if corr >= -0.4:
        return get_text("weak_negative", lang)
    if corr >= -0.7:
        return get_text("moderate_negative", lang)
    return get_text("strong_negative", lang)


def calculate_change_pct(series: pd.Series) -> float | None:
    """Calculate period change percentage."""

    clean_series = _sanitize_numeric_series(series)
    if len(clean_series) < 2:
        return None

    start_value = clean_series.iloc[0]
    end_value = clean_series.iloc[-1]
    if start_value <= 0:
        return None

    return _as_finite_float(((end_value - start_value) / start_value) * 100)


def calculate_volatility(
    series: pd.Series,
    periods_per_year: int = 252,
) -> float | None:
    """Calculate annualized volatility from daily returns."""

    returns = _calculate_returns(series)
    if returns is None or len(returns) < DATA_CONFIG.get("min_correlation_points", 10):
        return None

    volatility = returns.std() * np.sqrt(periods_per_year) * 100
    finite_value = _as_finite_float(volatility)
    if finite_value is None:
        return None

    return finite_value


def calculate_sharpe_ratio(
    series: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float | None:
    """Calculate the Sharpe ratio."""

    returns = _calculate_returns(series)
    if returns is None or len(returns) < DATA_CONFIG.get("min_correlation_points", 10):
        return None

    volatility = returns.std() * np.sqrt(periods_per_year)
    finite_volatility = _as_finite_float(volatility)
    if finite_volatility is None or finite_volatility <= 0:
        return None

    mean_return = returns.mean() * periods_per_year
    return _as_finite_float((mean_return - risk_free_rate) / finite_volatility)


def calculate_maximum_drawdown(series: pd.Series) -> float | None:
    """Calculate the maximum drawdown percentage."""

    clean_series = _sanitize_numeric_series(series)
    if len(clean_series) < 2 or (clean_series <= 0).any():
        return None

    cumulative_max = clean_series.cummax()
    drawdown = ((clean_series - cumulative_max) / cumulative_max) * 100
    return _as_finite_float(drawdown.min())


def calculate_cagr(
    series: pd.Series,
    periods_per_year: int = 252,
) -> float | None:
    """Calculate CAGR for a clean price series."""

    clean_series = _sanitize_numeric_series(series)
    if len(clean_series) < 2:
        return None

    start_price = clean_series.iloc[0]
    end_price = clean_series.iloc[-1]
    if start_price <= 0 or end_price <= 0:
        return None

    years = _calculate_elapsed_years(clean_series.index, periods_per_year)
    if years <= 0:
        return None

    cagr = ((end_price / start_price) ** (1 / years) - 1) * 100
    return _as_finite_float(cagr)


def _calculate_returns(series: pd.Series) -> pd.Series | None:
    """Calculate clean percentage returns."""

    clean_series = _sanitize_numeric_series(series)
    if len(clean_series) < 2 or (clean_series <= 0).any():
        return None

    returns = clean_series.pct_change().dropna()
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if returns.empty:
        return None

    return returns


def _sanitize_numeric_series(series: pd.Series) -> pd.Series:
    """Return a numeric, finite, ordered series."""

    numeric_series = pd.to_numeric(series, errors="coerce")
    clean_series = numeric_series.replace([np.inf, -np.inf], np.nan).dropna()
    clean_series = clean_series[~clean_series.index.duplicated(keep="last")]
    return clean_series.sort_index()


def _calculate_elapsed_years(index: pd.Index, periods_per_year: int) -> float:
    """Return elapsed years using calendar time when possible."""

    if isinstance(index, pd.DatetimeIndex):
        start_timestamp = pd.Timestamp(index[0])
        end_timestamp = pd.Timestamp(index[-1])
        elapsed_seconds = (end_timestamp - start_timestamp).total_seconds()
        if elapsed_seconds > 0:
            return elapsed_seconds / (60 * 60 * 24 * 365.25)

    return len(index) / periods_per_year


def _as_finite_float(value: float | int | None) -> float | None:
    """Return a float only when the value is finite."""

    if value is None:
        return None

    numeric_value = float(value)
    if not np.isfinite(numeric_value):
        return None

    return numeric_value
