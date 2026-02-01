"""
Commodity Service v2 - with period selection
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import requests


@dataclass
class CommodityData:
    """원자재 가격 데이터"""
    symbol: str
    name: str
    current_price: Optional[float]
    currency: str
    change_percent: Optional[float]
    history: List[Tuple[str, float]]
    error: Optional[str] = None


def fetch_commodity_via_yahoo(symbol: str, name: str, days: int = 30) -> CommodityData:
    """
    Yahoo Finance API로 원자재 가격 조회
    
    Args:
        symbol: Yahoo Finance 심볼
        name: 표시용 이름
        days: 조회할 기간 (일)
    """
    try:
        end_date = int(datetime.now().timestamp())
        start_date = int((datetime.now() - timedelta(days=days)).timestamp())
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"period1": start_date, "period2": end_date, "interval": "1d"}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        result = data.get("chart", {}).get("result", [])
        if not result:
            return CommodityData(symbol, name, None, "USD", None, [], error="데이터 없음")
        
        meta = result[0].get("meta", {})
        indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
        timestamps = result[0].get("timestamp", [])
        closes = indicators.get("close", [])
        
        current_price = meta.get("regularMarketPrice")
        prev_close = meta.get("previousClose", current_price)
        change_percent = ((current_price - prev_close) / prev_close * 100) if prev_close else None
        currency = meta.get("currency", "USD")
        
        history = []
        for ts, close in zip(timestamps, closes):
            if close is not None:
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                history.append((date_str, close))
        
        return CommodityData(
            symbol=symbol, name=name, current_price=current_price,
            currency=currency, change_percent=change_percent, history=history,
        )
    except Exception as e:
        return CommodityData(symbol, name, None, "USD", None, [], error=str(e))


def get_all_commodities(days: int = 30) -> dict:
    """주요 원자재 4종 조회"""
    commodities = {
        "gold": ("GC=F", "금 (Gold)"),
        "oil": ("CL=F", "원유 (WTI)"),
        "copper": ("HG=F", "구리 (Copper)"),
        "natgas": ("NG=F", "천연가스"),
    }
    return {key: fetch_commodity_via_yahoo(sym, name, days) for key, (sym, name) in commodities.items()}
