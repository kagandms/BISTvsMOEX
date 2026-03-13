
import asyncio
import aiohttp
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import io

# Setup logger for the script
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

async def check_finam_connection(ticker="SBER", attempt=1):
    """Check Finam API (MOEX)"""
    # Em for SBER is 3 (usually)
    em = 3 
    base_url = "https://export.finam.ru"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)
    
    filename = f"{ticker}_test"
    params = (
        f"/{filename}.csv?"
        f"market=1&em={em}&code={ticker}&apply=0"
        f"&df={start_date.day}&mf={start_date.month-1}&yf={start_date.year}&from={start_date.strftime('%d.%m.%Y')}"
        f"&dt={end_date.day}&mt={end_date.month-1}&yt={end_date.year}&to={end_date.strftime('%d.%m.%Y')}"
        f"&p=8&f={filename}&e=.csv&cn={ticker}&dtf=1&tmf=1&MSOR=1&mstime=on&mstimever=1&sep=1&sep2=1&datf=1&at=1"
    )
    url = base_url + params
    
    print(f"\n🇷🇺 Checking MOEX (Finam) for {ticker}...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    if "Date" in text or "<DATE>" in text:
                        try:
                            df = pd.read_csv(io.StringIO(text))
                            if not df.empty and '<DATE>' in df.columns:
                                last_date = str(df.iloc[-1]['<DATE>'])
                                last_close = df.iloc[-1]['<CLOSE>']
                                print(f"   ✅ Success! {ticker} Last Date: {last_date}, Close: {last_close}")
                                return True
                            else:
                                print(f"   ⚠️ Connected, but no data or wrong format.")
                                print(f"   Sample: {text[:100]}")
                        except Exception as e:
                            print(f"   ⚠️ CSV Parse Error: {e}")
                    else:
                         print(f"   ⚠️  Response valid but unexpected content.")
                         print(f"   Sample: {text[:100]}")
                else:
                    print(f"   ❌ HTTP Error: {response.status}")
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")
    return False

def check_yfinance(ticker, name):
    """Check Yahoo Finance (BIST/Currency)"""
    print(f"\n{name} Checking ({ticker})...")
    try:
        stock = yf.Ticker(ticker)
        # Fetch last 5 days
        df = stock.history(period="5d", auto_adjust=False)
        
        if df.empty:
            print(f"   ❌ No data found for {ticker}")
            return False
            
        last_date = df.index[-1].strftime('%Y-%m-%d')
        last_close = df.iloc[-1]['Close']
        print(f"   ✅ Success! {ticker} Last Date: {last_date}, Close: {last_close:.4f}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def main():
    print("🚀 STARTING SYSTEM DIAGNOSTICS 🚀")
    
    # 1. BIST Check
    check_yfinance("THYAO.IS", "🇹🇷 BIST")
    
    # 2. Currency Check
    check_yfinance("TRY=X", "💵 USD/TRY")
    check_yfinance("RUB=X", "💵 USD/RUB")
    
    # 3. MOEX Check (Async)
    await check_finam_connection("SBER")
    
    print("\n🏁 DIAGNOSTICS COMPLETE")

if __name__ == "__main__":
    asyncio.run(main())
