#!/usr/bin/env python3
"""반포·잠원 '래미안' 아파트 단지의 국토부 실거래 전량 수집기.

수집 대상 (모두 국토교통부 실거래가 공개 자료):
  - 매매   : 아파트 매매 실거래가 '상세' 자료 (등기일자 rgstDate 포함)
  - 분양권 : 아파트 분양권/입주권 전매 실거래가 자료 (분양 직후 전매 거래)
  - 전월세 : 아파트 전월세 실거래가 자료 (옵션)

서초구(11650) 전 기간을 월 단위로 훑은 뒤 법정동(반포동/잠원동) + 단지명에
'래미안'이 포함된 건만 남긴다. 단지명 표기 흔들림(공백/구 표기)을 흡수하기 위해
화이트리스트가 아니라 '래미안' 부분일치로 거른다.

사용법:
    export MOLIT_SERVICE_KEY='<공공데이터포털 일반 인증키(Decoding)>'
    python scripts/collect_banpo_raemian.py --start 200601 --outdir data/banpo_raemian

원본 XML은 --outdir/_cache 에 월별로 저장되어 재실행 시 재호출하지 않는다.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.molit_rtms_service import (  # noqa: E402
    MolitRtmsClient,
    current_ym,
    month_range,
    resolve_service_key,
)

SEOCHO_LAWD_CD = "11650"          # 서울특별시 서초구
TARGET_DONGS = ("반포동", "잠원동")
BRAND_KEYWORD = "래미안"

# 참고용 단지 메타 (필터에는 쓰지 않고 리포트 라벨링에만 사용)
KNOWN_COMPLEXES = {
    "래미안퍼스티지": {"법정동": "반포동", "입주": "2009-07", "세대수": 2444},
    "래미안원베일리": {"법정동": "반포동", "입주": "2023-08", "세대수": 2990},
    "래미안원펜타스": {"법정동": "반포동", "입주": "2024-08", "세대수": 641},
    "래미안신반포팰리스": {"법정동": "잠원동", "입주": "2016-06", "세대수": 843},
    "래미안신반포리오센트": {"법정동": "잠원동", "입주": "2019-06", "세대수": 475},
}

log = logging.getLogger("collect")


def norm(text: str) -> str:
    return (text or "").replace(" ", "").strip()


def is_target(row: Dict[str, str], all_seocho: bool) -> bool:
    if BRAND_KEYWORD not in norm(row.get("단지명", "")):
        return False
    if all_seocho:
        return True
    return norm(row.get("법정동", "")) in TARGET_DONGS


def dedup_key(row: Dict[str, str]) -> tuple:
    """동일 거래 중복 제거용 키. 재실행/페이지 중복을 흡수한다."""
    return (
        row.get("거래구분", ""),
        norm(row.get("단지명", "")),
        row.get("법정동", ""),
        row.get("지번", ""),
        row.get("전용면적", ""),
        row.get("층", ""),
        row.get("계약년도", ""),
        row.get("계약월", ""),
        row.get("계약일", ""),
        row.get("거래금액", ""),
        row.get("보증금액", ""),
        row.get("월세금액", ""),
    )


def contract_date(row: Dict[str, str]) -> str:
    y, m, d = row.get("계약년도", ""), row.get("계약월", ""), row.get("계약일", "")
    if not (y and m and d):
        return ""
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    columns: List[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    lead = ["거래구분", "계약일자", "단지명", "법정동", "지번", "전용면적", "층",
            "거래금액", "보증금액", "월세금액", "등기일자", "해제여부", "해제사유발생일"]
    ordered = [c for c in lead if c in columns] + [c for c in columns if c not in lead]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=ordered, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_sqlite(path: Path, rows: List[Dict[str, str]]) -> None:
    if not rows:
        return
    columns: List[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    con = sqlite3.connect(path)
    try:
        cols_sql = ", ".join(f'"{c}" TEXT' for c in columns)
        con.execute("DROP TABLE IF EXISTS transactions")
        con.execute(f"CREATE TABLE transactions ({cols_sql})")
        placeholders = ", ".join("?" for _ in columns)
        con.executemany(
            f"INSERT INTO transactions VALUES ({placeholders})",
            [tuple(row.get(c, "") for c in columns) for row in rows],
        )
        con.commit()
    finally:
        con.close()


def build_report(rows: List[Dict[str, str]], months: List[str], gaps: List[str]) -> str:
    by_kind: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_kind[row.get("거래구분", "?")].append(row)

    lines = ["# 반포·잠원 래미안 실거래 수집 리포트", ""]
    lines.append(f"- 조회 구간: {months[0]} ~ {months[-1]} (총 {len(months)}개월)")
    lines.append(f"- 총 수집 건수: {len(rows):,}건")
    for kind, items in sorted(by_kind.items()):
        lines.append(f"  - {kind}: {len(items):,}건")
    if gaps:
        lines.append(f"- ⚠ 응답 검증 실패(재확인 필요) 월: {', '.join(gaps)}")
    else:
        lines.append("- 모든 월에서 totalCount와 수집 건수가 일치했습니다.")
    lines.append("")

    lines.append("## 단지별 요약")
    lines.append("")
    lines.append("| 단지명 | 거래구분 | 건수 | 최초 계약일 | 최근 계약일 | 등기일자 보유 | 해제 |")
    lines.append("|---|---|---:|---|---|---:|---:|")
    grouped: Dict[tuple, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(norm(row.get("단지명", "")), row.get("거래구분", ""))].append(row)
    for (name, kind), items in sorted(grouped.items()):
        dates = sorted(d for d in (contract_date(r) for r in items) if d)
        rgst = sum(1 for r in items if r.get("등기일자"))
        cancelled = sum(1 for r in items if norm(r.get("해제여부", "")))
        lines.append(
            f"| {name} | {kind} | {len(items):,} | {dates[0] if dates else '-'} | "
            f"{dates[-1] if dates else '-'} | {rgst:,} | {cancelled:,} |"
        )
    lines.append("")

    lines.append("## 연도별 거래 건수 (매매)")
    lines.append("")
    year_counter = Counter(
        r.get("계약년도", "") for r in by_kind.get("매매", []) if r.get("계약년도")
    )
    lines.append("| 연도 | 건수 |")
    lines.append("|---|---:|")
    for year in sorted(year_counter):
        lines.append(f"| {year} | {year_counter[year]:,} |")
    lines.append("")
    lines.append(
        "> 등기일자는 2023년 1월 1일 이후 계약분에만 채워집니다. "
        "그 이전 계약은 국토부가 등기 정보를 공개하지 않으므로 공란입니다."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="반포·잠원 래미안 실거래 전량 수집")
    parser.add_argument("--service-key", default=None, help="공공데이터포털 인증키(Decoding)")
    parser.add_argument("--start", default="200601", help="시작 계약년월 YYYYMM (기본 200601)")
    parser.add_argument("--end", default=current_ym(), help="종료 계약년월 YYYYMM (기본 이번 달)")
    parser.add_argument("--outdir", default="data/banpo_raemian", help="결과 저장 폴더")
    parser.add_argument("--lawd-cd", default=SEOCHO_LAWD_CD, help="시군구코드 (기본 11650 서초구)")
    parser.add_argument(
        "--kinds", default="매매,분양권,전월세",
        help="수집할 거래구분 (쉼표 구분: 매매,분양권,전월세)",
    )
    parser.add_argument(
        "--all-seocho-raemian", action="store_true",
        help="반포동·잠원동으로 제한하지 않고 서초구 전체의 래미안을 수집",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    client = MolitRtmsClient(
        service_key=resolve_service_key(args.service_key),
        cache_dir=outdir / "_cache",
    )

    months = list(month_range(args.start, args.end))
    kinds = [k.strip() for k in args.kinds.split(",") if k.strip()]

    seen: set = set()
    kept: List[Dict[str, str]] = []
    gaps: List[str] = []

    for kind in kinds:
        for ym in months:
            try:
                batch = client.fetch_month(kind, args.lawd_cd, ym)
            except Exception as exc:
                log.error("%s %s 수집 실패: %s", kind, ym, exc)
                gaps.append(f"{kind}/{ym}")
                continue
            hits = [r for r in batch if is_target(r, args.all_seocho_raemian)]
            for row in hits:
                key = dedup_key(row)
                if key in seen:
                    continue
                seen.add(key)
                row["계약일자"] = contract_date(row)
                kept.append(row)
            log.info("%s %s: 서초구 %s건 중 래미안 %s건", kind, ym, len(batch), len(hits))

    kept.sort(key=lambda r: (norm(r.get("단지명", "")), r.get("거래구분", ""), r.get("계약일자", "")))

    write_csv(outdir / "banpo_raemian_all.csv", kept)
    for kind in kinds:
        subset = [r for r in kept if r.get("거래구분") == kind]
        write_csv(outdir / f"banpo_raemian_{kind}.csv", subset)
    write_sqlite(outdir / "banpo_raemian.sqlite", kept)
    (outdir / "REPORT.md").write_text(build_report(kept, months, gaps), encoding="utf-8")

    log.info("완료: %s건 -> %s", len(kept), outdir)
    if gaps:
        log.warning("검증 실패 월이 있습니다: %s", gaps)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
