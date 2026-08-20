#!/usr/bin/env python3
"""반포 래미안퍼스티지 실거래 수집 + 정리.

두 축으로 정리한다:
  축 1) 거래유형 — 매매 / 전세 / 월세 (전월세 API 결과를 월세금액 0 여부로 분리)
  축 2) 평형 — 전용면적을 평(3.3058㎡)으로 환산해 묶고, 전용면적별 상세도 함께 낸다

사용법:
    export MOLIT_SERVICE_KEY='공공데이터포털 일반 인증키(Decoding)'
    python scripts/firstige_report.py --start 200901 --outdir data/firstige

래미안퍼스티지는 2009년 7월 입주이므로 매매 기본 시작은 200901,
전월세는 국토부 공개 시작 시점에 맞춰 201101부터 조회한다.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.molit_rtms_service import (  # noqa: E402
    MolitRtmsClient,
    current_ym,
    month_range,
    resolve_service_key,
)

SEOCHO = "11650"
TARGET = "래미안퍼스티지"
PYEONG = 3.3058

log = logging.getLogger("firstige")


def norm(text: str) -> str:
    return (text or "").replace(" ", "").strip()


def to_int(text: str) -> Optional[int]:
    digits = (text or "").replace(",", "").strip()
    if not digits:
        return None
    try:
        return int(float(digits))
    except ValueError:
        return None


def to_float(text: str) -> Optional[float]:
    try:
        return float((text or "").strip())
    except ValueError:
        return None


def contract_date(row: Dict[str, str]) -> str:
    y, m, d = row.get("계약년도"), row.get("계약월"), row.get("계약일")
    if not (y and m and d):
        return ""
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def enrich(row: Dict[str, str]) -> Dict[str, str]:
    """분석용 파생 컬럼을 붙인다."""
    area = to_float(row.get("전용면적", ""))
    row["계약일자"] = contract_date(row)
    row["전용면적"] = f"{area:.2f}" if area is not None else ""
    row["평형"] = str(round(area / PYEONG)) if area else ""
    row["평수"] = f"{area / PYEONG:.1f}" if area else ""

    price = to_int(row.get("거래금액", ""))
    if price is not None:
        row["거래금액_만원"] = str(price)
        if area:
            row["㎡당_만원"] = f"{price / area:.1f}"
            row["평당_만원"] = f"{price / (area / PYEONG):.1f}"

    deposit = to_int(row.get("보증금액", ""))
    rent = to_int(row.get("월세금액", ""))
    if deposit is not None:
        row["보증금_만원"] = str(deposit)
        row["월세_만원"] = str(rent or 0)
        row["임대유형"] = "월세" if (rent or 0) > 0 else "전세"
    return row


def is_cancelled(row: Dict[str, str]) -> bool:
    return bool(norm(row.get("해제여부", "")))


def collect(client: MolitRtmsClient, kind: str, start_ym: str, end_ym: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    failed: List[str] = []
    for ym in month_range(start_ym, end_ym):
        try:
            batch = client.fetch_month(kind, SEOCHO, ym)
        except Exception as exc:
            log.error("%s %s 실패: %s", kind, ym, exc)
            failed.append(ym)
            continue
        hits = [enrich(r) for r in batch if TARGET in norm(r.get("단지명", ""))]
        out.extend(hits)
        if hits:
            log.info("%s %s: %s건", kind, ym, len(hits))
    if failed:
        log.warning("%s 실패한 월: %s", kind, ", ".join(failed))
    return out


def write_csv(path: Path, rows: List[Dict[str, str]], columns: Optional[List[str]] = None) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    if columns is None:
        columns = []
        for row in rows:
            for key in row:
                if key not in columns:
                    columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def stats(values: Iterable[int]) -> Dict[str, int]:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return {}
    mid = len(vals) // 2
    median = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) // 2
    return {
        "건수": len(vals),
        "평균": round(sum(vals) / len(vals)),
        "중위": median,
        "최저": vals[0],
        "최고": vals[-1],
    }


def by_pyeong(rows: List[Dict[str, str]], value_key: str) -> List[Dict[str, str]]:
    """평형(정수 평) 단위 집계. 해제 거래는 제외한다."""
    groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        if is_cancelled(row):
            continue
        if row.get("평형"):
            groups[row["평형"]].append(row)

    table: List[Dict[str, str]] = []
    for pyeong in sorted(groups, key=lambda p: int(p)):
        items = groups[pyeong]
        s = stats(to_int(r.get(value_key, "")) for r in items)
        if not s:
            continue
        areas = sorted({r["전용면적"] for r in items})
        dates = sorted(d for d in (r["계약일자"] for r in items) if d)
        entry = {
            "평형": pyeong,
            "전용면적": ", ".join(areas),
            "건수": s["건수"],
            "평균_만원": s["평균"],
            "중위_만원": s["중위"],
            "최저_만원": s["최저"],
            "최고_만원": s["최고"],
            "최초계약일": dates[0] if dates else "",
            "최근계약일": dates[-1] if dates else "",
        }
        if value_key == "거래금액_만원":
            entry["등기일자보유"] = sum(1 for r in items if r.get("등기일자"))
            rents = [to_int(r.get("평당_만원", "")) for r in items]
            rents = [v for v in rents if v is not None]
            if rents:
                entry["평균_평당_만원"] = round(sum(rents) / len(rents))
        if value_key == "보증금_만원":
            monthly = [to_int(r.get("월세_만원", "")) or 0 for r in items]
            if any(monthly):
                entry["평균_월세_만원"] = round(sum(monthly) / len(monthly))
        table.append(entry)
    return table


def by_pyeong_year(rows: List[Dict[str, str]], value_key: str) -> List[Dict[str, str]]:
    """평형 × 연도 평균가 피벗."""
    cells: Dict[tuple, List[int]] = defaultdict(list)
    years, pyeongs = set(), set()
    for row in rows:
        if is_cancelled(row) or not row.get("평형") or not row.get("계약일자"):
            continue
        value = to_int(row.get(value_key, ""))
        if value is None:
            continue
        year = row["계약일자"][:4]
        cells[(row["평형"], year)].append(value)
        years.add(year)
        pyeongs.add(row["평형"])

    table = []
    for pyeong in sorted(pyeongs, key=int):
        entry = {"평형": pyeong}
        for year in sorted(years):
            vals = cells.get((pyeong, year))
            entry[year] = round(sum(vals) / len(vals)) if vals else ""
        table.append(entry)
    return table


def md_table(rows: List[Dict[str, str]], columns: List[str]) -> List[str]:
    if not rows:
        return ["_해당 거래 없음_", ""]
    out = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    out.append("")
    return out


def build_report(sale: List[Dict], jeonse: List[Dict], wolse: List[Dict], span: str) -> str:
    lines = [f"# 반포 래미안퍼스티지 실거래 정리 ({span})", ""]
    lines.append("서울 서초구 반포동 18-1 · 2009년 7월 입주 · 2,444세대")
    lines.append("")
    lines.append("| 거래유형 | 총 건수 | 해제(취소) | 집계 대상 |")
    lines.append("|---|---:|---:|---:|")
    for label, rows in (("매매", sale), ("전세", jeonse), ("월세", wolse)):
        cancelled = sum(1 for r in rows if is_cancelled(r))
        lines.append(f"| {label} | {len(rows):,} | {cancelled:,} | {len(rows) - cancelled:,} |")
    lines.append("")
    lines.append("> 해제(취소) 거래는 아래 모든 집계에서 제외했습니다. 금액 단위는 만원입니다.")
    lines.append("")

    lines.append("## 1. 매매 — 평형별")
    lines.append("")
    lines += md_table(
        by_pyeong(sale, "거래금액_만원"),
        ["평형", "전용면적", "건수", "평균_만원", "중위_만원", "최저_만원", "최고_만원",
         "평균_평당_만원", "등기일자보유", "최초계약일", "최근계약일"],
    )

    lines.append("## 2. 매매 — 평형 × 연도 평균가")
    lines.append("")
    pivot = by_pyeong_year(sale, "거래금액_만원")
    if pivot:
        lines += md_table(pivot, list(pivot[0].keys()))
    else:
        lines += ["_데이터 없음_", ""]

    lines.append("## 3. 전세 — 평형별 보증금")
    lines.append("")
    lines += md_table(
        by_pyeong(jeonse, "보증금_만원"),
        ["평형", "전용면적", "건수", "평균_만원", "중위_만원", "최저_만원", "최고_만원",
         "최초계약일", "최근계약일"],
    )

    lines.append("## 4. 전세 — 평형 × 연도 평균 보증금")
    lines.append("")
    pivot = by_pyeong_year(jeonse, "보증금_만원")
    if pivot:
        lines += md_table(pivot, list(pivot[0].keys()))
    else:
        lines += ["_데이터 없음_", ""]

    lines.append("## 5. 월세 — 평형별 (보증금 / 월세)")
    lines.append("")
    lines += md_table(
        by_pyeong(wolse, "보증금_만원"),
        ["평형", "전용면적", "건수", "평균_만원", "최저_만원", "최고_만원",
         "평균_월세_만원", "최초계약일", "최근계약일"],
    )

    lines.append("## 6. 월세 — 평형 × 연도 평균 월세")
    lines.append("")
    pivot = by_pyeong_year(wolse, "월세_만원")
    if pivot:
        lines += md_table(pivot, list(pivot[0].keys()))
    else:
        lines += ["_데이터 없음_", ""]

    lines.append("> 등기일자는 2023년 1월 1일 이후 계약분에만 채워집니다.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="래미안퍼스티지 실거래 수집 및 평형별 정리")
    parser.add_argument("--service-key", default=None)
    parser.add_argument("--start", default="200901", help="매매 조회 시작 YYYYMM (기본 200901)")
    parser.add_argument("--rent-start", default="201101", help="전월세 조회 시작 YYYYMM (기본 201101)")
    parser.add_argument("--end", default=current_ym(), help="조회 종료 YYYYMM")
    parser.add_argument("--outdir", default="data/firstige")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    client = MolitRtmsClient(
        service_key=resolve_service_key(args.service_key),
        cache_dir=outdir / "_cache",
    )

    log.info("매매 수집 %s ~ %s", args.start, args.end)
    sale = collect(client, "매매", args.start, args.end)
    log.info("전월세 수집 %s ~ %s", args.rent_start, args.end)
    rent = collect(client, "전월세", args.rent_start, args.end)

    jeonse = [r for r in rent if r.get("임대유형") == "전세"]
    wolse = [r for r in rent if r.get("임대유형") == "월세"]

    sale.sort(key=lambda r: (r.get("계약일자", ""), r.get("전용면적", "")))
    jeonse.sort(key=lambda r: (r.get("계약일자", ""), r.get("전용면적", "")))
    wolse.sort(key=lambda r: (r.get("계약일자", ""), r.get("전용면적", "")))

    write_csv(outdir / "firstige_매매_전건.csv", sale)
    write_csv(outdir / "firstige_전세_전건.csv", jeonse)
    write_csv(outdir / "firstige_월세_전건.csv", wolse)

    write_csv(outdir / "firstige_평형별_매매.csv", by_pyeong(sale, "거래금액_만원"))
    write_csv(outdir / "firstige_평형별_전세.csv", by_pyeong(jeonse, "보증금_만원"))
    write_csv(outdir / "firstige_평형별_월세.csv", by_pyeong(wolse, "보증금_만원"))

    write_csv(outdir / "firstige_평형별연도별_매매.csv", by_pyeong_year(sale, "거래금액_만원"))
    write_csv(outdir / "firstige_평형별연도별_전세.csv", by_pyeong_year(jeonse, "보증금_만원"))
    write_csv(outdir / "firstige_평형별연도별_월세.csv", by_pyeong_year(wolse, "월세_만원"))

    span = f"{args.start}~{args.end} 매매 / {args.rent_start}~{args.end} 전월세"
    (outdir / "REPORT_firstige.md").write_text(
        build_report(sale, jeonse, wolse, span), encoding="utf-8"
    )

    log.info("완료 — 매매 %s건, 전세 %s건, 월세 %s건 -> %s",
             len(sale), len(jeonse), len(wolse), outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
