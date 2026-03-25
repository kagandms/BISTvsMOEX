"""
Provider diagnostic script aligned with the runtime architecture.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import fetch_stock_data, fetch_usd_rates


def print_result(label: str, result_code: str | None) -> None:
    """Print a normalized status line."""

    if result_code is None:
        print(f"   ✅ {label}")
        return

    print(f"   ❌ {label}: {result_code}")


def main() -> None:
    """Run a quick diagnostic against all active data providers."""

    end_date = date.today() - timedelta(days=3)
    start_date = end_date - timedelta(days=10)
    print("🚀 STARTING SYSTEM DIAGNOSTICS 🚀")

    bist_result = fetch_stock_data("THYAO.IS", start_date, end_date, is_russian=False)
    print_result("BIST / Yahoo Finance", bist_result.error_code)

    moex_result = fetch_stock_data("SBER", start_date, end_date, is_russian=True)
    print_result("MOEX / ISS", moex_result.error_code)

    fx_result = fetch_usd_rates(start_date, end_date)
    print_result("FX / Yahoo Finance", fx_result.error_code)

    print("🏁 DIAGNOSTICS COMPLETE")


if __name__ == "__main__":
    main()
