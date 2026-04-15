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
        # Baseline TRY: 90.0, Rate on Jan 1: 9.0 => Baseline USD = 10.0
        # Price on Jan 3: 120.0, Rate on Jan 3: 10.0 => Current USD = 12.0
        # YTD USD: (12.0 - 10.0) / 10.0 = 20%
        prices = _make_price_result([100.0, 120.0], start="2025-01-02")
        baseline = _make_baseline_result(90.0)
        fx = _make_fx_rates(try_rates=[9.0, 10.0, 10.0], start="2025-01-01")

        result = calculate_ytd_change_usd(prices, baseline, "TRY", fx)

        assert result.is_success
        assert result.payload is not None
        assert abs(result.payload - 20.0) < 0.01

    def test_happy_path_rub_conversion(self) -> None:
        """RUB conversion path works correctly."""
        # Baseline RUB: 4500.0, Rate on Jan 1: 90.0 => Baseline USD = 50.0
        # Price on Jan 3: 6000.0, Rate on Jan 3: 100.0 => Current USD = 60.0
        # YTD USD: (60.0 - 50.0) / 50.0 = 20%
        prices = _make_price_result([5000.0, 6000.0], start="2025-01-02")
        baseline = _make_baseline_result(4500.0)
        fx = _make_fx_rates(rub_rates=[90.0, 100.0, 100.0], start="2025-01-01")

        result = calculate_ytd_change_usd(prices, baseline, "RUB", fx)

        assert result.is_success
        assert result.payload is not None
        assert abs(result.payload - 20.0) < 0.01

    def test_returns_conversion_incomplete_when_fx_empty(self) -> None:
        """When FX data is empty, USD YTD must fail closed."""
        prices = _make_price_result([100.0, 120.0])
        baseline = _make_baseline_result(100.0)
        fx = FxRateWindow(usd_try=None, usd_rub=None)

        result = calculate_ytd_change_usd(prices, baseline, "TRY", fx)

        assert not result.is_success
        assert result.error_code == "conversion_incomplete"

    def test_returns_conversion_incomplete_when_baseline_rate_is_missing(self) -> None:
        """Missing baseline FX coverage must not leak a local-currency YTD result."""
        prices = _make_price_result([100.0, 120.0], start="2025-01-02")
        baseline = _make_baseline_result(100.0)
        fx = _make_fx_rates(try_rates=[10.0], start="2025-01-02")

        result = calculate_ytd_change_usd(prices, baseline, "TRY", fx)

        assert not result.is_success
        assert result.error_code == "conversion_incomplete"

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
