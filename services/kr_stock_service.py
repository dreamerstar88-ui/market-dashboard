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
    Accelerated Data Fetching via Localhost Backend with FDR Fallback
    """
    # 코드 정리
    clean_code = code.replace("KRX:", "").replace(".KS", "").replace(".KQ", "")
    
    # 이름 조회 (기존 로직 활용)
    name = clean_code
    if clean_code in KR_STOCK_INFO:
        _, name = KR_STOCK_INFO[clean_code]

    # 1차 시도: Backend API
    try:
        url = f"http://127.0.0.1:8000/api/v1/stocks/history/{clean_code}?days={days}"
        response = requests.get(url, timeout=2)  # 빠른 실패를 위해 2초
        
        if response.status_code == 200:
            data = response.json()
            if data:
                latest = data[-1]
                prev = data[-2] if len(data) > 1 else latest
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
    except Exception:
        pass  # 폴백으로 진행

    # 2차 시도: FinanceDataReader 직접 호출 (호스팅 환경용)
    try:
        import FinanceDataReader as fdr
        from datetime import datetime, timedelta
        
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = fdr.DataReader(clean_code, start_date)
        
        if df is not None and len(df) > 0:
            df = df.dropna()
            history_tuples = [(idx.strftime("%Y-%m-%d"), row['Close']) for idx, row in df.iterrows()]
            
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            current_price = float(latest['Close'])
            change_percent = ((latest['Close'] - prev['Close']) / prev['Close']) * 100
            
            return KrStockData(
                code=clean_code,
                name=name,
                current_price=current_price,
                change_percent=float(change_percent),
                history=history_tuples,
            )
    except Exception as e:
        return KrStockData(clean_code, name, None, None, [], error=f"데이터 로딩 실패: {str(e)[:30]}")


def fetch_kr_index_history(code: str, days: int = 365) -> List[dict]:
    """
    백엔드 API를 통해 지수 이력 데이터 조회 (실패 시 네이버 금융 API 폴백)
    """
    import requests
    import json
    from datetime import datetime
    
    target_code = code
    if code == "KOSPI": target_code = "KOSPI" 
    elif code == "KOSDAQ": target_code = "KOSDAQ" 
    
    # 1. Try Backend API (localhost)
    url = f"http://127.0.0.1:8000/api/v1/stocks/history/{target_code}?days={days}"
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass

    # 2. Try Naver SISE JSON API (가장 안정적임)
    try:
        import ast
        end_date = datetime.now().strftime("%Y%m%d")
        url = f"https://api.finance.naver.com/siseJson.naver?symbol={target_code}&requestType=1&startTime=20200101&endTime={end_date}&timeframe=day"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': 'https://finance.naver.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            text = response.text.strip()
            cleaned_text = text.replace("NaN", "0")
            
            try:
                raw_data = ast.literal_eval(cleaned_text)
            except Exception:
                raw_data = json.loads(cleaned_text.replace("'", '"'))
            
            if isinstance(raw_data, list) and len(raw_data) > 1:
                rows = raw_data[1:]
                history = []
                for row in rows[-days:]:
                    try:
                        dt_str = f"{row[0][:4]}-{row[0][4:6]}-{row[0][6:8]}"
                        history.append({
                            "time": dt_str,
                            "open": float(row[1]),
                            "high": float(row[2]),
                            "low": float(row[3]),
                            "close": float(row[4]),
                            "volume": int(row[5])
                        })
                    except: continue
                if history:
                    return history
    except Exception as e:
        print(f"Naver Error ({code}): {e}")

    # 3. Last Resort: FinanceDataReader
    try:
        import FinanceDataReader as fdr
        fdr_code = "KS11" if code == "KOSPI" else "KQ11"
        df = fdr.DataReader(fdr_code)
        if df is not None and not df.empty:
            df = df.iloc[-days:].dropna()
            history = []
            for index, row in df.iterrows():
                history.append({
                    "time": index.strftime("%Y-%m-%d"),
                    "open": float(row.get('Open', 0)),
                    "high": float(row.get('High', 0)),
                    "low": float(row.get('Low', 0)),
                    "close": float(row.get('Close', 0)),
                    "volume": int(row.get('Volume', 0))
                })
            return history
    except Exception as e:
        print(f"FDR Error ({code}): {e}")
        
    return []
