"""
Manual integrity checks for the typed production data flow.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard import calculate_ytd_change
from src.data import fetch_market_cap_async, fetch_stock_data_async, fetch_ytd_start_price


async def verify_integrity() -> None:
    """Run manual integrity checks against one BIST and one MOEX asset."""

    selected_end_date = date.today() - timedelta(days=3)
    start_date = selected_end_date - timedelta(days=60)
    assets = [("🇹🇷", "THYAO.IS", False), ("🇷🇺", "AFLT", True)]

    print("\n🔍 DATA INTEGRITY AUDIT\n" + "=" * 50)
    for flag, ticker, is_russian in assets:
        print(f"\n{flag} Checking {ticker}...")
        price_result = await fetch_stock_data_async(ticker, start_date, selected_end_date, is_russian=is_russian)
        baseline_result = await fetch_ytd_start_price(ticker, selected_end_date, is_russian=is_russian)
        ytd_result = calculate_ytd_change(price_result, baseline_result)
        market_cap_result = await fetch_market_cap_async(ticker, is_russian=is_russian)

        print(f"   Price Status: {price_result.error_code or 'success'}")
        print(f"   Baseline Status: {baseline_result.error_code or 'success'}")
        print(f"   YTD Status: {ytd_result.error_code or 'success'}")
        print(f"   Market Cap Status: {market_cap_result.error_code or 'success'}")

        if price_result.is_success and price_result.payload is not None:
            print(f"   Effective Window End: {price_result.payload.index[-1].strftime('%Y-%m-%d')}")
        if ytd_result.is_success:
            print(f"   YTD Change: {ytd_result.payload:.2f}%")
        if market_cap_result.is_success:
            print(f"   Market Cap: ${market_cap_result.payload:.1f}B")

    print("\n" + "=" * 50)
    print("✅ AUDIT COMPLETE")


if __name__ == "__main__":
    asyncio.run(verify_integrity())
