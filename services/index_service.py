"""
Index Service v2 - Stable Fetching from Yahoo Finance
"""
import requests
import json
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class IndexData:
    symbol: str
    name: str
    current_price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    error: Optional[str] = None


def fetch_index(symbol: str, name: str) -> IndexData:
    """
    Yahoo Finance에서 지수 데이터 가져오기 (헤더 강화)
    """
    try:
        # query2가 더 안정적일 수 있음
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://finance.yahoo.com/"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # 404/401 에러 등이 발생할 경우 query1으로 백업
        if response.status_code != 200:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            response = requests.get(url, headers=headers, timeout=10)
        
        response.raise_for_status()
        data = response.json()
        result = data.get("chart", {}).get("result", [])
        
        if result:
            meta = result[0].get("meta", {})
            current_price = meta.get("regularMarketPrice")
            previous_close = meta.get("previousClose")
            
            # 가격 정보가 없을 경우 indicators 확인
            if current_price is None:
                adjclose = result[0].get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
                if adjclose:
                    current_price = adjclose[-1]
            
            if current_price:
                # Yahoo Finance가 제공하는 변동률 직접 사용 (더 정확)
                change = meta.get("regularMarketChange")
                change_percent = meta.get("regularMarketChangePercent")
                
                # 폴백: 직접 계산
                if change is None or change_percent is None:
                    if previous_close is None:
                        closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
                        if len(closes) > 1:
                            previous_close = closes[0]
                    
                    if previous_close:
                        change = current_price - previous_close
                        change_percent = (change / previous_close) * 100
                    else:
                        change = 0
                        change_percent = 0
                
                return IndexData(
                    symbol=symbol,
                    name=name,
                    current_price=current_price,
                    change=change,
                    change_percent=change_percent
                )
        
        return IndexData(symbol=symbol, name=name, error="데이터 구조 파싱 실패")
        
    except Exception as e:
        return IndexData(symbol=symbol, name=name, error=f"통신 오류: {str(e)[:50]}")


def get_us_indices() -> List[IndexData]:
    """미국 주요 지수 (S&P 500, NASDAQ, Dow Jones)"""
    indices = [
        ("^IXIC", "NASDAQ"),
        ("^GSPC", "S&P 500"),
        ("^DJI", "Dow Jones"),
    ]
    return [fetch_index(sym, name) for sym, name in indices]


def get_kr_indices() -> List[IndexData]:
    """한국 주요 지수 (KOSPI, KOSDAQ) - 5일 데이터로 변동률 계산"""
    indices = [
        ("^KS11", "KOSPI"),
        ("^KQ11", "KOSDAQ"),
    ]
    results = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    
    for symbol, name in indices:
        try:
            # 5일 데이터로 전일 종가 확보
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            result = data.get("chart", {}).get("result", [])
            
            if result:
                meta = result[0].get("meta", {})
                current_price = meta.get("regularMarketPrice")
                closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
                
                # 유효한 close 값만 필터링
                valid_closes = [c for c in closes if c is not None]
                
                if current_price and len(valid_closes) >= 2:
                    previous_close = valid_closes[-2]  # 전일 종가
                    change = current_price - previous_close
                    change_percent = (change / previous_close) * 100
                    
                    results.append(IndexData(
                        symbol=symbol,
                        name=name,
                        current_price=current_price,
                        change=change,
                        change_percent=change_percent
                    ))
                else:
                    results.append(IndexData(symbol=symbol, name=name, current_price=current_price, change=0, change_percent=0))
            else:
                results.append(IndexData(symbol=symbol, name=name, error="데이터 없음"))
                
        except Exception as e:
            results.append(IndexData(symbol=symbol, name=name, error=f"오류: {str(e)[:30]}"))
    
    return results
