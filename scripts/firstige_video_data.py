#!/usr/bin/env python3
"""영상 렌더러에 넘길 데이터 묶음(JSON)을 만든다.

전용 84㎡(시장 통칭 34평) 하나로 이야기를 끌고 간다. 자막 표기도 '전용 84㎡(34평)'.
분기 중위 거래금액(총액) 시계열 + 매물대 + 요약 숫자를 한 파일에 담는다.

사용법:
    python scripts/firstige_video_data.py --outfile ../../backtest-reels/content/apt-firstige-84.json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows 콘솔(cp949)에서 한글·기호 출력이 깨지지 않도록 표준출력을 UTF-8로 고정한다
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from firstige_analysis import (  # noqa: E402
    BASE_YEAR, BUNYANGGA, BUNYANG_YEAR, PYEONG_TARGET_AREA_PREFIX,
    load_csv, live_sales, quarter_of, real, year_of,
)

log = logging.getLogger("firstige_video_data")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", default="data/firstige")
    parser.add_argument("--outfile", default="data/firstige/video_84.json")
    parser.add_argument("--bucket", type=int, default=20_000, help="매물대 구간폭(만원)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    indir = Path(args.indir)
    sales = [r for r in live_sales(load_csv(indir / "firstige_매매_전건.csv"))
             if r["전용면적"].startswith(PYEONG_TARGET_AREA_PREFIX)]
    if not sales:
        log.error("전용 84㎡ 매매가 없습니다")
        return 1
    sales.sort(key=lambda r: r["계약일자"])
    log.info("전용 84㎡ 매매 %s건 (%s ~ %s)", len(sales), sales[0]["계약일자"], sales[-1]["계약일자"])

    # ── 분기 중위 총액 시계열 (명목·실질)
    q: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in sales:
        q[quarter_of(r["계약일자"])].append(r)
    series = []
    for key in sorted(q):
        rows = q[key]
        nom = statistics.median(float(r["거래금액_만원"]) for r in rows)
        rel = statistics.median(real(float(r["거래금액_만원"]), year_of(r)) for r in rows)
        series.append({"q": key, "n": len(rows),
                       "nominal": round(nom), "real": round(rel)})

    # ── 매물대 (총액 구간별 건수, 전 기간 / 최근 5년)
    width = args.bucket
    counts: Dict[int, Dict[str, int]] = defaultdict(lambda: {"all": 0, "recent": 0})
    for r in sales:
        edge = int(float(r["거래금액_만원"]) // width) * width
        counts[edge]["all"] += 1
        if r["계약일자"] >= "2021-08-01":
            counts[edge]["recent"] += 1
    profile = [{"edge": e, "width": width,
                "label": f"{e/10_000:.0f}~{(e+width)/10_000:.0f}억",
                "all": counts[e]["all"], "recent": counts[e]["recent"]}
               for e in sorted(counts)]

    # ── 연도별 중위 총액 (사건 표시용)
    by_year: Dict[int, List[float]] = defaultdict(list)
    by_year_real: Dict[int, List[float]] = defaultdict(list)
    for r in sales:
        by_year[year_of(r)].append(float(r["거래금액_만원"]))
        by_year_real[year_of(r)].append(real(float(r["거래금액_만원"]), year_of(r)))
    real_med = {y: statistics.median(v) for y, v in by_year_real.items()}
    low_year = min(real_med, key=real_med.get)

    low, high = BUNYANGGA[PYEONG_TARGET_AREA_PREFIX]
    mid = (low + high) / 2
    mid_real = real(mid, BUNYANG_YEAR)
    recent = [r for r in sales if r["계약일자"] >= "2025-08-01"]
    now_med = statistics.median(float(r["거래금액_만원"]) for r in recent)

    units = {r["전용면적"]: int(r["세대수"])
             for r in load_csv(indir / "세대수_전용면적별.csv")}
    unit_total = sum(v for k, v in units.items() if k.startswith(PYEONG_TARGET_AREA_PREFIX))

    peak = max(profile, key=lambda p: p["all"])
    heavy = [p for p in profile if 120_000 <= p["edge"] < 180_000]

    data = {
        "meta": {
            "complex": "래미안퍼스티지",
            "address": "서울 서초구 반포동 18-1",
            "typeLabel": "전용 84㎡(34평)",
            "movedIn": "2009-07",
            "unitsTotal": 2444,
            "unitsOfType": unit_total,
            "baseYear": BASE_YEAR,
            "cpiSource": "World Bank WDI FP.CPI.TOTL",
            "salesSource": "국토교통부 실거래가 오픈API",
            "unitsSource": "국토교통부 건축HUB 건축물대장 전유부",
        },
        "conditions": [
            "전용 84㎡(34평) 기준",
            f"국토부 실거래가 매매 {len(sales):,}건 (해제 제외)",
            f"{sales[0]['계약일자']} ~ {sales[-1]['계약일자']}",
        ],
        "launch": {
            "date": "2008-10",
            "low": low, "high": high, "mid": round(mid),
            "midReal": round(mid_real),
            "generalUnits": 426,
            "note": "후분양 · 2008-10-14~17 청약",
        },
        "series": series,
        "profile": profile,
        "marks": [
            {"q": series[0]["q"], "label": "입주", "sub": "2009-07"},
            {"q": f"{low_year}-Q4", "label": "실질 최저", "sub": f"{low_year}년"},
            {"q": max(series, key=lambda s: s["nominal"])["q"], "label": "최고가", "sub": ""},
        ],
        "summary": {
            "launchMid": round(mid),
            "launchMidReal": round(mid_real),
            "nowMedian": round(now_med),
            "nowCount": len(recent),
            "nominalMultiple": round(now_med / mid, 2),
            "realMultiple": round(now_med / mid_real, 2),
            "salesCount": len(sales),
            "turnover": round(len(sales) / unit_total, 3),
            "neverSold": max(0, unit_total - len(sales)),
            "neverSoldPct": round(max(0.0, 1 - len(sales) / unit_total) * 100),
            "peakBucket": peak["label"],
            "peakCount": peak["all"],
            "heavyLabel": "12~18억",
            "heavyCount": sum(p["all"] for p in heavy),
            "heavyPct": round(sum(p["all"] for p in heavy) / len(sales) * 100),
            "realLowYear": low_year,
        },
    }

    out = Path(args.outfile)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("완료 — 시계열 %s분기 / 매물대 %s구간 -> %s", len(series), len(profile), out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
