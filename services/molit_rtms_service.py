"""국토교통부 부동산 실거래가 오픈API(공공데이터포털) 클라이언트.

공공데이터포털 '국토교통부_아파트 매매/전월세/분양권전매 실거래가 (상세)자료'를
시군구코드(LAWD_CD) + 계약년월(DEAL_YMD) 단위로 전량 수집한다.

- 매매 상세자료는 2023년 개편으로 ``rgstDate``(등기일자) 항목을 포함한다.
  등기일자는 2023년 1월 1일 이후 계약분에 한해 채워지며, 그 이전 계약분은 공란이다.
- 응답은 XML. 월별 원본 XML을 캐시에 저장해 재실행 시 재호출을 건너뛴다(감사·재현용).
"""

from __future__ import annotations

import logging
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional
from urllib.parse import unquote

import requests

logger = logging.getLogger(__name__)

BASE = "https://apis.data.go.kr/1613000"

ENDPOINTS: Dict[str, str] = {
    # 아파트 매매 실거래가 상세 자료 (등기일자 포함)
    "매매": f"{BASE}/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev",
    # 아파트 전월세 실거래가 자료
    "전월세": f"{BASE}/RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
    # 아파트 분양권/입주권 전매 실거래가 자료
    "분양권": f"{BASE}/RTMSDataSvcSilvTrade/getRTMSDataSvcSilvTrade",
}

# 영문 응답 필드 -> 한글 컬럼
FIELD_MAP: Dict[str, str] = {
    "sggCd": "지역코드",
    "umdCd": "법정동코드",
    "umdNm": "법정동",
    "landCd": "대지구분코드",
    "bonbun": "본번",
    "bubun": "부번",
    "jibun": "지번",
    "roadNm": "도로명",
    "roadNmSggCd": "도로명시군구코드",
    "roadNmCd": "도로명코드",
    "roadNmSeq": "도로명일련번호코드",
    "roadNmbCd": "도로명지상지하코드",
    "roadNmBonbun": "도로명건물본번호코드",
    "roadNmBubun": "도로명건물부번호코드",
    "aptNm": "단지명",
    "aptSeq": "단지일련번호",
    "aptDong": "동",
    "buildYear": "건축년도",
    "excluUseAr": "전용면적",
    "floor": "층",
    "dealYear": "계약년도",
    "dealMonth": "계약월",
    "dealDay": "계약일",
    "dealAmount": "거래금액",
    "dealingGbn": "거래유형",
    "estateAgentSggNm": "중개사소재지",
    "cdealType": "해제여부",
    "cdealDay": "해제사유발생일",
    "rgstDate": "등기일자",          # 소유권이전등기 신고일 (2023.01 계약분~)
    "slerGbn": "매도자",
    "buyerGbn": "매수자",
    "landLeaseholdGbn": "토지임대부여부",
    # 전월세
    "deposit": "보증금액",
    "monthlyRent": "월세금액",
    "contractTerm": "계약기간",
    "contractType": "계약구분",
    "useRRRight": "갱신요구권사용",
    "preDeposit": "종전계약보증금",
    "preMonthlyRent": "종전계약월세",
    # 분양권/입주권
    "offiNm": "단지명",
}


class MolitApiError(RuntimeError):
    """공공데이터포털이 정상(000) 이외의 resultCode를 반환한 경우."""


@dataclass
class MolitRtmsClient:
    service_key: str
    cache_dir: Optional[Path] = None
    timeout: int = 30
    max_retries: int = 5
    sleep_between_calls: float = 0.12
    session: requests.Session = field(default_factory=requests.Session)

    def __post_init__(self) -> None:
        # 포털이 발급하는 Encoding/Decoding 키를 모두 허용한다.
        self.service_key = unquote(str(self.service_key).strip())
        if self.cache_dir:
            self.cache_dir = Path(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ HTTP
    def _cache_path(self, kind: str, lawd_cd: str, deal_ymd: str, page: int) -> Optional[Path]:
        if not self.cache_dir:
            return None
        sub = self.cache_dir / kind / lawd_cd
        sub.mkdir(parents=True, exist_ok=True)
        return sub / f"{deal_ymd}_p{page}.xml"

    def _fetch_xml(self, kind: str, lawd_cd: str, deal_ymd: str, page: int, rows: int) -> str:
        cached = self._cache_path(kind, lawd_cd, deal_ymd, page)
        if cached and cached.exists() and cached.stat().st_size > 0:
            return cached.read_text(encoding="utf-8")

        params = {
            "serviceKey": self.service_key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "pageNo": str(page),
            "numOfRows": str(rows),
        }
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(ENDPOINTS[kind], params=params, timeout=self.timeout)
                resp.raise_for_status()
                text = resp.content.decode("utf-8", errors="replace")
                if cached:
                    cached.write_text(text, encoding="utf-8")
                time.sleep(self.sleep_between_calls)
                return text
            except Exception as exc:  # 네트워크/일시 오류는 지수 백오프로 재시도
                last_err = exc
                wait = 2 ** attempt
                logger.warning("%s %s p%s 실패(%s) — %ss 후 재시도", kind, deal_ymd, page, exc, wait)
                time.sleep(wait)
        raise MolitApiError(f"{kind} {lawd_cd} {deal_ymd} p{page} 호출 실패: {last_err}")

    # ----------------------------------------------------------------- parse
    @staticmethod
    def _parse(xml_text: str) -> tuple[List[Dict[str, str]], int]:
        root = ET.fromstring(xml_text)

        code = root.findtext(".//resultCode") or root.findtext(".//returnReasonCode")
        msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg") or ""
        if code is not None and code.strip() not in ("00", "000"):
            raise MolitApiError(f"resultCode={code.strip()} resultMsg={msg.strip()}")

        total_raw = root.findtext(".//totalCount")
        total = int(total_raw) if total_raw and total_raw.strip().isdigit() else 0

        rows: List[Dict[str, str]] = []
        for item in root.iter("item"):
            row: Dict[str, str] = {}
            for child in item:
                value = (child.text or "").strip()
                row[FIELD_MAP.get(child.tag, child.tag)] = value
            if row:
                rows.append(row)
        return rows, total

    # ------------------------------------------------------------------ API
    def fetch_month(self, kind: str, lawd_cd: str, deal_ymd: str, rows: int = 1000) -> List[Dict[str, str]]:
        """한 달치를 페이지 끝까지 모두 받아 반환한다(누락 방지를 위해 totalCount로 검증)."""
        page = 1
        collected: List[Dict[str, str]] = []
        total = None
        while True:
            xml_text = self._fetch_xml(kind, lawd_cd, deal_ymd, page, rows)
            page_rows, page_total = self._parse(xml_text)
            if total is None:
                total = page_total
            collected.extend(page_rows)
            if not page_rows or len(collected) >= (total or 0) or len(page_rows) < rows:
                break
            page += 1

        if total is not None and len(collected) != total:
            logger.warning(
                "%s %s %s: totalCount=%s 이지만 %s건 수집 — 재확인 필요",
                kind, lawd_cd, deal_ymd, total, len(collected),
            )
        for row in collected:
            row["거래구분"] = kind
            row["조회년월"] = deal_ymd
        return collected

    def fetch_range(
        self,
        kind: str,
        lawd_cd: str,
        start_ym: str,
        end_ym: str,
        rows: int = 1000,
        progress: bool = True,
    ) -> Iterator[tuple[str, List[Dict[str, str]]]]:
        """start_ym~end_ym(YYYYMM) 전 구간을 월 단위로 순회한다."""
        for ym in month_range(start_ym, end_ym):
            batch = self.fetch_month(kind, lawd_cd, ym, rows=rows)
            if progress:
                logger.info("%s %s %s: %s건", kind, lawd_cd, ym, len(batch))
            yield ym, batch


def month_range(start_ym: str, end_ym: str) -> Iterable[str]:
    """'200601', '202608' -> 그 사이 모든 YYYYMM 문자열."""
    sy, sm = int(start_ym[:4]), int(start_ym[4:6])
    ey, em = int(end_ym[:4]), int(end_ym[4:6])
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield f"{y:04d}{m:02d}"
        m += 1
        if m == 13:
            y, m = y + 1, 1


def current_ym() -> str:
    today = date.today()
    return f"{today.year:04d}{today.month:02d}"


def resolve_service_key(explicit: Optional[str] = None) -> str:
    """CLI 인자 > 환경변수 순으로 인증키를 찾는다."""
    key = explicit or os.getenv("MOLIT_SERVICE_KEY") or os.getenv("DATA_GO_KR_SERVICE_KEY")
    if not key:
        raise SystemExit(
            "공공데이터포털 인증키가 없습니다. "
            "MOLIT_SERVICE_KEY 환경변수에 넣거나 --service-key 로 전달하세요."
        )
    return key
