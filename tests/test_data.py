"""
Unit tests for the data layer.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock, patch

import pandas as pd
import requests as http_requests
from curl_cffi import requests as curl_requests

from src.data import (
    _fetch_moex_iss_candles,
    fetch_inflation_window,
    fetch_moex_iss_data,
    fetch_stock_data,
    fetch_usd_rates,
)


def _make_moex_json(rows: list[tuple[str, float]]) -> dict:
    """Build a minimal MOEX ISS payload."""

    data = [[row[0], row[1], row[1] + 1, row[1] - 1, 1e9, 1_000_000, row[0], row[0]] for row in rows]
    return {
        "candles": {
            "columns": ["open", "close", "high", "low", "value", "volume", "begin", "end"],
            "data": data,
        }
    }


SAMPLE_ROWS = [
    ("2025-01-10 00:00:00", 150.00),
    ("2025-01-13 00:00:00", 152.50),
    ("2025-01-14 00:00:00", 155.00),
    ("2025-01-15 00:00:00", 158.50),
    ("2025-01-16 00:00:00", 160.00),
    ("2025-01-17 00:00:00", 163.00),
]


class TestFetchMoexIssCandles:
    """Tests for the low-level MOEX fetcher."""

    @patch("src.data._get_moex_session")
    def test_successful_single_page(self, mock_session_fn: Mock) -> None:
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = _make_moex_json(SAMPLE_ROWS)
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_fn.return_value = mock_session

        data_frame = _fetch_moex_iss_candles("SBER", date(2025, 1, 1), date(2025, 1, 31))

        assert len(data_frame) == len(SAMPLE_ROWS)
        assert "Close" in data_frame.columns
        assert data_frame.index.name == "Date"

    @patch("src.data._get_moex_session")
    def test_empty_candles_return_empty_frame(self, mock_session_fn: Mock) -> None:
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"candles": {"columns": [], "data": []}}
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_fn.return_value = mock_session

        data_frame = _fetch_moex_iss_candles("SBER", date(2025, 1, 1), date(2025, 1, 31))
        assert data_frame.empty


class TestFetchMoexIssData:
    """Tests for the public MOEX result contract."""

    @patch("src.data._get_moex_session")
    def test_successful_fetch(self, mock_session_fn: Mock) -> None:
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = _make_moex_json(SAMPLE_ROWS)
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_fn.return_value = mock_session

        result = fetch_moex_iss_data("SBER", date(2025, 1, 1), date(2025, 1, 31))

        assert result.is_success
        assert result.payload is not None
        assert len(result.payload) == len(SAMPLE_ROWS)
        assert result.error_code is None

    @patch("src.data._get_moex_session")
    def test_http_404_returns_no_data(self, mock_session_fn: Mock) -> None:
        mock_session = Mock()
        mock_session.get.return_value = Mock(status_code=404)
        mock_session_fn.return_value = mock_session

        result = fetch_moex_iss_data("INVALID", date(2025, 1, 1), date(2025, 1, 31))

        assert result.status == "error"
        assert result.error_code == "no_data"

    @patch("src.data._get_moex_session")
    def test_schema_error_is_not_masked_as_no_data(self, mock_session_fn: Mock) -> None:
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"candles": {"columns": ["open"], "data": [[1]]}}
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_fn.return_value = mock_session

        result = fetch_moex_iss_data("SBER", date(2025, 1, 1), date(2025, 1, 31))

        assert result.status == "error"
        assert result.error_code == "schema_error"

    @patch("src.data._get_moex_session")
    def test_generic_request_exception_returns_connection_error(self, mock_session_fn: Mock) -> None:
        mock_session = Mock()
        mock_session.get.side_effect = http_requests.exceptions.RequestException("transport failure")
        mock_session_fn.return_value = mock_session

        result = fetch_moex_iss_data("SBER", date(2025, 1, 1), date(2025, 1, 31))

        assert result.status == "error"
        assert result.error_code == "connection"

    def test_unsupported_window_returns_explicit_error(self) -> None:
        result = fetch_moex_iss_data("SBER", date(2025, 1, 31), date(2025, 1, 1))
        assert result.error_code == "unsupported_window"


class TestFetchStockData:
    """Tests for the provider-agnostic stock fetcher."""

    @patch("src.data._fetch_moex_iss_candles")
    def test_russian_ticker_routes_to_moex(self, mock_fetch: Mock) -> None:
        fetch_stock_data.clear()
        mock_fetch.return_value = pd.DataFrame(
            {"Close": [100.0] * 5},
            index=pd.date_range("2025-01-01", periods=5),
        )

        result = fetch_stock_data("SBER", date(2025, 1, 1), date(2025, 1, 31), is_russian=True)

        mock_fetch.assert_called_once_with("SBER", date(2025, 1, 1), date(2025, 1, 31))
        assert result.is_success

    @patch("src.data._fetch_yfinance_history")
    def test_missing_close_column_returns_schema_error(self, mock_history: Mock) -> None:
        mock_history.return_value = pd.DataFrame({"Open": [1, 2, 3]}, index=pd.date_range("2025-01-01", periods=3))

        result = fetch_stock_data("THYAO.IS", date(2025, 1, 1), date(2025, 1, 31))

        assert result.status == "error"
        assert result.error_code == "schema_error"

    @patch("src.data.yf.Ticker")
    def test_yfinance_history_uses_native_timeout(self, mock_ticker_cls: Mock) -> None:
        fetch_stock_data.clear()
        mock_ticker = mock_ticker_cls.return_value
        mock_ticker.history.return_value = pd.DataFrame(
            {"Close": [100.0] * 5},
            index=pd.date_range("2025-01-01", periods=5),
        )

        result = fetch_stock_data("THYAO.IS", date(2025, 1, 1), date(2025, 1, 31))

        assert result.is_success
        mock_ticker.history.assert_called_once_with(
            start=date(2025, 1, 1),
            end=date(2025, 2, 1),
            auto_adjust=False,
            timeout=15,
            raise_errors=True,
        )

    @patch("src.data.yf.Ticker")
    def test_yfinance_timeout_maps_to_timeout_error(self, mock_ticker_cls: Mock) -> None:
        fetch_stock_data.clear()
        mock_ticker = mock_ticker_cls.return_value
        mock_ticker.history.side_effect = curl_requests.exceptions.Timeout("timed out")

        result = fetch_stock_data("THYAO.IS", date(2025, 1, 1), date(2025, 1, 31))

        assert result.status == "error"
        assert result.error_code == "timeout"

    @patch("src.data._fetch_yfinance_history")
    def test_stock_error_result_is_not_cached(self, mock_history: Mock) -> None:
        fetch_stock_data.clear()
        bad_frame = pd.DataFrame({"Open": [1, 2, 3]}, index=pd.date_range("2025-01-01", periods=3))
        good_frame = pd.DataFrame({"Close": [100, 101, 102, 103, 104]}, index=pd.date_range("2025-01-01", periods=5))
        mock_history.side_effect = [bad_frame, good_frame]

        first_result = fetch_stock_data("THYAO.IS", date(2025, 1, 1), date(2025, 1, 31))
        second_result = fetch_stock_data("THYAO.IS", date(2025, 1, 1), date(2025, 1, 31))

        assert first_result.status == "error"
        assert first_result.error_code == "schema_error"
        assert second_result.is_success
        assert mock_history.call_count == 2


class TestFetchUsdRates:
    """Tests for FX fetching contract."""

    @patch("src.data._fetch_yfinance_history")
    def test_complete_fx_window_returns_success(self, mock_history: Mock) -> None:
        fetch_usd_rates.clear()
        try_frame = pd.DataFrame({"Close": [35.0, 35.2]}, index=pd.date_range("2025-01-01", periods=2))
        rub_frame = pd.DataFrame({"Close": [92.0, 92.5]}, index=pd.date_range("2025-01-01", periods=2))
        mock_history.side_effect = [try_frame, rub_frame]

        result = fetch_usd_rates(date(2025, 1, 1), date(2025, 1, 31))

        assert result.is_success
        assert result.payload is not None
        assert result.payload.usd_try is not None
        assert result.payload.usd_rub is not None

    @patch("src.data._fetch_yfinance_history")
    def test_fx_error_result_is_not_cached(self, mock_history: Mock) -> None:
        fetch_usd_rates.clear()
        bad_frame = pd.DataFrame({"Open": [1, 2]}, index=pd.date_range("2025-01-01", periods=2))
        good_try = pd.DataFrame({"Close": [35.0, 35.1]}, index=pd.date_range("2025-01-01", periods=2))
        good_rub = pd.DataFrame({"Close": [90.0, 90.1]}, index=pd.date_range("2025-01-01", periods=2))
        mock_history.side_effect = [bad_frame, good_rub, good_try, good_rub]

        first_result = fetch_usd_rates(date(2025, 1, 1), date(2025, 1, 31))
        second_result = fetch_usd_rates(date(2025, 1, 1), date(2025, 1, 31))

        assert first_result.status == "error"
        assert first_result.error_code == "schema_error"
        assert second_result.is_success
        assert mock_history.call_count == 4


class TestFetchInflationWindow:
    """Tests for curated inflation coverage."""

    def test_recent_window_returns_shared_cpi_base_month(self) -> None:
        result = fetch_inflation_window(date(2025, 12, 1), date(2026, 3, 15))

        assert result.is_success
        assert result.payload is not None
        assert result.payload.shared_base_month == pd.Timestamp("2026-03-01")
        assert result.is_complete

    def test_window_past_latest_shared_month_returns_partial_real_coverage(self) -> None:
        result = fetch_inflation_window(date(2025, 12, 1), date(2026, 4, 15))

        assert result.is_success
        assert result.payload is not None
        assert result.payload.shared_base_month == pd.Timestamp("2026-03-01")
        assert result.effective_range is not None
        assert result.effective_range.end == date(2026, 3, 31)
        assert not result.is_complete

    def test_window_before_snapshot_fails_closed(self) -> None:
        result = fetch_inflation_window(date(2024, 1, 1), date(2024, 2, 1))

        assert result.status == "error"
        assert result.error_code == "inflation_incomplete"
