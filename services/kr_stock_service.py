"""
Korean Stock Service - Yahoo Finance based
TradingView 무료 위젯이 한국주식을 지원하지 않아 Yahoo Finance로 대체
"""
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Tuple


@dataclass
class KrStockData:
    """한국 주식 데이터"""
    code: str
    name: str
    current_price: Optional[float]
    change_percent: Optional[float]
    history: List[Tuple[str, float]]
    error: Optional[str] = None


# 종목코드 -> Yahoo Finance 심볼 변환 (한국주식은 .KS 또는 .KQ 접미사)
KR_STOCK_INFO = {
    "005930": ("005930.KS", "삼성전자"),
    "000660": ("000660.KS", "SK하이닉스"),
    "373220": ("373220.KS", "LG에너지솔루션"),
    "005380": ("005380.KS", "현대차"),
    "035420": ("035420.KS", "NAVER"),
    "051910": ("051910.KS", "LG화학"),
    "006400": ("006400.KS", "삼성SDI"),
    "035720": ("035720.KS", "카카오"),
    "003670": ("003670.KS", "포스코퓨처엠"),
    "068270": ("068270.KS", "셀트리온"),
    "005490": ("005490.KS", "POSCO홀딩스"),
    "028260": ("028260.KS", "삼성물산"),
    "105560": ("105560.KS", "KB금융"),
    "055550": ("055550.KS", "신한지주"),
    "034730": ("034730.KS", "SK"),
}


def get_kr_stock_name(code: str) -> str:
    """종목코드로 종목명 반환"""
    clean_code = code.replace("KRX:", "").replace(".KS", "").replace(".KQ", "")
    if clean_code in KR_STOCK_INFO:
        return KR_STOCK_INFO[clean_code][1]
    return clean_code


def fetch_kr_stock(code: str, days: int = 30) -> KrStockData:
    """
    Accelerated Data Fetching via Localhost Backend
    """
    # 코드 정리
    clean_code = code.replace("KRX:", "").replace(".KS", "").replace(".KQ", "")
    
    # 이름 조회 (기존 로직 활용)
    name = clean_code
    if clean_code in KR_STOCK_INFO:
        _, name = KR_STOCK_INFO[clean_code]

    try:
        # Call Fast Backend
        url = f"http://127.0.0.1:8000/api/v1/stocks/history/{clean_code}?days={days}"
        response = requests.get(url, timeout=2) # Fast timeout
        
        if response.status_code == 200:
            data = response.json()
            if not data:
                return KrStockData(clean_code, name, None, None, [], error="데이터 없음")
            
            # Process Data
            latest = data[-1]
            prev = data[-2] if len(data) > 1 else latest
            
            # Structure matches existing Dataclass
            history_tuples = [(d['time'], d['close']) for d in data]
            
            current_price = latest['close']
            change_percent = ((latest['close'] - prev['close']) / prev['close']) * 100
            
            return KrStockData(
                code=clean_code,
                name=name,
                current_price=current_price,
                change_percent=change_percent,
                history=history_tuples,
            )
        else:
            return KrStockData(clean_code, name, None, None, [], error=f"API Error {response.status_code}")
            
    except Exception as e:
        return KrStockData(clean_code, name, None, None, [], error=str(e))


def fetch_kr_index_history(code: str, days: int = 365) -> List[dict]:
    """
    Fetch history for indices (e.g. ^KS11) formatted for Lightweight Charts (Candlesticks)
    """
    try:
        # Backend endpoint standard: /api/v1/stocks/history/{code}
                    'high': d['high'],
                    'low': d['low'],
                    'close': d['close']
                })
            return formatted
    except Exception:
        pass
    return []
