"""
Async data-fetching tests.
"""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pandas as pd

from src.models import FxRateWindow, build_date_range, success_result


class TestAsyncData(unittest.IsolatedAsyncioTestCase):
    """Tests for async wrappers in the data module."""

    async def test_fetch_stock_data_async_passthrough(self) -> None:
        from src.data import fetch_stock_data_async

        expected = success_result(
            pd.Series([100.0], index=pd.to_datetime(["2025-01-10"])),
            build_date_range(date(2025, 1, 1), date(2025, 1, 31)),
            build_date_range(date(2025, 1, 10), date(2025, 1, 10)),
        )

        with patch("src.data.fetch_stock_data", return_value=expected) as mock_fetch:
            result = await fetch_stock_data_async("SBER", date(2025, 1, 1), date(2025, 1, 31), is_russian=True)

        mock_fetch.assert_called_once_with("SBER", date(2025, 1, 1), date(2025, 1, 31), True)
        assert result is expected

    async def test_fetch_usd_rates_async_passthrough(self) -> None:
        from src.data import fetch_usd_rates_async

        expected = success_result(
            FxRateWindow(
                usd_try=pd.DataFrame({"USD_TRY": [35.0]}, index=pd.to_datetime(["2025-01-10"])),
                usd_rub=pd.DataFrame({"USD_RUB": [92.0]}, index=pd.to_datetime(["2025-01-10"])),
            ),
            build_date_range(date(2025, 1, 1), date(2025, 1, 31)),
            build_date_range(date(2025, 1, 1), date(2025, 1, 31)),
        )

        with patch("src.data.fetch_usd_rates", return_value=expected) as mock_fetch:
            result = await fetch_usd_rates_async(date(2025, 1, 1), date(2025, 1, 31))

        mock_fetch.assert_called_once_with(date(2025, 1, 1), date(2025, 1, 31))
        assert result is expected

    async def test_fetch_ytd_start_price_uses_selected_end_year(self) -> None:
        from src.data import fetch_ytd_start_price

        expected = success_result(
            pd.Series(
                [120.0, 121.0, 122.0, 123.0, 124.0],
                index=pd.date_range("2024-01-02", periods=5),
            ),
            build_date_range(date(2024, 1, 1), date(2024, 1, 31)),
            build_date_range(date(2024, 1, 2), date(2024, 1, 6)),
        )

        with patch("src.data.fetch_stock_data_async", return_value=expected) as mock_fetch:
            result = await fetch_ytd_start_price("THYAO.IS", date(2024, 8, 15), is_russian=False)

        mock_fetch.assert_called_once_with("THYAO.IS", date(2024, 1, 1), date(2024, 1, 31), False)
        assert result.is_success
        assert result.payload == Decimal("120.0")

    async def test_fetch_ytd_start_price_accepts_first_available_january_session(self) -> None:
        from src.data import fetch_ytd_start_price

        expected = success_result(
            pd.Series(
                [120.0, 121.0, 122.0, 123.0, 124.0],
                index=pd.date_range("2024-01-15", periods=5),
            ),
            build_date_range(date(2024, 1, 1), date(2024, 1, 31)),
            build_date_range(date(2024, 1, 15), date(2024, 1, 19)),
        )

        with patch("src.data.fetch_stock_data_async", return_value=expected):
            result = await fetch_ytd_start_price("THYAO.IS", date(2024, 8, 15), is_russian=False)

        assert result.is_success
        assert result.payload == Decimal("120.0")
        assert result.is_complete
