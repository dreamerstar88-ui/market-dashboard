"""
Data Service - CSV Logging & Journal I/O
Handles persistent storage for market snapshots and user notes.
"""
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import HISTORY_PATH, JOURNAL_PATH


def log_market_snapshot(
    btc_global: float,
    btc_krw: float,
    kimchi_premium: float,
    usd_krw: float,
    fear_greed: Optional[int] = None
) -> None:
    """
    시장 스냅샷을 CSV 파일에 추가합니다.

    Args:
        btc_global: 글로벌 BTC 가격 (USD)
        btc_krw: 국내 BTC 가격 (KRW)
        kimchi_premium: 김치프리미엄 (%)
        usd_krw: 원달러 환율
        fear_greed: 공포/탐욕 지수 (Optional)
    """
    timestamp = datetime.now().isoformat()
    row = [timestamp, btc_global, btc_krw, kimchi_premium, usd_krw, fear_greed or ""]

    with open(HISTORY_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def load_journal() -> str:
    """저널 파일 내용을 읽어옵니다."""
    if JOURNAL_PATH.exists():
        return JOURNAL_PATH.read_text(encoding="utf-8")
    return ""


def save_journal(content: str) -> None:
    """저널 파일에 내용을 저장합니다."""
    JOURNAL_PATH.write_text(content, encoding="utf-8")


def append_journal_entry(entry: str) -> None:
    """저널에 새로운 항목을 추가합니다 (날짜 자동 삽입)."""
    current = load_journal()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"\n\n---\n**[{timestamp}]**\n{entry}"
    save_journal(current + new_entry)
