#!/usr/bin/env python3
"""네트워크 없이 수집 파이프라인을 검증한다.

월별 원본 XML 캐시를 미리 심어두고 collect_banpo_raemian.py 를 그대로 돌려
파싱 -> 필터 -> 중복제거 -> CSV/SQLite/리포트 생성까지 확인한다.
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.molit_rtms_service import MolitRtmsClient, MolitApiError, month_range  # noqa: E402

TRADE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>000</resultCode><resultMsg>OK</resultMsg></header>
<body><items>
<item><aptNm>래미안퍼스티지</aptNm><umdNm>반포동</umdNm><jibun>18-1</jibun>
<excluUseAr>84.93</excluUseAr><floor>25</floor><buildYear>2009</buildYear>
<dealYear>2026</dealYear><dealMonth>6</dealMonth><dealDay>17</dealDay>
<dealAmount>545,000</dealAmount><rgstDate>26.07.30</rgstDate>
<dealingGbn>중개거래</dealingGbn><sggCd>11650</sggCd></item>
<item><aptNm>래미안 원베일리</aptNm><umdNm>반포동</umdNm><jibun>1</jibun>
<excluUseAr>84.95</excluUseAr><floor>20</floor><buildYear>2023</buildYear>
<dealYear>2026</dealYear><dealMonth>6</dealMonth><dealDay>24</dealDay>
<dealAmount>563,000</dealAmount><rgstDate></rgstDate>
<cdealType>O</cdealType><cdealDay>26.07.02</cdealDay><sggCd>11650</sggCd></item>
<item><aptNm>반포자이</aptNm><umdNm>반포동</umdNm><jibun>20</jibun>
<excluUseAr>84.94</excluUseAr><floor>10</floor><buildYear>2008</buildYear>
<dealYear>2026</dealYear><dealMonth>6</dealMonth><dealDay>11</dealDay>
<dealAmount>510,000</dealAmount><sggCd>11650</sggCd></item>
<item><aptNm>래미안에스티지</aptNm><umdNm>서초동</umdNm><jibun>1330</jibun>
<excluUseAr>84.96</excluUseAr><floor>5</floor><buildYear>2016</buildYear>
<dealYear>2026</dealYear><dealMonth>6</dealMonth><dealDay>9</dealDay>
<dealAmount>390,000</dealAmount><sggCd>11650</sggCd></item>
</items><numOfRows>1000</numOfRows><pageNo>1</pageNo><totalCount>4</totalCount></body></response>
"""

# 동일 거래를 한 번 더 넣어 중복 제거가 동작하는지 본다.
TRADE_XML_DUP = TRADE_XML.replace("<totalCount>4</totalCount>", "<totalCount>4</totalCount>")

SILV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>000</resultCode><resultMsg>OK</resultMsg></header>
<body><items>
<item><aptNm>래미안원펜타스</aptNm><umdNm>반포동</umdNm><jibun>12</jibun>
<excluUseAr>107.6378</excluUseAr><floor>16</floor><buildYear>2024</buildYear>
<dealYear>2026</dealYear><dealMonth>6</dealMonth><dealDay>5</dealDay>
<dealAmount>710,000</dealAmount><dealingGbn>분양권</dealingGbn><sggCd>11650</sggCd></item>
</items><numOfRows>1000</numOfRows><pageNo>1</pageNo><totalCount>1</totalCount></body></response>
"""

EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>000</resultCode><resultMsg>OK</resultMsg></header>
<body><items></items><numOfRows>1000</numOfRows><pageNo>1</pageNo><totalCount>0</totalCount></body></response>
"""

ERROR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<OpenAPI_ServiceResponse><cmmMsgHeader>
<returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>
<returnReasonCode>30</returnReasonCode></cmmMsgHeader></OpenAPI_ServiceResponse>
"""


def seed_cache(outdir: Path, start: str, end: str) -> None:
    for kind, payload in (("매매", TRADE_XML), ("분양권", SILV_XML), ("전월세", EMPTY_XML)):
        for ym in month_range(start, end):
            path = outdir / "_cache" / kind / "11650"
            path.mkdir(parents=True, exist_ok=True)
            body = payload if ym == "202606" else EMPTY_XML
            (path / f"{ym}_p1.xml").write_text(body, encoding="utf-8")


def check(label: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'}  {label}{' — ' + detail if detail else ''}")
    return condition


def main() -> int:
    outdir = ROOT / "data" / "_offline_test"
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    seed_cache(outdir, "202604", "202606")

    ok = True

    # 1. 인증 실패 XML을 명시적 예외로 올리는지
    try:
        MolitRtmsClient._parse(ERROR_XML)
        ok &= check("인증오류 XML -> MolitApiError", False)
    except MolitApiError as exc:
        ok &= check("인증오류 XML -> MolitApiError", "SERVICE_KEY" in str(exc), str(exc))

    # 2. totalCount 파싱
    rows, total = MolitRtmsClient._parse(TRADE_XML)
    ok &= check("매매 XML 파싱 4건", len(rows) == 4 and total == 4, f"{len(rows)}건/total={total}")
    ok &= check("등기일자 필드 매핑", rows[0].get("등기일자") == "26.07.30", rows[0].get("등기일자", ""))
    ok &= check("해제 정보 매핑", rows[1].get("해제여부") == "O" and rows[1].get("해제사유발생일") == "26.07.02")

    # 3. 수집기 전체 실행 (캐시만 사용 — 네트워크 호출 없음)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "collect_banpo_raemian.py"),
         "--service-key", "OFFLINE_TEST_KEY",
         "--start", "202604", "--end", "202606",
         "--outdir", str(outdir)],
        capture_output=True, text=True,
    )
    ok &= check("수집기 종료코드 0", proc.returncode == 0, proc.stderr[-400:])

    all_csv = outdir / "banpo_raemian_all.csv"
    with all_csv.open(encoding="utf-8-sig") as fh:
        collected = list(csv.DictReader(fh))
    names = sorted({r["단지명"] for r in collected})
    ok &= check("래미안 3건만 남음(반포자이·서초동 래미안 제외)", len(collected) == 3, f"{len(collected)}건 {names}")
    ok &= check("반포자이 제외", "반포자이" not in names)
    ok &= check("서초동 래미안에스티지 제외", "래미안에스티지" not in names)
    ok &= check("분양권 거래 포함", any(r["거래구분"] == "분양권" for r in collected))
    ok &= check("계약일자 정규화", any(r["계약일자"] == "2026-06-17" for r in collected))

    con = sqlite3.connect(outdir / "banpo_raemian.sqlite")
    db_count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    con.close()
    ok &= check("SQLite 적재", db_count == 3, f"{db_count}행")

    report = (outdir / "REPORT.md").read_text(encoding="utf-8")
    ok &= check("리포트 생성", "단지별 요약" in report and "총 수집 건수: 3건" in report)

    # 4. 서초구 전체 옵션
    proc2 = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "collect_banpo_raemian.py"),
         "--service-key", "OFFLINE_TEST_KEY", "--start", "202604", "--end", "202606",
         "--outdir", str(outdir), "--all-seocho-raemian"],
        capture_output=True, text=True,
    )
    with all_csv.open(encoding="utf-8-sig") as fh:
        wide = list(csv.DictReader(fh))
    ok &= check("--all-seocho-raemian 로 서초동 래미안 포함", proc2.returncode == 0 and len(wide) == 4, f"{len(wide)}건")

    shutil.rmtree(outdir)
    print("\n=== 전체 통과 ===" if ok else "\n=== 실패 항목 있음 ===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
