"""
Korean Stock Favorites Service v2
한국 주식 즐겨찾기 관리 - TradingView 호환 심볼 사용
"""
import json
from pathlib import Path
from typing import List
from config.settings import DATA_DIR

KR_FAVORITES_PATH = DATA_DIR / "kr_favorites.json"

# TradingView 한국 주식 심볼 형식: KOSPI:005930, KOSDAQ:035720
DEFAULT_KR_FAVORITES = [
    "KRX:005930",   # 삼성전자
    "KRX:000660",   # SK하이닉스  
    "KRX:373220",   # LG에너지솔루션
    "KRX:005380",   # 현대차
    "KRX:035420",   # NAVER
]

# 종목명 매핑
KR_STOCK_NAMES = {
    "KRX:005930": "삼성전자",
    "KRX:000660": "SK하이닉스",
    "KRX:373220": "LG에너지",
    "KRX:005380": "현대차",
    "KRX:035420": "NAVER",
    "KRX:051910": "LG화학",
    "KRX:006400": "삼성SDI",
    "KRX:035720": "카카오",
    "KRX:003670": "포스코퓨처엠",
    "KRX:068270": "셀트리온",
}


def load_kr_favorites() -> List[str]:
    """한국 주식 즐겨찾기 로드"""
    if KR_FAVORITES_PATH.exists():
        try:
            with open(KR_FAVORITES_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("favorites", DEFAULT_KR_FAVORITES)
        except:
            return DEFAULT_KR_FAVORITES
    return DEFAULT_KR_FAVORITES


def save_kr_favorites(favorites: List[str]) -> None:
    """한국 주식 즐겨찾기 저장"""
    with open(KR_FAVORITES_PATH, "w", encoding="utf-8") as f:
        json.dump({"favorites": favorites}, f, ensure_ascii=False, indent=2)


def add_kr_favorite(ticker: str) -> List[str]:
    """즐겨찾기 추가"""
    favorites = load_kr_favorites()
    # KRX: 접두사 추가
    if ":" not in ticker:
        ticker = f"KRX:{ticker}"
    else:
        ticker = ticker.upper()
    if ticker not in favorites:
        favorites.append(ticker)
        save_kr_favorites(favorites)
    return favorites


def remove_kr_favorite(ticker: str) -> List[str]:
    """즐겨찾기 삭제"""
    favorites = load_kr_favorites()
    if ticker in favorites:
        favorites.remove(ticker)
        save_kr_favorites(favorites)
    return favorites


def get_kr_stock_name(ticker: str) -> str:
    """종목코드로 종목명 반환"""
    return KR_STOCK_NAMES.get(ticker, ticker.split(":")[-1] if ":" in ticker else ticker)
