"""
Fear & Greed Index Service v2
- Alternative.me: Crypto Fear & Greed (무료 API)
- CNN Fear & Greed: 주식 시장용 (API)
"""
import requests
from dataclasses import dataclass
from typing import Optional


@dataclass
class FearGreedData:
    """공포/탐욕 지수 데이터"""
    value: int
    classification: str
    source: str
    error: Optional[str] = None


def get_crypto_fear_greed() -> FearGreedData:
    """
    Crypto Fear & Greed Index (Alternative.me API)
    크립토 시장 전용 지수
    """
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("data"):
            item = data["data"][0]
            value = int(item.get("value", 0))
            classification = item.get("value_classification", "Unknown")
            
            kr_class = {
                "Extreme Fear": "극도의 공포 😱",
                "Fear": "공포 😨",
                "Neutral": "중립 😐",
                "Greed": "탐욕 🤑",
                "Extreme Greed": "극도의 탐욕 🚀",
            }.get(classification, classification)
            
            return FearGreedData(value=value, classification=kr_class, source="Crypto (Alternative.me)")
        return FearGreedData(0, "Unknown", "Crypto", error="데이터 없음")
    except Exception as e:
        return FearGreedData(0, "Unknown", "Crypto", error=str(e))


def get_cnn_fear_greed() -> FearGreedData:
    """
    CNN Fear & Greed Index (주식 시장용)
    웹 스크래핑으로 가져옴
    """
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # CNN API returns fear_and_greed object
        fg_data = data.get("fear_and_greed", {})
        score = fg_data.get("score", 0)
        rating = fg_data.get("rating", "Unknown")
        
        value = int(round(score))
        
        kr_class = {
            "extreme fear": "극도의 공포 😱",
            "fear": "공포 😨",
            "neutral": "중립 😐",
            "greed": "탐욕 🤑",
            "extreme greed": "극도의 탐욕 🚀",
        }.get(rating.lower(), rating)
        
        return FearGreedData(value=value, classification=kr_class, source="CNN (주식)")
        
    except Exception as e:
        return FearGreedData(0, "Unknown", "CNN", error=str(e))


def get_fear_greed_index() -> dict:
    """
    CNN과 Crypto 두 가지 Fear & Greed 지수를 모두 반환
    """
    return {
        "cnn": get_cnn_fear_greed(),
        "crypto": get_crypto_fear_greed(),
    }
