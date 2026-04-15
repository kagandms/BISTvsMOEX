"""
Unit tests for the analysis and configuration layers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis import (
    calculate_cagr,
    calculate_change_pct,
    calculate_correlation,
    calculate_maximum_drawdown,
    calculate_sharpe_ratio,
    calculate_volatility,
    interpret_correlation,
    normalize_to_base_100,
)


class TestNormalizeToBase100:
    """Tests for normalize_to_base_100."""

    def test_basic_normalization(self) -> None:
        series = pd.Series([50, 75, 100, 125])
        result = normalize_to_base_100(series)
        assert result.iloc[0] == 100.0
        assert result.iloc[-1] == 250.0

    def test_invalid_start_returns_empty_series(self) -> None:
        zero_result = normalize_to_base_100(pd.Series([0, 10, 20]))
        negative_result = normalize_to_base_100(pd.Series([-50, -25, 0, 25]))

        assert zero_result.empty
        assert negative_result.empty


class TestCalculateCorrelation:
    """Tests for calculate_correlation."""

    def test_perfect_positive_correlation(self) -> None:
        dates = pd.date_range("2024-01-01", periods=20)
        left = pd.Series(np.random.randn(20), index=dates)
        right = left.copy()
        correlation = calculate_correlation(left, right)
        assert correlation is not None
        assert abs(correlation - 1.0) < 1e-10

    def test_insufficient_data_returns_none(self) -> None:
        dates = pd.date_range("2024-01-01", periods=5)
        left = pd.Series([1, 2, 3, 4, 5], index=dates)
        right = pd.Series([5, 4, 3, 2, 1], index=dates)
        assert calculate_correlation(left, right) is None

    def test_no_overlap_returns_none(self) -> None:
        left = pd.Series(np.random.randn(10), index=pd.date_range("2024-01-01", periods=10))
        right = pd.Series(np.random.randn(10), index=pd.date_range("2024-06-01", periods=10))
        assert calculate_correlation(left, right) is None


class TestInterpretCorrelation:
    """Tests for interpret_correlation."""

    def test_nan_value_maps_to_insufficient_data(self) -> None:
        assert interpret_correlation(np.nan, "en") == "Insufficient data"

    def test_translation_variants(self) -> None:
        assert interpret_correlation(0.85, "tr") == "Güçlü Pozitif Korelasyon"
        assert interpret_correlation(0.85, "ru") == "Сильная Положительная Корреляция"


class TestCalculateChangePct:
    """Tests for period change calculation."""

    def test_positive_change(self) -> None:
        assert calculate_change_pct(pd.Series([100, 150])) == 50.0

    def test_invalid_series_returns_none(self) -> None:
        assert calculate_change_pct(pd.Series([100])) is None
        assert calculate_change_pct(pd.Series([0, 10, 20])) is None
        assert calculate_change_pct(pd.Series([], dtype=float)) is None


class TestConfig:
    """Tests for configuration helpers."""

    def test_config_loads(self) -> None:
        from src.config import CONFIG

        assert CONFIG is not None
        assert "sectors" in CONFIG
        assert "colors" in CONFIG

    def test_get_text_translations(self) -> None:
        from src.config import get_text

        assert "Eurasian Bridge" in get_text("app_title", "en")
        assert "Avrasya" in get_text("app_title", "tr")
        assert "Евразийский" in get_text("app_title", "ru")

    def test_get_sector_options(self) -> None:
        from src.config import get_sector_options

        options = get_sector_options("en")
        assert len(options) == 5
        assert "aviation" in options.values()

    def test_risk_summary_translation_keys_exist(self) -> None:
        from src.config import TRANSLATIONS

        summary_keys = (
            "risk_summary_title",
            "risk_summary_intro",
            "volatility_summary",
            "sharpe_ratio_summary",
            "max_drawdown_summary",
            "cagr_summary",
            "metric_unavailable",
            "error_schema",
            "error_conversion_incomplete",
            "error_inflation_incomplete",
            "mode_real",
            "real_conversion_unavailable",
            "methodology_point_6",
        )

        for lang in ("en", "tr", "ru"):
            for key in summary_keys:
                assert key in TRANSLATIONS[lang]
                assert TRANSLATIONS[lang][key]


class TestVolatility:
    """Tests for calculate_volatility."""

    def test_volatility_calculation(self) -> None:
        dates = pd.date_range("2024-01-01", periods=20)
        series = pd.Series(
            [100, 105, 95, 110, 90, 105, 95, 110, 88, 105, 95, 112, 85, 108, 95, 115, 82, 105, 98, 120],
            index=dates,
        )
        volatility = calculate_volatility(series)
        assert volatility is not None
        assert volatility > 0

    def test_zero_returns_are_zero_volatility(self) -> None:
        dates = pd.date_range("2024-01-01", periods=20)
        series = pd.Series([100] * 20, index=dates)
        assert calculate_volatility(series) == 0.0

    def test_insufficient_data_returns_none(self) -> None:
        dates = pd.date_range("2024-01-01", periods=5)
        series = pd.Series([100, 105, 110, 115, 120], index=dates)
        assert calculate_volatility(series) is None


class TestSharpeRatio:
    """Tests for calculate_sharpe_ratio."""

    def test_positive_and_negative_trends(self) -> None:
        dates = pd.date_range("2024-01-01", periods=20)
        positive = pd.Series([100 + i * 2 for i in range(20)], index=dates)
        negative = pd.Series([138 - i * 2 for i in range(20)], index=dates)

        assert calculate_sharpe_ratio(positive) is not None
        assert calculate_sharpe_ratio(positive) > 0
        assert calculate_sharpe_ratio(negative) is not None
        assert calculate_sharpe_ratio(negative) < 0

    def test_invalid_inputs_return_none(self) -> None:
        dates = pd.date_range("2024-01-01", periods=5)
        short_series = pd.Series([100, 105, 110, 115, 120], index=dates)
        flat_series = pd.Series([100] * 20, index=pd.date_range("2024-01-01", periods=20))

        assert calculate_sharpe_ratio(short_series) is None
        assert calculate_sharpe_ratio(flat_series) is None


class TestMaximumDrawdown:
    """Tests for calculate_maximum_drawdown."""

    def test_drawdown_behaviour(self) -> None:
        falling_series = pd.Series([100, 110, 120, 130, 125, 115, 105, 95, 85, 80])
        rising_series = pd.Series([100, 105, 110, 115, 120, 125, 130, 135, 140, 145])

        max_drawdown = calculate_maximum_drawdown(falling_series)
        assert max_drawdown is not None
        assert max_drawdown < 0
        assert calculate_maximum_drawdown(rising_series) == 0.0

    def test_invalid_input_returns_none(self) -> None:
        assert calculate_maximum_drawdown(pd.Series([100])) is None
        assert calculate_maximum_drawdown(pd.Series([100, 0, 90])) is None


class TestCagr:
    """Tests for calculate_cagr."""

    def test_positive_and_negative_cagr(self) -> None:
        dates = pd.date_range("2024-01-01", periods=252)
        positive = pd.Series(100 * (1.002 ** np.arange(252)), index=dates)
        negative = pd.Series(120 * (0.998 ** np.arange(252)), index=dates)

        assert calculate_cagr(positive) is not None
        assert calculate_cagr(positive) > 0
        assert calculate_cagr(negative) is not None
        assert calculate_cagr(negative) < 0

    def test_invalid_inputs_return_none(self) -> None:
        assert calculate_cagr(pd.Series([100])) is None
        zero_series = pd.Series([0, 10, 20], index=pd.date_range("2024-01-01", periods=3))
        assert calculate_cagr(zero_series) is None

    def test_calendar_time_drives_cagr_for_sparse_series(self) -> None:
        sparse = pd.Series([100.0, 110.0], index=pd.to_datetime(["2024-01-01", "2024-12-31"]))
        dense = pd.Series(
            [100.0] * 364 + [110.0],
            index=pd.date_range("2024-01-01", periods=365),
        )

        sparse_cagr = calculate_cagr(sparse)
        dense_cagr = calculate_cagr(dense)

        assert sparse_cagr is not None
        assert dense_cagr is not None
        assert abs(sparse_cagr - dense_cagr) < 0.5
