import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd

def check_bist_data():
    ticker = "THYAO.IS"
    print(f"--- BIST Detailed Check: {ticker} ---")
    
    try:
        stock = yf.Ticker(ticker)
        # Fetch last 5 days
        df = stock.history(period="5d", auto_adjust=False)
        
        if df.empty:
            print("❌ No data found.")
            return

        print(f"📅 Last 5 Days Data:")
        for date, row in df.iterrows():
            date_str = date.strftime('%Y-%m-%d')
            close = row['Close']
            print(f"   {date_str}: {close:.2f}")

        last_date = df.index[-1].strftime('%Y-%m-%d')
        last_price = df.iloc[-1]['Close']
        
        # Calculate return for context
        print(f"\n✅ Last Recorded Close ({last_date}): {last_price:.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_bist_data()
