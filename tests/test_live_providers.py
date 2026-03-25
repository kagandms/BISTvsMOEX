"""
Optional live-provider integration tests.
Run explicitly with: pytest -m live
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.data import fetch_stock_data, fetch_usd_rates


@pytest.mark.live
def test_live_bist_fetch_returns_typed_result() -> None:
    end_date = date.today() - timedelta(days=3)
    start_date = end_date - timedelta(days=10)

    result = fetch_stock_data("THYAO.IS", start_date, end_date, is_russian=False)

    assert result.status in {"success", "error"}
    assert result.requested_range is not None


@pytest.mark.live
def test_live_fx_fetch_returns_typed_result() -> None:
    end_date = date.today() - timedelta(days=3)
    start_date = end_date - timedelta(days=10)

    result = fetch_usd_rates(start_date, end_date)

    assert result.status in {"success", "error"}
    assert result.requested_range is not None
