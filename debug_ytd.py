from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from decimal import Decimal

from src.data import fetch_stock_data_async, fetch_ytd_start_price

logging.basicConfig(level=logging.INFO)


def calculate_ytd_change(current_price: Decimal, start_price: Decimal) -> Decimal:
    """Calculate YTD performance for a debug run."""
    if start_price <= 0:
        return Decimal("0.0")

    return ((current_price - start_price) / start_price) * Decimal("100")


async def debug_ytd() -> None:
    """Run a lightweight YTD diagnostic for one BIST and one MOEX asset."""

    print("🚀 Debugging YTD Calculation...")
    current_year = datetime.now().year
    start_date = datetime(current_year, 1, 1)
    end_date = datetime(current_year, 1, 20)

    assets = [
        ("🇹🇷", "THYAO.IS", False),
        ("🇷🇺", "AFLT", True),
    ]

    for flag, ticker, is_russian in assets:
        print(f"\n{flag} Testing {ticker}...")
        start_price = await fetch_ytd_start_price(ticker, is_russian=is_russian)
        print(f"   Start Price: {start_price}")

        result = await fetch_stock_data_async(ticker, start_date, datetime.now(), is_russian=is_russian)
        if not result["success"] or result["df"] is None or result["df"].empty:
            print(f"   ❌ No Data Found or Error: {result.get('error')}")
            continue

        current_price = Decimal(str(result["df"].iloc[-1]["Close"]))
        ytd_change = calculate_ytd_change(current_price, start_price)
        print(f"   Current Price: {current_price}")
        print(f"   YTD Change: {ytd_change:.2f}%")

        january_window = await fetch_stock_data_async(
            ticker,
            start_date,
            end_date,
            is_russian=is_russian
        )
        if january_window["success"] and january_window["df"] is not None and not january_window["df"].empty:
            print(f"   First January Row: {january_window['df'].iloc[0]}")
        else:
            print(f"   January Window Error: {january_window.get('error')}")


if __name__ == "__main__":
    asyncio.run(debug_ytd())
