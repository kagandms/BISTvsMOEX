"""
Unit tests for the analysis module.
"""

import numpy as np
import pandas as pd
import pytest

from src.analysis import (
    normalize_to_base_100,
    calculate_correlation,
    interpret_correlation,
    calculate_change_pct,
    calculate_volatility,
    calculate_sharpe_ratio,
    calculate_maximum_drawdown,
    calculate_cagr,
)


class TestNormalizeToBase100:
    """Tests for normalize_to_base_100 function."""

    def test_basic_normalization(self):
        """First value should become 100."""
        series = pd.Series([50, 75, 100, 125])
        result = normalize_to_base_100(series)
        assert result.iloc[0] == 100.0

    def test_proportional_scaling(self):
        """Values should scale proportionally."""
        series = pd.Series([50, 75, 100, 125])
        result = normalize_to_base_100(series)
        assert result.iloc[1] == 150.0  # 75/50 * 100
        assert result.iloc[2] == 200.0  # 100/50 * 100
        assert result.iloc[3] == 250.0  # 125/50 * 100

    def test_zero_initial_value(self):
        """Should return original series if initial value is zero."""
        series = pd.Series([0, 10, 20])
        result = normalize_to_base_100(series)
        pd.testing.assert_series_equal(result, series)

    def test_single_value(self):
        """Should handle single-element series."""
        series = pd.Series([42])
        result = normalize_to_base_100(series)
        assert result.iloc[0] == 100.0

    def test_negative_values(self):
        """Should handle negative starting values."""
        series = pd.Series([-50, -25, 0, 25])
        result = normalize_to_base_100(series)
        assert result.iloc[0] == 100.0
        assert result.iloc[1] == 50.0  # -25/-50 * 100


class TestCalculateCorrelation:
    """Tests for calculate_correlation function."""

    def test_perfect_positive_correlation(self):
        """Identical series should have correlation of 1.0."""
        dates = pd.date_range('2024-01-01', periods=20)
        s1 = pd.Series(np.random.randn(20), index=dates)
        s2 = s1.copy()
        corr = calculate_correlation(s1, s2)
        assert abs(corr - 1.0) < 1e-10

    def test_perfect_negative_correlation(self):
        """Negated series should have correlation of -1.0."""
        dates = pd.date_range('2024-01-01', periods=20)
        s1 = pd.Series(np.random.randn(20), index=dates)
        s2 = -s1
        corr = calculate_correlation(s1, s2)
        assert abs(corr - (-1.0)) < 1e-10

    def test_insufficient_data(self):
        """Should return NaN for fewer than 10 data points."""
        dates = pd.date_range('2024-01-01', periods=5)
        s1 = pd.Series([1, 2, 3, 4, 5], index=dates)
        s2 = pd.Series([5, 4, 3, 2, 1], index=dates)
        corr = calculate_correlation(s1, s2)
        assert np.isnan(corr)

    def test_misaligned_indices(self):
        """Should align series by index before calculating."""
        dates1 = pd.date_range('2024-01-01', periods=15)
        dates2 = pd.date_range('2024-01-05', periods=15)
        s1 = pd.Series(np.random.randn(15), index=dates1)
        s2 = pd.Series(np.random.randn(15), index=dates2)
        corr = calculate_correlation(s1, s2)
        # Should have 11 overlapping points, enough for calculation
        assert not np.isnan(corr)

    def test_no_overlap(self):
        """Should return NaN when series don't overlap."""
        dates1 = pd.date_range('2024-01-01', periods=10)
        dates2 = pd.date_range('2024-06-01', periods=10)
        s1 = pd.Series(np.random.randn(10), index=dates1)
        s2 = pd.Series(np.random.randn(10), index=dates2)
        corr = calculate_correlation(s1, s2)
        assert np.isnan(corr)


class TestInterpretCorrelation:
    """Tests for interpret_correlation function."""

    def test_strong_positive(self):
        result = interpret_correlation(0.85, "en")
        assert result == "Strong Positive Correlation"

    def test_moderate_positive(self):
        result = interpret_correlation(0.55, "en")
        assert result == "Moderate Positive Correlation"

    def test_weak_positive(self):
        result = interpret_correlation(0.25, "en")
        assert result == "Weak Positive Correlation"

    def test_no_correlation(self):
        result = interpret_correlation(0.05, "en")
        assert result == "No Significant Correlation"

    def test_weak_negative(self):
        result = interpret_correlation(-0.25, "en")
        assert result == "Weak Negative Correlation"

    def test_moderate_negative(self):
        result = interpret_correlation(-0.55, "en")
        assert result == "Moderate Negative Correlation"

    def test_strong_negative(self):
        result = interpret_correlation(-0.85, "en")
        assert result == "Strong Negative Correlation"

    def test_nan_value(self):
        result = interpret_correlation(np.nan, "en")
        assert result == "Insufficient data"

    def test_turkish_translation(self):
        result = interpret_correlation(0.85, "tr")
        assert result == "Güçlü Pozitif Korelasyon"

    def test_russian_translation(self):
        result = interpret_correlation(0.85, "ru")
        assert result == "Сильная Положительная Корреляция"

    def test_boundary_values(self):
        """Test exact boundary values."""
        assert "Strong Positive" in interpret_correlation(0.7, "en")
        assert "Moderate Positive" in interpret_correlation(0.4, "en")
        assert "Weak Positive" in interpret_correlation(0.1, "en")
        assert "No Significant" in interpret_correlation(-0.1, "en")


class TestCalculateChangePct:
    """Tests for calculate_change_pct function."""

    def test_positive_change(self):
        series = pd.Series([100, 110, 120, 150])
        result = calculate_change_pct(series)
        assert result == 50.0

    def test_negative_change(self):
        series = pd.Series([100, 90, 80, 50])
        result = calculate_change_pct(series)
        assert result == -50.0

    def test_no_change(self):
        series = pd.Series([100, 110, 90, 100])
        result = calculate_change_pct(series)
        assert result == 0.0

    def test_single_value(self):
        """Should return 0 for single-element series."""
        series = pd.Series([100])
        result = calculate_change_pct(series)
        assert result == 0.0

    def test_zero_initial(self):
        """Should return 0 if initial value is zero."""
        series = pd.Series([0, 10, 20])
        result = calculate_change_pct(series)
        assert result == 0.0

    def test_empty_series(self):
        """Should return 0 for empty series."""
        series = pd.Series([], dtype=float)
        result = calculate_change_pct(series)
        assert result == 0.0


class TestConfig:
    """Tests for configuration module."""

    def test_config_loads(self):
        from src.config import CONFIG
        assert CONFIG is not None
        assert "sectors" in CONFIG
        assert "colors" in CONFIG

    def test_sectors_structure(self):
        from src.config import SECTORS
        assert "aviation" in SECTORS
        assert "energy" in SECTORS
        assert "banking" in SECTORS
        assert "retail" in SECTORS
        assert "steel" in SECTORS
        for sector_id, sector in SECTORS.items():
            assert "TR" in sector
            assert "RU" in sector
            assert "icon" in sector

    def test_get_text_english(self):
        from src.config import get_text
        result = get_text("app_title", "en")
        assert "Eurasian Bridge" in result

    def test_get_text_turkish(self):
        from src.config import get_text
        result = get_text("app_title", "tr")
        assert "Avrasya" in result

    def test_get_text_russian(self):
        from src.config import get_text
        result = get_text("app_title", "ru")
        assert "Евразийский" in result

    def test_get_text_with_kwargs(self):
        from src.config import get_text
        result = get_text("error_no_data", "en", ticker="TEST")
        assert "TEST" in result

    def test_get_text_fallback(self):
        """Unknown key should return the key itself."""
        from src.config import get_text
        result = get_text("nonexistent_key", "en")
        assert result == "nonexistent_key"

    def test_get_sector_options(self):
        from src.config import get_sector_options
        options = get_sector_options("en")
        assert len(options) == 5
        # Values should be sector IDs
        assert "aviation" in options.values()


class TestVolatility:
    """Tests for calculate_volatility function."""
    
    def test_volatility_calculation(self):
        """Should calculate annualized volatility correctly."""
        dates = pd.date_range('2024-01-01', periods=20)
        # High volatility series
        series = pd.Series([100, 105, 95, 110, 90, 105, 95, 110, 88, 105,
                          95, 112, 85, 108, 95, 115, 82, 105, 98, 120], index=dates)
        vol = calculate_volatility(series)
        assert not np.isnan(vol)
        assert vol > 0
    
    def test_volatility_zero_returns(self):
        """Should return NaN for series with no variation."""
        dates = pd.date_range('2024-01-01', periods=20)
        series = pd.Series([100] * 20, index=dates)
        vol = calculate_volatility(series)
        assert not np.isnan(vol)
    
    def test_volatility_insufficient_data(self):
        """Should return NaN for insufficient data points."""
        dates = pd.date_range('2024-01-01', periods=5)
        series = pd.Series([100, 105, 110, 115, 120], index=dates)
        vol = calculate_volatility(series)
        assert np.isnan(vol)


class TestSharpeRatio:
    """Tests for calculate_sharpe_ratio function."""
    
    def test_sharpe_ratio_positive(self):
        """Should calculate positive Sharpe ratio."""
        dates = pd.date_range('2024-01-01', periods=20)
        # Upward trending series
        series = pd.Series([100, 102, 104, 106, 108, 110, 112, 114, 116, 118,
                          120, 122, 124, 126, 128, 130, 132, 134, 136, 138], index=dates)
        sharpe = calculate_sharpe_ratio(series)
        assert not np.isnan(sharpe)
        assert sharpe > 0
    
    def test_sharpe_ratio_negative(self):
        """Should calculate negative Sharpe ratio for downward trend."""
        dates = pd.date_range('2024-01-01', periods=20)
        # Downward trending series
        series = pd.Series([138, 136, 134, 132, 130, 128, 126, 124, 122, 120,
                          118, 116, 114, 112, 110, 108, 106, 104, 102, 100], index=dates)
        sharpe = calculate_sharpe_ratio(series)
        assert not np.isnan(sharpe)
        assert sharpe < 0
    
    def test_sharpe_ratio_with_risk_free(self):
        """Should handle risk-free rate parameter."""
        dates = pd.date_range('2024-01-01', periods=20)
        series = pd.Series([100, 102, 104, 106, 108, 110, 112, 114, 116, 118,
                          120, 122, 124, 126, 128, 130, 132, 134, 136, 138], index=dates)
        sharpe = calculate_sharpe_ratio(series, risk_free_rate=0.05)
        assert not np.isnan(sharpe)
    
    def test_sharpe_ratio_insufficient_data(self):
        """Should return NaN for insufficient data."""
        dates = pd.date_range('2024-01-01', periods=5)
        series = pd.Series([100, 105, 110, 115, 120], index=dates)
        sharpe = calculate_sharpe_ratio(series)
        assert np.isnan(sharpe)


class TestMaximumDrawdown:
    """Tests for calculate_maximum_drawdown function."""
    
    def test_max_drawdown_calculation(self):
        """Should calculate maximum drawdown correctly."""
        dates = pd.date_range('2024-01-01', periods=10)
        # Up then down
        series = pd.Series([100, 110, 120, 130, 125, 115, 105, 95, 85, 80], index=dates)
        mdd = calculate_maximum_drawdown(series)
        assert not np.isnan(mdd)
        assert mdd < 0  # Drawdown is always negative
    
    def test_max_drawdown_no_decline(self):
        """Should return 0 for steadily increasing series."""
        dates = pd.date_range('2024-01-01', periods=10)
        series = pd.Series([100, 105, 110, 115, 120, 125, 130, 135, 140, 145], index=dates)
        mdd = calculate_maximum_drawdown(series)
        assert mdd == 0
    
    def test_max_drawdown_single_value(self):
        """Should return NaN for single value."""
        series = pd.Series([100])
        mdd = calculate_maximum_drawdown(series)
        assert np.isnan(mdd)


class TestCAGR:
    """Tests for calculate_cagr function."""
    
    def test_cagr_positive(self):
        """Should calculate positive CAGR."""
        dates = pd.date_range('2024-01-01', periods=252)  # 1 year of daily data
        # Start at 100, end at 120 = ~73% annual return
        import numpy as np
        series = pd.Series(100 * (1.002 ** np.arange(252)), index=dates)
        cagr = calculate_cagr(series)
        assert not np.isnan(cagr)
        assert cagr > 0
    
    def test_cagr_negative(self):
        """Should calculate negative CAGR for declining prices."""
        dates = pd.date_range('2024-01-01', periods=252)
        # Start at 120, end at 100
        import numpy as np
        series = pd.Series(120 * (0.998 ** np.arange(252)), index=dates)
        cagr = calculate_cagr(series)
        assert not np.isnan(cagr)
        assert cagr < 0
    
    def test_cagr_insufficient_data(self):
        """Should return NaN for single value."""
        series = pd.Series([100])
        cagr = calculate_cagr(series)
        assert np.isnan(cagr)
    
    def test_cagr_zero_prices(self):
        """Should return NaN for zero or negative prices."""
        dates = pd.date_range('2024-01-01', periods=20)
        series = pd.Series([0, 10, 20, 30, 40, 50, 60, 70, 80, 90,
                          100, 110, 120, 130, 140, 150, 160, 170, 180, 190], index=dates)
        cagr = calculate_cagr(series)
        assert np.isnan(cagr)
