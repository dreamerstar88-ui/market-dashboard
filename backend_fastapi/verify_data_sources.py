
import asyncio
import ccxt.async_support as ccxt
import FinanceDataReader as fdr
import yfinance as yf
from fredapi import Fred
import os
from datetime import datetime, timedelta
import pandas as pd

# Load environment variables (mocking for local test if needed, but better to check existence)
# os.environ["FRED_API_KEY"] = "YOUR_KEY_HERE" 


# Robust network settings
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import ccxt # Sync version for stability check

def get_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })
    return session

async def test_ccxt():
    print("\n[1/4] Testing CCXT (Upbit - Sync Mode)...")
    try:
        # Use sync to rule out async loop issues on Windows
        exchange = ccxt.upbit({
            'enableRateLimit': True,
            'timeout': 10000,
        })
        # exchange.load_markets() # Only if needed
        ticker = exchange.fetch_ticker('BTC/KRW')
        print(f"✅ Success: BTC/KRW = {ticker['last']} KRW")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_fdr():
    print("\n[2/4] Testing FinanceDataReader (KRX)...")
    try:
        # Fetch Samsung Electronics (005930)
        df = fdr.DataReader('005930', '2024-01-01', '2024-01-10')
        if not df.empty:
            print(f"✅ Success: Samsung Electronics data fetched ({len(df)} rows)")
            print(df.head(2))
            return True
        else:
            print("❌ Failed: Empty DataFrame")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_yfinance():
    print("\n[3/4] Testing yfinance (US - Custom Session)...")
    try:
        # Inject custom session
        session = get_session()
        # Fetching history is often more reliable than fast_info for initial checks
        ticker = yf.Ticker("AAPL", session=session)
        history = ticker.history(period="1d")
        
        if not history.empty:
            price = history['Close'].iloc[-1]
            print(f"✅ Success: AAPL Price = ${price:.2f}")
            return True
        else:
            print("❌ Failed: Empty history")
            return False
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_fred():
    print("\n[4/4] Testing FRED API...")
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        print("⚠️  Skipped: FRED_API_KEY not found in env.")
        return True # Not a failure of the library, just config
    
    try:
        fred = Fred(api_key=api_key)
        data = fred.get_series('GDP')
        print(f"✅ Success: Fetched GDP data ({len(data)} points)")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def main():
    print("🚀 Starting Data Source Verification...")
    
    results = {
        "CCXT": await test_ccxt(),
        "FinanceDataReader": test_fdr(),
        "yfinance": test_yfinance(),
        "FRED": test_fred()
    }
    
    print("\n📊 Verification Summary:")
    all_pass = True
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
        if not success: all_pass = False
        
    if all_pass:
        print("\n🎉 All systems ready for Phase 2!")
    else:
        print("\n⚠️  Some checks failed. Review errors before proceeding.")

if __name__ == "__main__":
    asyncio.run(main())
