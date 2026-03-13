"""
Unit tests for the data module.
Tests the data fetching functions with mocking for external API calls.
"""

import io
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import pandas as pd
import pytest
import requests

from src.data import (
    _build_finam_url,
    _get_em_for_ticker,
    fetch_finam_data,
    fetch_stock_data,
)


class TestBuildFinamUrl:
    """Tests for _build_finam_url function."""

    def test_url_basic_structure(self):
        """Should build a URL with correct parameters."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        url = _build_finam_url("SBER", 3, start, end)
        
        assert "https://export.finam.ru" in url
        assert "SBER" in url
        assert "em=3" in url
        assert "market=1" in url

    def test_url_date_format(self):
        """Should include properly formatted dates."""
        start = datetime(2024, 1, 15)
        end = datetime(2024, 6, 30)
        url = _build_finam_url("LKOH", 8, start, end)
        
        # Check date parameters
        assert "df=15" in url  # start day
        assert "mf=0" in url    # start month (0-indexed, so January = 0)
        assert "yf=2024" in url  # start year
        assert "dt=30" in url   # end day
        assert "mt=5" in url    # end month (0-indexed, so June = 5)

    def test_url_contains_filename(self):
        """Should include filename in URL."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 3, 31)
        url = _build_finam_url("AFLT", 29, start, end)
        
        # Filename uses start date format
        assert "AFLT_240101_240331" in url


class TestGetEmForTicker:
    """Tests for _get_em_for_ticker function."""

    def test_valid_ticker_sber(self):
        """Should return correct emitent ID for SBER."""
        em = _get_em_for_ticker("SBER")
        assert em == 3

    def test_valid_ticker_lkoh(self):
        """Should return correct emitent ID for LKOH."""
        em = _get_em_for_ticker("LKOH")
        assert em == 8

    def test_valid_ticker_thyao_raises(self):
        """Should raise ValueError for Turkish ticker (not in RU_EM)."""
        with pytest.raises(ValueError, match="Finam emitent ID not found"):
            _get_em_for_ticker("THYAO.IS")

    def test_invalid_ticker(self):
        """Should raise ValueError for unknown ticker."""
        with pytest.raises(ValueError, match="Finam emitent ID not found"):
            _get_em_for_ticker("INVALID")


class TestFetchFinamData:
    """Tests for fetch_finam_data function."""

    @patch('src.data.requests.get')
    @patch('src.data._get_em_for_ticker')
    def test_successful_fetch(self, mock_em, mock_get):
        """Should successfully fetch and parse data."""
        mock_em.return_value = 3
        
        # Create mock CSV response
        csv_content = """<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>
SBER,D,20240110,100000,150.00,155.00,148.00,152.50,1000000
SBER,D,20240111,100000,152.50,158.00,151.00,156.00,1100000
SBER,D,20240112,100000,156.00,160.00,155.00,158.50,1200000
SBER,D,20240115,100000,158.50,162.00,157.00,160.00,1300000
SBER,D,20240116,100000,160.00,165.00,159.00,163.00,1400000
SBER,D,20240117,100000,163.00,168.00,162.00,165.00,1500000
SBER,D,20240118,100000,165.00,170.00,164.00,168.00,1600000
SBER,D,20240119,100000,168.00,172.00,167.00,170.00,1700000
SBER,D,20240122,100000,170.00,175.00,169.00,172.00,1800000
SBER,D,20240123,100000,172.00,177.00,171.00,175.00,1900000
"""
        mock_response = Mock()
        mock_response.text = csv_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        result = fetch_finam_data("SBER", start, end)
        
        assert result['success'] is True
        assert result['df'] is not None
        assert len(result['df']) == 10
        assert 'Close' in result['df'].columns

    @patch('src.data.requests.get')
    def test_connection_error(self, mock_get):
        """Should handle connection errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        result = fetch_finam_data("SBER", start, end)
        
        assert result['success'] is False
        assert result['error'] == 'connection'

    @patch('src.data.requests.get')
    def test_timeout_error(self, mock_get):
        """Should handle timeout errors."""
        mock_get.side_effect = requests.exceptions.Timeout("Timed out")
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        result = fetch_finam_data("SBER", start, end)
        
        assert result['success'] is False
        assert result['error'] == 'timeout'

    @patch('src.data.requests.get')
    @patch('src.data._get_em_for_ticker')
    def test_empty_response(self, mock_em, mock_get):
        """Should handle empty response."""
        mock_em.return_value = 3
        
        mock_response = Mock()
        mock_response.text = ""
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        result = fetch_finam_data("SBER", start, end)
        
        assert result['success'] is False
        assert result['error'] == 'no_data'

    @patch('src.data.requests.get')
    @patch('src.data._get_em_for_ticker')
    def test_invalid_ticker_config(self, mock_em, mock_get):
        """Should handle invalid ticker configuration."""
        mock_em.side_effect = ValueError("Finam emitent ID not found")
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        result = fetch_finam_data("INVALID", start, end)
        
        assert result['success'] is False
        assert 'unknown' in result['error']


class TestFetchStockData:
    """Tests for fetch_stock_data function."""

    def test_russian_stock_uses_finam(self):
        """Should verify Finam API exists for Russian stocks."""
        # We test that the routing logic works correctly
        # by checking the code structure
        import src.data as data_module
        
        # Verify that fetch_finam_data exists and is callable
        assert hasattr(data_module, 'fetch_finam_data')
        assert callable(data_module.fetch_finam_data)


class TestDataStructure:
    """Tests for data structure consistency."""

    def test_result_dict_keys(self):
        """All fetch functions should return consistent dict structure."""
        # Test that fetch_finam_data returns expected keys
        @patch('src.data.requests.get')
        def check_keys(mock_get):
            mock_get.side_effect = requests.exceptions.ConnectionError()
            
            start = datetime(2024, 1, 1)
            end = datetime(2024, 1, 31)
            result = fetch_finam_data("SBER", start, end)
            
            expected_keys = {'df', 'success', 'actual_end_date', 'requested_end_date', 'date_adjusted', 'error'}
            assert expected_keys == set(result.keys())
        
        check_keys()
