"""
Unit tests for conversion behaviour.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.data import convert_to_real, convert_to_usd
from src.models import FxRateWindow, InflationWindow


class TestConvertToUsd:
    """Tests for convert_to_usd."""

    def test_convert_to_usd_returns_decimal_series(self) -> None:
        dates = pd.date_range("2024-01-01", periods=3)
        prices = pd.Series([100.0, 200.0, 300.0], index=dates, name="price")
        rates = FxRateWindow(
            usd_try=pd.DataFrame({"USD_TRY": [10.0, 20.0, 30.0]}, index=dates),
            usd_rub=None,
        )

        result = convert_to_usd(prices, "TRY", rates)

        assert len(result) == 3
        assert isinstance(result.iloc[0], Decimal)
        assert result.iloc[0] == Decimal("10")
        assert result.iloc[1] == Decimal("10")
        assert result.iloc[2] == Decimal("10")

    def test_rub_conversion_works(self) -> None:
        dates = pd.date_range("2024-01-01", periods=2)
        prices = pd.Series([5000.0, 6000.0], index=dates, name="price")
        rates = FxRateWindow(
            usd_try=None,
            usd_rub=pd.DataFrame({"USD_RUB": [100.0, 200.0]}, index=dates),
        )

        result = convert_to_usd(prices, "RUB", rates)

        assert result.iloc[0] == Decimal("50")
        assert result.iloc[1] == Decimal("30")

    def test_missing_opening_fx_observation_shrinks_window(self) -> None:
        price_dates = pd.date_range("2024-01-01", periods=3)
        prices = pd.Series([100.0, 120.0, 150.0], index=price_dates, name="price")
        rates = FxRateWindow(
            usd_try=pd.DataFrame({"USD_TRY": [15.0]}, index=pd.to_datetime(["2024-01-03"])),
            usd_rub=None,
        )

        result = convert_to_usd(prices, "TRY", rates)

        assert len(result) == 1
        assert result.index[0] == pd.Timestamp("2024-01-03")
        assert result.iloc[0] == Decimal("10")

    def test_missing_rates_fail_closed(self) -> None:
        dates = pd.date_range("2024-01-01", periods=1)
        prices = pd.Series([100.0], index=dates)
        rates = FxRateWindow(usd_try=None, usd_rub=None)

        result = convert_to_usd(prices, "TRY", rates)

        assert result.empty

    def test_missing_trailing_fx_observation_does_not_forward_fill_latest_price(self) -> None:
        price_dates = pd.date_range("2024-01-01", periods=3)
        prices = pd.Series([100.0, 120.0, 150.0], index=price_dates, name="price")
        rates = FxRateWindow(
            usd_try=pd.DataFrame({"USD_TRY": [10.0, 12.0]}, index=price_dates[:2]),
            usd_rub=None,
        )

        result = convert_to_usd(prices, "TRY", rates)

        assert result.index.tolist() == [
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-01-02"),
        ]
        assert result.iloc[-1] == Decimal("10")


class TestConvertToReal:
    """Tests for convert_to_real."""

    def test_convert_to_real_uses_shared_base_month(self) -> None:
        prices = pd.Series(
            [100.0, 110.0, 120.0],
            index=pd.to_datetime(["2025-04-10", "2025-05-10", "2025-06-10"]),
        )
        cpi = pd.Series(
            [103.0, 104.03, 105.0703],
            index=pd.to_datetime(["2025-04-01", "2025-05-01", "2025-06-01"]),
        )
        inflation = InflationWindow(
            tr_cpi=cpi,
            ru_cpi=cpi,
            shared_base_month=pd.Timestamp("2025-06-01"),
        )

        result = convert_to_real(prices, "TR", inflation)

        assert len(result) == 3
        assert round(float(result.iloc[0]), 4) == round(100.0 * 105.0703 / 103.0, 4)
        assert round(float(result.iloc[-1]), 4) == 120.0

    def test_convert_to_real_trims_dates_beyond_shared_base_month(self) -> None:
        prices = pd.Series(
            [100.0, 110.0, 120.0],
            index=pd.to_datetime(["2025-12-10", "2026-01-10", "2026-03-10"]),
        )
        cpi = pd.Series(
            [101.0, 103.0],
            index=pd.to_datetime(["2025-12-01", "2026-01-01"]),
        )
        inflation = InflationWindow(
            tr_cpi=cpi,
            ru_cpi=cpi,
            shared_base_month=pd.Timestamp("2026-01-01"),
        )

        result = convert_to_real(prices, "TR", inflation)

        assert result.index.tolist() == [
            pd.Timestamp("2025-12-10"),
            pd.Timestamp("2026-01-10"),
        ]

    def test_convert_to_real_fails_closed_when_month_is_missing(self) -> None:
        prices = pd.Series(
            [100.0, 110.0],
            index=pd.to_datetime(["2025-04-10", "2025-05-10"]),
        )
        cpi = pd.Series([103.0], index=pd.to_datetime(["2025-04-01"]))
        inflation = InflationWindow(
            tr_cpi=cpi,
            ru_cpi=cpi,
            shared_base_month=pd.Timestamp("2025-05-01"),
        )

        result = convert_to_real(prices, "TR", inflation)

        assert result.empty
