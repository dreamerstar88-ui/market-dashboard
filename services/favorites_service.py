"""
Favorites Service - Persistent Stock Watchlist
Stores user's favorite tickers in a JSON file.
"""
import json
from pathlib import Path
from typing import List

from config.settings import DATA_DIR

FAVORITES_PATH = DATA_DIR / "favorites.json"

# Default favorites
DEFAULT_FAVORITES = ["NASDAQ:NVDA", "NASDAQ:TSLA", "NASDAQ:AAPL", "NASDAQ:TQQQ", "NASDAQ:QQQ"]


def load_favorites() -> List[str]:
    """저장된 즐겨찾기 목록을 로드합니다."""
    if FAVORITES_PATH.exists():
        try:
            with open(FAVORITES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("favorites", DEFAULT_FAVORITES)
        except (json.JSONDecodeError, KeyError):
            return DEFAULT_FAVORITES
    return DEFAULT_FAVORITES


def save_favorites(favorites: List[str]) -> None:
    """즐겨찾기 목록을 저장합니다."""
    with open(FAVORITES_PATH, "w", encoding="utf-8") as f:
        json.dump({"favorites": favorites}, f, ensure_ascii=False, indent=2)


def add_favorite(ticker: str) -> List[str]:
    """즐겨찾기에 종목을 추가합니다."""
    favorites = load_favorites()
    # Normalize ticker format
    if ":" not in ticker:
        ticker = f"NASDAQ:{ticker.upper()}"
    else:
        ticker = ticker.upper()
    
    if ticker not in favorites:
        favorites.append(ticker)
        save_favorites(favorites)
    return favorites


def remove_favorite(ticker: str) -> List[str]:
    """즐겨찾기에서 종목을 제거합니다."""
    favorites = load_favorites()
    if ticker in favorites:
        favorites.remove(ticker)
        save_favorites(favorites)
    return favorites
