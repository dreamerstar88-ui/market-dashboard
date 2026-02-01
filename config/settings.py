"""
GlobalMarketApp Configuration
Centralized settings for widgets, themes, and default tickers.
Adheres to 'python-pro' standards for clean execution.
"""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
JOURNAL_PATH = DATA_DIR / "journal.md"
HISTORY_PATH = DATA_DIR / "market_history.csv"

# Make sure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# App Settings
APP_TITLE = "Market Eye"
APP_ICON = "📱"
LAYOUT = "wide"  # Use 'wide' but optimize for mobile via CSS

# Default Tickers (Stocks Tab)
DEFAULT_STOCK_SYMBOL = "NASDAQ:NVDA"

# Ticker Tape Symbols (Top Bar)
TICKER_TAPE_SYMBOLS = [
    {"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"},
    {"proName": "FOREXCOM:NSXUSD", "title": "Nasdaq 100"},
    {"proName": "FX_IDC:USDKRW", "title": "USD/KRW"},
    {"proName": "BITSTAMP:BTCUSD", "title": "Bitcoin"},
    {"proName": "COMEX:GC1!", "title": "Gold"},
]

# Economic Calendar Events (Market Intel Tab)
# Importance: 0 (Low) to 1 (High, strictly relevant)
CALENDAR_IMPORTANCE_FILTER = "-1" # Show all or filter by importance in widget settings

# AI Service Settings
AI_MODEL_NAME = "gemini-2.0-flash-exp" # Fast and capable
