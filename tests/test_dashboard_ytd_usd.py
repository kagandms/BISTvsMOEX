"""
Unit tests for YTD USD conversion logic.
Validates calculate_ytd_change_usd from src.dashboard.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.dashboard import calculate_ytd_change_usd
from src.models import (
    DateRange,
    FxRateWindow,
    OperationResult,
    error_result,
    success_result,
)


def _make_price_result(
    prices: list[float],
    start: str = "2025-01-02",
) -> OperationResult[pd.Series]:
    """Build a successful price OperationResult."""
    dates = pd.date_range(start, periods=len(prices))
    series = pd.Series(prices, index=dates, name="Close")
    rng = DateRange(start=dates[0].date(), end=dates[-1].date())
    return success_result(series, rng, rng)


def _make_baseline_result(value: float) -> OperationResult[Decimal]:
    """Build a successful baseline OperationResult."""
    rng = DateRange(start=pd.Timestamp("2025-01-01").date(), end=pd.Timestamp("2025-01-01").date())
    return success_result(Decimal(str(value)), rng, rng)


def _make_fx_rates(
    try_rates: list[float] | None = None,
    rub_rates: list[float] | None = None,
    start: str = "2025-01-02",
) -> FxRateWindow:
    """Build FxRateWindow with optional TRY/RUB rates."""
    usd_try = None
    usd_rub = None
    if try_rates is not None:
        dates = pd.date_range(start, periods=len(try_rates))
        usd_try = pd.DataFrame({"USD_TRY": try_rates}, index=dates)
    if rub_rates is not None:
        dates = pd.date_range(start, periods=len(rub_rates))
        usd_rub = pd.DataFrame({"USD_RUB": rub_rates}, index=dates)
    return FxRateWindow(usd_try=usd_try, usd_rub=usd_rub)


class TestCalculateYtdChangeUsd:
    """Tests for calculate_ytd_change_usd."""

    def test_happy_path_try_conversion(self) -> None:
        """With valid FX data, YTD should be computed in USD terms."""
        # TRY prices: 100, 120 ;  USD/TRY rate: 10, 10
        # USD prices: 10, 12 => YTD = (12-10)/10*100 = +20%
        prices = _make_price_result([100.0, 120.0])
        baseline = _make_baseline_result(90.0)  # local baseline, ignored in USD path
        fx = _make_fx_rates(try_rates=[10.0, 10.0])

        result = calculate_ytd_change_usd(prices, baseline, "TRY", fx)

        assert result.is_success
        assert result.payload is not None
        assert abs(result.payload - 20.0) < 0.01

    def test_happy_path_rub_conversion(self) -> None:
        """RUB conversion path works correctly."""
        # RUB prices: 5000, 6000 ; USD/RUB rate: 100, 100
        # USD prices: 50, 60 => YTD = (60-50)/50*100 = +20%
        prices = _make_price_result([5000.0, 6000.0])
        baseline = _make_baseline_result(4500.0)
        fx = _make_fx_rates(rub_rates=[100.0, 100.0])

        result = calculate_ytd_change_usd(prices, baseline, "RUB", fx)

        assert result.is_success
        assert result.payload is not None
        assert abs(result.payload - 20.0) < 0.01

    def test_fallback_when_fx_empty(self) -> None:
        """When FX data is empty, falls back to local currency YTD."""
        prices = _make_price_result([100.0, 120.0])
        baseline = _make_baseline_result(100.0)
        fx = FxRateWindow(usd_try=None, usd_rub=None)

        result = calculate_ytd_change_usd(prices, baseline, "TRY", fx)

        # Fallback uses local: (120-100)/100*100 = 20%
        assert result.is_success
        assert result.payload is not None
        assert abs(result.payload - 20.0) < 0.01

    def test_error_when_price_result_failed(self) -> None:
        """Returns error when the price result itself is an error."""
        rng = DateRange(start=pd.Timestamp("2025-01-01").date(), end=pd.Timestamp("2025-01-31").date())
        prices = error_result("timeout", rng)
        baseline = _make_baseline_result(100.0)
        fx = _make_fx_rates(try_rates=[10.0, 10.0])

        result = calculate_ytd_change_usd(prices, baseline, "TRY", fx)

        assert not result.is_success
        assert result.error_code == "insufficient_data"

    def test_error_when_baseline_zero(self) -> None:
        """Edge case: baseline price is zero (division by zero guard)."""
        prices = _make_price_result([100.0, 120.0])
        baseline = _make_baseline_result(0.0)
        fx = _make_fx_rates(try_rates=[10.0, 10.0])

        result = calculate_ytd_change_usd(prices, baseline, "TRY", fx)

        assert not result.is_success
        assert result.error_code == "insufficient_data"

    def test_error_when_baseline_negative(self) -> None:
        """Edge case: negative baseline is rejected."""
        prices = _make_price_result([100.0, 120.0])
        baseline = _make_baseline_result(-50.0)
        fx = _make_fx_rates(try_rates=[10.0, 10.0])

        result = calculate_ytd_change_usd(prices, baseline, "TRY", fx)

        assert not result.is_success

    def test_error_when_price_series_empty(self) -> None:
        """Edge case: empty price series."""
        rng = DateRange(start=pd.Timestamp("2025-01-01").date(), end=pd.Timestamp("2025-01-31").date())
        empty_series = pd.Series([], dtype=float, name="Close")
        prices = success_result(empty_series, rng, rng)
        baseline = _make_baseline_result(100.0)
        fx = _make_fx_rates(try_rates=[10.0])

        result = calculate_ytd_change_usd(prices, baseline, "TRY", fx)

        assert not result.is_success
