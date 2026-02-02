"""
FRED Service - US Treasury Yields via FRED API
Fetches real-time bond yield data for 2Y, 10Y, 30Y treasuries.
"""
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TreasuryYieldData:
    """국채 수익률 데이터"""
    series_id: str
    name: str
    current_value: Optional[float]
    date: Optional[str]
    change: Optional[float]  # Added change attribute
    history: List[Tuple[str, float]]  # (date, value) pairs
    error: Optional[str] = None


def fetch_fred_series(series_id: str, name: str, observations: int = 30) -> TreasuryYieldData:
    """
    FRED API에서 시계열 데이터를 조회합니다.
    """
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return TreasuryYieldData(
            series_id=series_id,
            name=name,
            current_value=None,
            date=None,
            change=None,
            history=[],
            error="FRED_API_KEY가 .env 파일에 설정되지 않았습니다."
        )

    try:
        # Calculate date range (last 60 days to ensure we get enough data points)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start_date,
            "observation_end": end_date,
            "sort_order": "desc",
            "limit": observations,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        observations_data = data.get("observations", [])
        
        # Filter out missing values (FRED uses "." for missing)
        valid_obs = [
            (obs["date"], float(obs["value"]))
            for obs in observations_data
            if obs["value"] != "."
        ]

        if not valid_obs:
            return TreasuryYieldData(
                series_id=series_id,
                name=name,
                current_value=None,
                date=None,
                change=None,
                history=[],
                error="데이터를 찾을 수 없습니다."
            )

        # Most recent value (sorted desc, so first item)
        current_date, current_value = valid_obs[0]
        
        # Calculate change (vs previous valid observation)
        change = 0.0
        if len(valid_obs) > 1:
            prev_value = valid_obs[1][1]
            change = current_value - prev_value
        
        # Reverse for chronological order in history
        history = list(reversed(valid_obs))

        return TreasuryYieldData(
            series_id=series_id,
            name=name,
            current_value=current_value,
            date=current_date,
            change=change,
            history=history,
        )

    except requests.RequestException as e:
        return TreasuryYieldData(
            series_id=series_id,
            name=name,
            current_value=None,
            date=None,
            change=None,
            history=[],
            error=f"네트워크 오류: {e}"
        )
    except Exception as e:
        return TreasuryYieldData(
            series_id=series_id,
            name=name,
            current_value=None,
            date=None,
            change=None,
            history=[],
            error=f"오류: {e}"
        )


def get_treasury_yields() -> dict:
    """
    미국 국채 수익률(2Y, 10Y, 30Y)을 조회합니다.

    Returns:
        dict: {series_id: TreasuryYieldData}
    """
    series_map = {
        "DGS2": "2년물",
        "DGS10": "10년물",
        "DGS30": "30년물",
    }

    results = {}
    for series_id, name in series_map.items():
        results[series_id] = fetch_fred_series(series_id, name)

    return results
