#!/usr/bin/env python3
"""래미안퍼스티지 분양권·입주권 전매 거래 수집 + 평형별 정리.

firstige_report.py 가 매매/전세/월세 세 축을 다루는 데 반해, 이 스크립트는
'분양 직후' 구간을 채우는 분양권·입주권 전매 자료만 따로 낸다.
퍼스티지는 2009년 7월 입주라 입주 전 거래가 전부 이 자료에 잡힌다.

분양권 자료는 2007년 7월 신고분부터 공개된다(그 이전 월은 응답이 0건).
최초 분양가 자체는 실거래가 자료에 없다(청약홈 입주자모집공고 소관).

사용법:
    python scripts/firstige_bunyang.py --start 200601 --outdir data/firstige

firstige_report.py 와 같은 --outdir 를 쓰면 월별 원본 XML 캐시를 공유하므로
API를 다시 호출하지 않는다.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows 콘솔(cp949)에서 한글·기호 출력이 깨지지 않도록 표준출력을 UTF-8로 고정한다
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:  # 파이프로 리다이렉트된 경우 등
        pass

from services.molit_rtms_service import (  # noqa: E402
    MolitRtmsClient,
    current_ym,
    resolve_service_key,
)
from firstige_report import (  # noqa: E402
    by_pyeong,
    by_pyeong_year,
    collect,
    is_cancelled,
    md_table,
    write_csv,
)

log = logging.getLogger("firstige_bunyang")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-key", default=None)
    parser.add_argument("--start", default="200601", help="조회 시작 YYYYMM (기본 200601)")
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

    rows = collect(client, "분양권", args.start, args.end)
    cancelled = [r for r in rows if is_cancelled(r)]
    live = [r for r in rows if not is_cancelled(r)]

    write_csv(outdir / "firstige_분양권_전건.csv", rows)
    write_csv(outdir / "firstige_평형별_분양권.csv", by_pyeong(live, "거래금액_만원"))
    write_csv(outdir / "firstige_평형별연도별_분양권.csv", by_pyeong_year(live, "거래금액_만원"))

    span = f"{args.start} ~ {args.end}"
    lines = [
        "# 래미안퍼스티지 분양권·입주권 전매",
        "",
        f"조회 구간 {span} · 전체 {len(rows)}건 (해제 {len(cancelled)}건 제외하고 집계)",
        "",
        "분양권 자료는 2007년 7월 신고분부터 공개된다. 최초 분양가는 실거래가 자료에 없다.",
        "",
        "## 평형별",
        "",
    ]
    table = by_pyeong(live, "거래금액_만원")
    lines += md_table(table, list(table[0].keys())) if table else ["(자료 없음)"]
    lines += ["", "## 평형 × 연도 평균가", ""]
    pivot = by_pyeong_year(live, "거래금액_만원")
    lines += md_table(pivot, list(pivot[0].keys())) if pivot else ["(자료 없음)"]

    (outdir / "REPORT_firstige_분양권.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    log.info("완료 — 분양권 %s건(해제 %s건) -> %s", len(rows), len(cancelled), outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
