"""
Lightweight BIST data diagnostic.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import fetch_stock_data


def check_bist_data() -> None:
    """Print a short recent snapshot for a BIST ticker."""

    ticker = "THYAO.IS"
    end_date = date.today() - timedelta(days=2)
    start_date = end_date - timedelta(days=7)
    result = fetch_stock_data(ticker, start_date, end_date, is_russian=False)

    print(f"--- BIST Detailed Check: {ticker} ---")
    if not result.is_success or result.payload is None:
        print(f"❌ Error: {result.error_code}")
        return

    print("📅 Recent Close Data:")
    for timestamp, close in result.payload.items():
        print(f"   {timestamp.strftime('%Y-%m-%d')}: {close:.2f}")


if __name__ == "__main__":
    check_bist_data()
