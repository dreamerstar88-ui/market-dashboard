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
    Yahoo Finance로 한국 주식 데이터 조회
    
    Args:
        code: 종목코드 (예: 005930, KRX:005930)
        days: 조회 기간
    """
    # 코드 정리
    clean_code = code.replace("KRX:", "").replace(".KS", "").replace(".KQ", "")
    
    # Yahoo Finance 심볼 변환
    if clean_code in KR_STOCK_INFO:
        yahoo_symbol, name = KR_STOCK_INFO[clean_code]
    else:
        yahoo_symbol = f"{clean_code}.KS"  # 기본적으로 KOSPI 가정
        name = clean_code
    
    try:
        end_date = int(datetime.now().timestamp())
        start_date = int((datetime.now() - timedelta(days=days)).timestamp())
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
        params = {"period1": start_date, "period2": end_date, "interval": "1d"}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        result = data.get("chart", {}).get("result", [])
        if not result:
            return KrStockData(clean_code, name, None, None, [], error="데이터 없음")
        
        meta = result[0].get("meta", {})
        indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
        timestamps = result[0].get("timestamp", [])
        closes = indicators.get("close", [])
        
        current_price = meta.get("regularMarketPrice")
        prev_close = meta.get("previousClose", current_price)
        change_percent = ((current_price - prev_close) / prev_close * 100) if prev_close and current_price else None
        
        history = []
        for ts, close in zip(timestamps, closes):
            if close is not None:
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                history.append((date_str, close))
        
        return KrStockData(
            code=clean_code,
            name=name,
            current_price=current_price,
            change_percent=change_percent,
            history=history,
        )
        
    except Exception as e:
        return KrStockData(clean_code, name, None, None, [], error=str(e))
