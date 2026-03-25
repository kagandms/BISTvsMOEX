"""
Debug the selected-year YTD calculation for one BIST and one MOEX asset.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard import calculate_ytd_change
from src.data import fetch_stock_data_async, fetch_ytd_start_price


async def debug_ytd() -> None:
    """Run a YTD diagnostic for one BIST and one MOEX asset."""

    selected_end_date = date.today()
    start_date = date(selected_end_date.year, 1, 1)
    assets = [("🇹🇷", "THYAO.IS", False), ("🇷🇺", "AFLT", True)]

    print("🚀 Debugging YTD Calculation...")
    for flag, ticker, is_russian in assets:
        print(f"\n{flag} Testing {ticker}...")
        baseline = await fetch_ytd_start_price(ticker, selected_end_date, is_russian=is_russian)
        result = await fetch_stock_data_async(
            ticker,
            start_date,
            selected_end_date,
            is_russian=is_russian,
        )
        ytd_result = calculate_ytd_change(result, baseline)

        print(f"   Baseline Status: {baseline.error_code or 'success'}")
        print(f"   Price Status: {result.error_code or 'success'}")
        if ytd_result.is_success:
            print(f"   YTD Change: {ytd_result.payload:.2f}%")
        else:
            print(f"   YTD Change Unavailable: {ytd_result.error_code}")


if __name__ == "__main__":
    asyncio.run(debug_ytd())
