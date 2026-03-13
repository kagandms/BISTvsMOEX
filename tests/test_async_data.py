
import unittest
import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from src.data import fetch_finam_data_async

class TestAsyncDataByFinam(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_finam_async_success(self):
        """Test successful async fetch from Finam."""
        ticker = "SBER"
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 10)
        
        # Mock aiohttp ClientSession
        with patch('aiohttp.ClientSession') as MockSession:
            session = MockSession.return_value
            session.__aenter__.return_value = session
            session.__aexit__.return_value = None
            
            # Mock get response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = """<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>
SBER,D,20240101,000000,100,105,95,102,1000
SBER,D,20240102,000000,102,108,100,105,1200
SBER,D,20240103,000000,105,110,104,108,1300
SBER,D,20240104,000000,108,112,106,110,1400
SBER,D,20240105,000000,110,115,109,112,1500
"""
            session.get.return_value.__aenter__.return_value = mock_response
            
            # We also need to mock _get_em_for_ticker or ensure SBER is in SECTORS (it is)
            # But let's patch it just in case config is separate
            with patch('src.data._get_em_for_ticker', return_value=3):
                result = await fetch_finam_data_async(ticker, start, end)
                
                self.assertTrue(result['success'])
                self.assertIsNotNone(result['df'])
                self.assertEqual(len(result['df']), 5)
                self.assertTrue('Close' in result['df'].columns)

    async def test_fetch_finam_async_timeout(self):
        """Test timeout handling in async fetch."""
        ticker = "SBER"
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 10)
        
        with patch('aiohttp.ClientSession') as MockSession:
            session = MockSession.return_value
            session.__aenter__.return_value = session
            session.__aexit__.return_value = None
            
            # Simulate generic exception that leads us to check for timeout manually in loop
            # Or better, asyncio.TimeoutError raised by session.get
            import asyncio
            session.get.side_effect = asyncio.TimeoutError()
            
            with patch('src.data._get_em_for_ticker', return_value=3):
                # We need to speed up retries for test, but keep base_url
                new_finam_config = {
                    'base_url': 'http://test',
                    'timeout_seconds': 0.1,
                    'max_retries': 2,
                    'retry_delay_seconds': 0.01
                }
                with patch.dict('src.data.API_CONFIG', {'finam': new_finam_config}):
                    # Mock response to raise TimeoutError
                    # Note: aiohttp.ClientSession.get returns a context manager
                    # When we await session.get(), it enters __aenter__
                    # raises asyncio.TimeoutError
                    
                    # We need to mock the session.get to raise TimeoutError when awaited or entered
                    # session.get(...) is a context manager.
                    
                    # More robust mock for aiohttp client
                    mock_get_ctx = MagicMock()
                    mock_get_ctx.__aenter__.side_effect = asyncio.TimeoutError()
                    session.get.return_value = mock_get_ctx

                    result = await fetch_finam_data_async(ticker, start, end)
                    
                    self.assertFalse(result['success'])
                    self.assertEqual(result['error'], 'timeout')

