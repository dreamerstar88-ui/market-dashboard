"""
Crypto Service - Kimchi Premium Calculator (REST API Version)
Uses pure requests to fetch BTC prices from Binance and Upbit public APIs.
No external dependencies that require C++ compilation.
"""
from dataclasses import dataclass
from typing import Optional
import requests


@dataclass
class KimchiPremiumData:
    """김치프리미엄 계산 결과 데이터 클래스"""
    btc_global_usd: float
    btc_korea_krw: float
    usd_krw_rate: float
    premium_percent: float
    error: Optional[str] = None


def get_kimchi_premium() -> KimchiPremiumData:
    """
    바이낸스와 업비트 BTC 가격을 비교하여 김치프리미엄을 계산합니다.
    순수 REST API 사용 (ccxt 의존성 없음).

    Returns:
        KimchiPremiumData: 글로벌 가격, 국내 가격, 환율, 프리미엄 비율
    """
    try:
        # 1. Binance (Global USD Price)
        binance_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        binance_resp = requests.get(binance_url, timeout=10)
        binance_resp.raise_for_status()
        btc_global_usd = float(binance_resp.json()["price"])

        # 2. Upbit (Korea KRW Price)
        upbit_btc_url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC"
        upbit_btc_resp = requests.get(upbit_btc_url, timeout=10)
        upbit_btc_resp.raise_for_status()
        btc_korea_krw = float(upbit_btc_resp.json()[0]["trade_price"])

        # 3. Upbit (USD/KRW via USDT)
        upbit_usdt_url = "https://api.upbit.com/v1/ticker?markets=KRW-USDT"
        upbit_usdt_resp = requests.get(upbit_usdt_url, timeout=10)
        upbit_usdt_resp.raise_for_status()
        usd_krw_rate = float(upbit_usdt_resp.json()[0]["trade_price"])

        # 4. Calculate Premium
        btc_global_krw = btc_global_usd * usd_krw_rate
        premium_percent = ((btc_korea_krw - btc_global_krw) / btc_global_krw) * 100

        return KimchiPremiumData(
            btc_global_usd=btc_global_usd,
            btc_korea_krw=btc_korea_krw,
            usd_krw_rate=usd_krw_rate,
            premium_percent=premium_percent,
        )

    except requests.RequestException as e:
        return KimchiPremiumData(0, 0, 0, 0, error=f"네트워크 오류: {e}")
    except (KeyError, IndexError, ValueError) as e:
        return KimchiPremiumData(0, 0, 0, 0, error=f"데이터 파싱 오류: {e}")
    except Exception as e:
        return KimchiPremiumData(0, 0, 0, 0, error=f"알 수 없는 오류: {e}")
