import sys
sys.path.append('.')
import traceback
import yfinance as yf
from datetime import datetime, timedelta

try:
    print("Testing KOSPI with yfinance (^KS11)...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    df = yf.download("^KS11", start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    print(df.tail())
except Exception as e:
    print(f"yfinance KS11 Error: {e}")
    traceback.print_exc()

try:
    print("\nTesting KOSDAQ with yfinance (^KQ11)...")
    df = yf.download("^KQ11", start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    print(df.tail())
except Exception as e:
    print(f"yfinance KQ11 Error: {e}")
    traceback.print_exc()
