"""
Analysis module for The Eurasian Bridge application.
Contains financial calculation and analysis functions.
"""

from decimal import Decimal, getcontext, InvalidOperation
import numpy as np
import pandas as pd
from typing import Union, Optional

from src.config import get_text, DATA_CONFIG

# Set precision for financial calculations
getcontext().prec = 28


def normalize_to_base_100(series: pd.Series) -> pd.Series:
    """
    Rebase a price series to start at 100 for relative performance comparison.
    Uses Decimal for precision, returns generic object series or float series 
    depending on compatibility needs, but calculations are precise.
    
    Args:
        series: Price series to normalize
    
    Returns:
        Normalized series starting at 100
    """
    if series.empty:
        return series

    try:
        # Defensive: Handle potential non-numeric types safely
        initial_val_raw = series.iloc[0]
        
        # precise conversion to Decimal
        try:
            initial_val = Decimal(str(initial_val_raw))
        except (InvalidOperation, TypeError):
            # Fallback if data is messy, though it shouldn't be
            return series

        if initial_val == 0:
            return series
            
        dec_100 = Decimal("100")

        # Perform calculation using Decimal
        # Note: applying to a pandas series invalidates vectorization performance,
        # but guarantees financial precision as requested.
        def _rebase(x):
            try:
                return (Decimal(str(x)) / initial_val) * dec_100
            except (InvalidOperation, TypeError):
                return x

        # Result is object-dtype Series of Decimal objects
        result = series.apply(_rebase)
        return result

    except Exception:
        # Fallback to original if something critical fails (Defensive Coding)
        return series


def calculate_correlation(series1: pd.Series, series2: pd.Series) -> float:
    """
    Calculate Pearson correlation coefficient between two series.
    
    Args:
        series1: First return series
        series2: Second return series
    
    Returns:
        Pearson correlation coefficient, or NaN if insufficient data
    """
    # Ensure inputs are float for numpy/pandas correlation (statistical measure, not currency)
    s1 = series1.astype(float)
    s2 = series2.astype(float)
    
    aligned = pd.concat([s1, s2], axis=1, join='inner').dropna()
    min_points = DATA_CONFIG.get("min_correlation_points", 10)
    if len(aligned) < min_points:
        return float('nan')
    return aligned.iloc[:, 0].corr(aligned.iloc[:, 1])


def interpret_correlation(corr: float, lang: str = "en") -> str:
    """
    Provide interpretation of correlation coefficient.
    
    Args:
        corr: Pearson correlation coefficient
        lang: Language code for translation
    
    Returns:
        Human-readable interpretation string
    """
    if np.isnan(corr):
        return get_text("insufficient_data", lang)
    elif corr >= 0.7:
        return get_text("strong_positive", lang)
    elif corr >= 0.4:
        return get_text("moderate_positive", lang)
    elif corr >= 0.1:
        return get_text("weak_positive", lang)
    elif corr >= -0.1:
        return get_text("no_correlation", lang)
    elif corr >= -0.4:
        return get_text("weak_negative", lang)
    elif corr >= -0.7:
        return get_text("moderate_negative", lang)
    else:
        return get_text("strong_negative", lang)


def calculate_change_pct(series: pd.Series) -> Decimal:
    """
    Calculate percentage change from first to last value using Decimal precision.
    
    Args:
        series: Price series
    
    Returns:
        Percentage change as a Decimal
    """
    if len(series) < 2:
        return Decimal("0.0")
        
    try:
        start = Decimal(str(series.iloc[0]))
        end = Decimal(str(series.iloc[-1]))
        
        if start == 0:
            return Decimal("0.0")
            
        return ((end - start) / start) * Decimal("100")
    except (InvalidOperation, TypeError):
        return Decimal("0.0")


def calculate_volatility(series: pd.Series, periods_per_year: int = 252) -> float:
    """
    Calculate annualized volatility (standard deviation of returns).
    
    Args:
        series: Price series
        periods_per_year: Number of trading periods per year (252 for daily)
    
    Returns:
        Annualized volatility as percentage, or NaN if insufficient data
    """
    # Convert to float for statistical calculations (std dev)
    series_float = series.astype(float)
    returns = series_float.pct_change().dropna()
    
    min_points = DATA_CONFIG.get("min_correlation_points", 10)
    if len(returns) < min_points:
        return float('nan')
    
    # Calculate standard deviation and annualize
    volatility = returns.std() * np.sqrt(periods_per_year)
    return volatility * 100  # Convert to percentage


def calculate_sharpe_ratio(series: pd.Series, risk_free_rate: float = 0.0, 
                           periods_per_year: int = 252) -> float:
    """
    Calculate Sharpe Ratio (risk-adjusted return).
    
    Args:
        series: Price series
        risk_free_rate: Annual risk-free rate (default 0%)
        periods_per_year: Number of trading periods per year (252 for daily)
    
    Returns:
        Sharpe ratio, or NaN if insufficient data
    """
    # Convert to float for statistical calculations
    series_float = series.astype(float)
    returns = series_float.pct_change().dropna()
    
    min_points = DATA_CONFIG.get("min_correlation_points", 10)
    if len(returns) < min_points:
        return float('nan')
    
    # Calculate annualized return and volatility
    mean_return = returns.mean() * periods_per_year
    volatility = returns.std() * np.sqrt(periods_per_year)
    
    if volatility == 0:
        return float('nan')
    
    sharpe = (mean_return - risk_free_rate) / volatility
    return sharpe


def calculate_maximum_drawdown(series: pd.Series) -> float:
    """
    Calculate maximum drawdown (largest peak-to-trough decline).
    
    Args:
        series: Price series
    
    Returns:
        Maximum drawdown as percentage (negative value), or NaN if insufficient data
    """
    if len(series) < 2:
        return float('nan')
    
    # Convert to float for cummax
    s = series.astype(float)
    
    # Calculate cumulative maximum
    cummax = s.cummax()
    # Calculate drawdown at each point
    drawdown = (s - cummax) / cummax
    # Return the minimum (most negative) drawdown
    max_dd = drawdown.min()
    return max_dd * 100  # Convert to percentage


def calculate_cagr(series: pd.Series, periods_per_year: int = 252) -> float:
    """
    Calculate Compound Annual Growth Rate (CAGR).
    
    Args:
        series: Price series
        periods_per_year: Number of trading periods per year (252 for daily)
    
    Returns:
        CAGR as percentage, or NaN if insufficient data
    """
    if len(series) < 2:
        return float('nan')
    
    # CAGR can be calculated with Decimal for precision
    try:
        start_price = Decimal(str(series.iloc[0]))
        end_price = Decimal(str(series.iloc[-1]))
        
        if start_price <= 0 or end_price <= 0:
            return float('nan')
        
        # Calculate total number of years
        num_periods = len(series)
        num_years = Decimal(str(num_periods)) / Decimal(str(periods_per_year))
        
        if num_years <= 0:
            return float('nan')
        
        # Calculate CAGR using float power for exponentiation as Decimal power can be tricky with non-integers
        # But we can try to stay in Decimal if possible, or cast for the power operation
        # (end/start)^(1/years) - 1
        
        # Using float for the exponentiation part is usually acceptable for CAGR
        res = (float(end_price / start_price)) ** (1 / float(num_years)) - 1
        return res * 100
        
    except Exception:
        return float('nan')
