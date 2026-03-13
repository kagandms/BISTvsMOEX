
import asyncio
import logging
from decimal import Decimal
from datetime import datetime
from src.data import fetch_ytd_start_price, fetch_stock_data_async
from src.config import MARKET_CAPS

# Configure logging
logging.basicConfig(level=logging.INFO)

async def verify_integrity():
    print("\n🔍 DATA INTEGRITY AUDIT (VERİ DOĞRULAMA DENETİMİ)\n" + "="*50)
    
    # Test Parameters (Aviation Sector)
    tr_ticker = "THYAO.IS"
    ru_ticker = "AFLT" # Finam symbol for Aeroflot
    
    print(f"\n1. 📊 YTD PERFORMANCE CHECKS")
    print("-" * 30)
    
    # --- TURKEY ---
    print(f"\n🇹🇷 Checking {tr_ticker}...")
    # 1. Fetch Start Price
    tr_start_price = await fetch_ytd_start_price(tr_ticker, is_russian=False)
    print(f"   📅 Jan 2026 Start Price: {tr_start_price}")
    
    # 2. Fetch Current Price
    tr_data = await fetch_stock_data_async(tr_ticker, datetime(2026, 2, 1), datetime.now(), is_russian=False)
    if tr_data['success']:
        tr_current = Decimal(str(tr_data['df'].iloc[-1]['Close']))
        tr_date = tr_data['df'].index[-1].strftime('%Y-%m-%d')
        print(f"   📅 Current Price ({tr_date}): {tr_current}")
        
        # Calculate
        if tr_start_price > 0:
            change = ((tr_current - tr_start_price) / tr_start_price) * 100
            print(f"   🧮 Calculated YTD: {change:.2f}%")
        else:
            print("   ⚠️ Start price is 0, cannot calculate.")
            
    # --- RUSSIA ---
    print(f"\n🇷🇺 Checking {ru_ticker}...")
    # 1. Fetch Start Price
    ru_start_price = await fetch_ytd_start_price(ru_ticker, is_russian=True)
    print(f"   📅 Jan 2026 Start Price: {ru_start_price}")
    
    # 2. Fetch Current Price
    ru_data = await fetch_stock_data_async(ru_ticker, datetime(2026, 2, 1), datetime.now(), is_russian=True)
    if ru_data['success']:
        ru_current = Decimal(str(ru_data['df'].iloc[-1]['Close']))
        ru_date = ru_data['df'].index[-1].strftime('%Y-%m-%d')
        print(f"   📅 Current Price ({ru_date}): {ru_current}")
        
        # Calculate
        if ru_start_price > 0:
            change = ((ru_current - ru_start_price) / ru_start_price) * 100
            print(f"   🧮 Calculated YTD: {change:.2f}%")
        else:
             print("   ⚠️ Start price is 0, cannot calculate.")

    print(f"\n\n2. 🏛️ MARKET CAP CHECKS (STATIC CONFIG)")
    print("-" * 30)
    print(f"Values sourced from manual config (Estimates for Feb 2026):")
    
    # Check Aviation
    print(f"\n✈️ Aviation Sector:")
    print(f"   🇹🇷 THYAO: ${MARKET_CAPS.get(tr_ticker, 'N/A')} Billion")
    print(f"   🇷🇺 AFLT:  ${MARKET_CAPS.get(ru_ticker, 'N/A')} Billion")
    
    
    print("\n" + "="*50)
    print("✅ AUDIT COMPLETE")

if __name__ == "__main__":
    asyncio.run(verify_integrity())
