"""
Optional live-provider integration tests.
Run explicitly with: pytest -m live
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from src.data import fetch_stock_data, fetch_usd_rates
from src.models import FxRateWindow, OperationResult

_LIVE_END_DELAY_DAYS = 7
_LIVE_LOOKBACK_DAYS = 14


def _build_live_window() -> tuple[date, date]:
    """Build a conservative live-provider window away from partial recent sessions."""

    end_date = date.today() - timedelta(days=_LIVE_END_DELAY_DAYS)
    start_date = end_date - timedelta(days=_LIVE_LOOKBACK_DAYS)
    return start_date, end_date


def _assert_successful_price_result(
    result: OperationResult[pd.Series],
    *,
    expected_start: date,
    expected_end: date,
) -> None:
    """Assert a live price result is successful and contains usable data."""

    assert result.is_success
    assert result.error_code is None
    assert result.requested_range is not None
    assert result.requested_range.start == expected_start
    assert result.requested_range.end == expected_end
    assert result.effective_range is not None
    assert result.effective_range.start >= expected_start
    assert result.effective_range.end <= expected_end
    assert result.payload is not None
    assert not result.payload.empty
    assert len(result.payload) >= 5


def _assert_successful_fx_result(
    result: OperationResult[FxRateWindow],
    *,
    expected_start: date,
    expected_end: date,
) -> None:
    """Assert a live FX result is successful and contains both required series."""

    assert result.is_success
    assert result.error_code is None
    assert result.requested_range is not None
    assert result.requested_range.start == expected_start
    assert result.requested_range.end == expected_end
    assert result.effective_range == result.requested_range
    assert result.payload is not None
    assert result.payload.usd_try is not None
    assert result.payload.usd_rub is not None
    assert not result.payload.usd_try.empty
    assert not result.payload.usd_rub.empty


@pytest.mark.live
def test_live_bist_fetch_returns_non_empty_price_series() -> None:
    start_date, end_date = _build_live_window()

    result = fetch_stock_data("THYAO.IS", start_date, end_date, is_russian=False)

    _assert_successful_price_result(
        result,
        expected_start=start_date,
        expected_end=end_date,
    )


@pytest.mark.live
def test_live_moex_fetch_returns_non_empty_price_series() -> None:
    start_date, end_date = _build_live_window()

    result = fetch_stock_data("AFLT", start_date, end_date, is_russian=True)

    _assert_successful_price_result(
        result,
        expected_start=start_date,
        expected_end=end_date,
    )


@pytest.mark.live
def test_live_fx_fetch_returns_non_empty_rate_windows() -> None:
    start_date, end_date = _build_live_window()

    result = fetch_usd_rates(start_date, end_date)

    _assert_successful_fx_result(
        result,
        expected_start=start_date,
        expected_end=end_date,
    )
