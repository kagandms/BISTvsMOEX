"""
Unit tests for MOEX ISS pagination safety limit.
Validates that _MOEX_ISS_MAX_PAGES prevents unbounded fetching.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock, patch

from src.data import _MOEX_ISS_MAX_PAGES, _MOEX_ISS_PAGE_SIZE, _fetch_moex_iss_candles


def _make_full_page_response() -> Mock:
    """Build a mock response that returns a full page of data (triggers pagination)."""
    rows = [
        [f"2025-01-{i + 1:02d} 00:00:00", 100.0 + i, 105.0, 95.0, 1e9, 1_000_000,
         f"2025-01-{i + 1:02d} 00:00:00", f"2025-01-{i + 1:02d} 00:00:00"]
        for i in range(_MOEX_ISS_PAGE_SIZE)
    ]
    response = Mock(status_code=200)
    response.json.return_value = {
        "candles": {
            "columns": ["open", "close", "high", "low", "value", "volume", "begin", "end"],
            "data": rows,
        }
    }
    return response


def _make_empty_response() -> Mock:
    """Build a mock response with no candle data (signals end of pagination)."""
    response = Mock(status_code=200)
    response.json.return_value = {"candles": {"columns": [], "data": []}}
    return response


class TestPaginationLimit:
    """Tests for the MOEX ISS pagination safety limit."""

    @patch("src.data._get_moex_session")
    def test_pagination_stops_at_max_pages(self, mock_session_fn: Mock) -> None:
        """When server always returns full pages, loop must stop at MAX_PAGES."""
        mock_session = Mock()
        mock_session.get.return_value = _make_full_page_response()
        mock_session_fn.return_value = mock_session

        df = _fetch_moex_iss_candles("SBER", date(2025, 1, 1), date(2025, 12, 31))

        # Should have fetched exactly MAX_PAGES pages
        assert mock_session.get.call_count == _MOEX_ISS_MAX_PAGES
        # Should contain data (dedup by date may reduce row count)
        assert not df.empty

    @patch("src.data._get_moex_session")
    def test_pagination_stops_early_on_partial_page(self, mock_session_fn: Mock) -> None:
        """When server returns a partial page, loop stops before MAX_PAGES."""
        partial_rows = [
            ["2025-01-01 00:00:00", 100.0, 105.0, 95.0, 1e9, 1_000_000,
             "2025-01-01 00:00:00", "2025-01-01 00:00:00"],
            ["2025-01-02 00:00:00", 101.0, 106.0, 96.0, 1e9, 1_000_000,
             "2025-01-02 00:00:00", "2025-01-02 00:00:00"],
        ]
        partial_response = Mock(status_code=200)
        partial_response.json.return_value = {
            "candles": {
                "columns": ["open", "close", "high", "low", "value", "volume", "begin", "end"],
                "data": partial_rows,
            }
        }
        mock_session = Mock()
        mock_session.get.return_value = partial_response
        mock_session_fn.return_value = mock_session

        df = _fetch_moex_iss_candles("SBER", date(2025, 1, 1), date(2025, 1, 31))

        # Only 1 request needed since partial page < PAGE_SIZE
        assert mock_session.get.call_count == 1
        assert len(df) == 2

    def test_max_pages_constant_is_sane(self) -> None:
        """Safety constant covers ~40 years of trading data."""
        max_rows = _MOEX_ISS_MAX_PAGES * _MOEX_ISS_PAGE_SIZE
        # ~250 trading days/year * 40 years = 10,000
        assert max_rows >= 10_000
        # But not absurdly large (< 100 years)
        assert max_rows <= 50_000
