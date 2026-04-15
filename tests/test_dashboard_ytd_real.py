"""
Unit tests for YTD real-return conversion logic.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.dashboard import calculate_ytd_change_real
from src.models import DateRange, InflationWindow, OperationResult, error_result, success_result


def _make_price_result(
    prices: list[float],
    start: str = "2025-01-02",
) -> OperationResult[pd.Series]:
    dates = pd.date_range(start, periods=len(prices))
    series = pd.Series(prices, index=dates, name="Close")
    result_range = DateRange(start=dates[0].date(), end=dates[-1].date())
    return success_result(series, result_range, result_range)


def _make_baseline_result(value: float) -> OperationResult[Decimal]:
    baseline_day = pd.Timestamp("2025-01-01").date()
    baseline_range = DateRange(start=baseline_day, end=baseline_day)
    return success_result(Decimal(str(value)), baseline_range, baseline_range)


class TestCalculateYtdChangeReal:
    """Tests for calculate_ytd_change_real."""

    def test_happy_path_uses_shared_base_month(self) -> None:
        prices = _make_price_result([102.0, 106.0], start="2025-02-02")
        baseline = _make_baseline_result(100.0)
        inflation = InflationWindow(
            tr_cpi=pd.Series(
                [101.0, 103.0],
                index=pd.to_datetime(["2025-01-01", "2025-02-01"]),
            ),
            ru_cpi=pd.Series(
                [110.0, 111.0],
                index=pd.to_datetime(["2025-01-01", "2025-02-01"]),
            ),
            shared_base_month=pd.Timestamp("2025-02-01"),
        )

        result = calculate_ytd_change_real(prices, baseline, "TR", inflation)

        assert result.is_success
        assert result.payload is not None
        assert abs(result.payload - 3.941747573) < 0.01

    def test_returns_inflation_incomplete_when_baseline_month_missing(self) -> None:
        prices = _make_price_result([102.0, 106.0], start="2025-02-02")
        baseline = _make_baseline_result(100.0)
        inflation = InflationWindow(
            tr_cpi=pd.Series([103.0], index=pd.to_datetime(["2025-02-01"])),
            ru_cpi=pd.Series([111.0], index=pd.to_datetime(["2025-02-01"])),
            shared_base_month=pd.Timestamp("2025-02-01"),
        )

        result = calculate_ytd_change_real(prices, baseline, "TR", inflation)

        assert not result.is_success
        assert result.error_code == "inflation_incomplete"

    def test_returns_insufficient_data_when_price_result_failed(self) -> None:
        requested_range = DateRange(
            start=pd.Timestamp("2025-01-01").date(),
            end=pd.Timestamp("2025-01-31").date(),
        )
        prices = error_result("timeout", requested_range)
        baseline = _make_baseline_result(100.0)
        inflation = InflationWindow(
            tr_cpi=pd.Series([101.0], index=pd.to_datetime(["2025-01-01"])),
            ru_cpi=pd.Series([111.0], index=pd.to_datetime(["2025-01-01"])),
            shared_base_month=pd.Timestamp("2025-01-01"),
        )

        result = calculate_ytd_change_real(prices, baseline, "TR", inflation)

        assert not result.is_success
        assert result.error_code == "insufficient_data"
