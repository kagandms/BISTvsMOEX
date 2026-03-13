
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import pytest
from src.data import fetch_stock_data_async, fetch_ytd_start_price, fetch_market_cap_async

# Mock logging to avoid clutter
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_future_dates():
    """Test fetching data for a future date range."""
    print("\n🧪 Testing Future Dates...")
    future_start = datetime.now() + timedelta(days=365)
    future_end = future_start + timedelta(days=30)
    
    # Turkey
    result_tr = await fetch_stock_data_async("THYAO.IS", future_start, future_end, is_russian=False)
    assert result_tr['success'] == False
    assert result_tr['error'] in ["no_data", "insufficient_data"]
    print("   ✅ TR Future Date handled correctly.")
    
    # Russia
    result_ru = await fetch_stock_data_async("AFLT", future_start, future_end, is_russian=True)
    assert result_ru['success'] == False
    assert result_ru['error'] in ["no_data", "insufficient_data"]
    print("   ✅ RU Future Date handled correctly.")

@pytest.mark.asyncio
async def test_invalid_ticker():
    """Test fetching data for a non-existent ticker."""
    print("\n🧪 Testing Invalid Ticker...")
    start = datetime(2025, 1, 1)
    end = datetime(2025, 1, 30)
    
    # Turkey
    result_tr = await fetch_stock_data_async("INVALID_TICKER_XYZ_123.IS", start, end, is_russian=False)
    assert result_tr['success'] == False
    print(f"   ✅ TR Invalid Ticker handled (Error: {result_tr.get('error')})")

    # Russia (Finam might return no_data or api_error)
    result_ru = await fetch_stock_data_async("INVALID_12345", start, end, is_russian=True)
    # Note: Finam might mask error as empty CSV or HTML error page
    assert result_ru['success'] == False 
    print(f"   ✅ RU Invalid Ticker handled (Error: {result_ru.get('error')})")

@pytest.mark.asyncio
async def test_ytd_boundary_conditions():
    """Test YTD logic at critical boundaries."""
    print("\n🧪 Testing YTD Logic Boundaries...")
    
    # 1. Start of year (No data before Jan 1 theoretically)
    # We mock this by asking for a ticker that definitely has data
    ytd = await fetch_ytd_start_price("THYAO.IS", is_russian=False)
    assert isinstance(ytd, Decimal)
    print(f"   ✅ YTD Fetch returned Decimal: {ytd}")
    
    # 2. Invalid Ticker YTD
    ytd_fail = await fetch_ytd_start_price("INVALID_XYZ", is_russian=False)
    assert ytd_fail == Decimal("0.0")
    print("   ✅ Invalid Ticker YTD returned 0.0 safe value.")

@pytest.mark.asyncio
async def test_market_cap_fallback():
    """Test Market Cap fallback logic."""
    print("\n🧪 Testing Market Cap Fallback...")
    
    # 1. Existing Ticker (Config)
    cap = await fetch_market_cap_async("AFLT", is_russian=True)
    assert cap > 0
    print(f"   ✅ Known Ticker Cap: {cap}B")
    
    # 2. Unknown Ticker
    cap_unknown = await fetch_market_cap_async("UNKNOWN_TICKER_999", is_russian=True)
    assert cap_unknown == 0.0
    print("   ✅ Unknown Ticker Cap returned 0.0 safe value.")

if __name__ == "__main__":
    # Custom runner to executing async tests without pytest CLI complexity
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_future_dates())
        loop.run_until_complete(test_invalid_ticker())
        loop.run_until_complete(test_ytd_boundary_conditions())
        loop.run_until_complete(test_market_cap_fallback())
        print("\n🎉 ALL ROBUSTNESS TESTS PASSED!")
    finally:
        loop.close()
