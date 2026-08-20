#!/usr/bin/env python3
"""래미안퍼스티지 시세 변화 분석 — 실질 평당가 시계열 + 평형별 매물대.

firstige_report.py / firstige_bunyang.py 가 만든 전건 CSV를 읽어
영상·리포트에 쓸 분석 산출물을 만든다. API를 호출하지 않는다.

내는 것 (--outdir 아래):
  평당가_시계열_평형별.csv   평형 × 분기, 명목·실질 중위 평당가
  실질배수_평형별.csv        분양권 → 최근 12개월, 명목배수·실질배수
  매물대_평형별.csv          평형 × 총액구간 × 기간구분(전기간/최근5년) 건수
  REPORT_분석.md             위 셋을 표로 정리

용어
  평당가        거래금액(만원) ÷ 평수. 단위 만원/평
  실질 평당가   소비자물가지수로 2025년 가치로 환산한 평당가
  매물대        가격대 구간별 매매 건수를 쌓은 분포. 세로축은 거래금액(총액)
  회전율        누적 매매 건수 ÷ 세대수

매물대를 평당가가 아니라 평형별 총액으로 만드는 이유는 두 가지다.
  1) 평형끼리 평당가 수준이 1.27배(최근 5년 중위) 차이나 한 축에 합치면 봉우리가 겹친다
  2) 같은 평형 안에서 전용면적이 갈라져도 중위 평당가 격차는 1~7%로 노이즈 수준이라
     면적별로 더 쪼갤 이유가 없다
"""

from __future__ import annotations

import argparse
import csv
import logging
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows 콘솔(cp949)에서 한글·기호 출력이 깨지지 않도록 표준출력을 UTF-8로 고정한다
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:  # 파이프로 리다이렉트된 경우 등
        pass

log = logging.getLogger("firstige_analysis")

# 한국 소비자물가지수 (2010 = 100), 연평균
# 출처: World Bank, World Development Indicators, series FP.CPI.TOTL
#       (Consumer price index, 2010 = 100), 2026-07-13 갱신분, 2026-08-20 조회
#       https://data.worldbank.org/indicator/FP.CPI.TOTL?locations=KOR
# 2026년치는 아직 공표 전이라 2025년 값을 그대로 쓴다(리포트에 명시).
CPI: Dict[int, float] = {
    2006: 88.0848, 2007: 90.3173, 2008: 94.5387, 2009: 97.1446, 2010: 100.0,
    2011: 104.0260, 2012: 106.3011, 2013: 107.6844, 2014: 109.0572, 2015: 109.8275,
    2016: 110.8947, 2017: 113.0508, 2018: 114.7193, 2019: 115.1586, 2020: 115.7774,
    2021: 118.6699, 2022: 124.7096, 2023: 129.1960, 2024: 132.1956, 2025: 135.0022,
    2026: 135.0022,  # 미공표 — 2025년 값 사용
}
BASE_YEAR = 2025          # 실질값의 기준 연도
UNITS_TOTAL = 2444        # 래미안퍼스티지 총 세대수
RECENT_MONTHS_START = "2025-08-01"   # '최근 12개월'의 시작
RECENT_5Y_START = "2021-08-01"       # '최근 5년'의 시작


# ------------------------------------------------------------------ 입출력
def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: List[Dict], columns: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def live_sales(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """해제(취소) 거래를 뺀 매매만 남긴다."""
    return [r for r in rows if not (r.get("해제여부") or "").strip()]


def year_of(row: Dict[str, str]) -> int:
    return int(row["계약일자"][:4])


def real(value: float, year: int) -> float:
    """명목값을 BASE_YEAR 가치로 환산한다."""
    return value * CPI[BASE_YEAR] / CPI[year]


# ------------------------------------------------------- 1) 평당가 시계열
def quarter_of(date: str) -> str:
    y, m = int(date[:4]), int(date[5:7])
    return f"{y}-Q{(m - 1) // 3 + 1}"


def price_series(sales: List[Dict[str, str]]) -> List[Dict]:
    buckets: Dict[tuple, List[Dict]] = defaultdict(list)
    for r in sales:
        if not r.get("평당_만원"):
            continue
        buckets[(r["평형"], quarter_of(r["계약일자"]))].append(r)

    out = []
    for (pyeong, q), rows in sorted(buckets.items(), key=lambda kv: (int(kv[0][0]), kv[0][1])):
        nominal = [float(r["평당_만원"]) for r in rows]
        realv = [real(float(r["평당_만원"]), year_of(r)) for r in rows]
        out.append({
            "평형": pyeong,
            "분기": q,
            "건수": len(rows),
            "명목_중위_평당_만원": round(statistics.median(nominal)),
            f"실질{BASE_YEAR}_중위_평당_만원": round(statistics.median(realv)),
        })
    return out


# --------------------------------------------------------- 2) 실질 배수
def multiples(sales: List[Dict[str, str]], bunyang: List[Dict[str, str]]) -> List[Dict]:
    recent = [r for r in sales if r["계약일자"] >= RECENT_MONTHS_START]
    out = []
    for pyeong in sorted({r["평형"] for r in sales}, key=int):
        b = [r for r in bunyang if r["평형"] == pyeong and r.get("평당_만원")]
        c = [r for r in recent if r["평형"] == pyeong and r.get("평당_만원")]
        if not b or not c:
            continue
        b_nom = statistics.mean(float(r["평당_만원"]) for r in b)
        b_real = statistics.mean(real(float(r["평당_만원"]), year_of(r)) for r in b)
        c_nom = statistics.mean(float(r["평당_만원"]) for r in c)
        c_real = statistics.mean(real(float(r["평당_만원"]), year_of(r)) for r in c)
        out.append({
            "평형": pyeong,
            "분양권_건수": len(b),
            "분양권_명목_평당_만원": round(b_nom),
            f"분양권_실질{BASE_YEAR}_평당_만원": round(b_real),
            "최근12개월_건수": len(c),
            "최근12개월_명목_평당_만원": round(c_nom),
            f"최근12개월_실질{BASE_YEAR}_평당_만원": round(c_real),
            "명목배수": round(c_nom / b_nom, 2),
            "실질배수": round(c_real / b_real, 2),
        })
    return out


# ------------------------------------------------------------- 3) 매물대
def bucket_width(values: List[float]) -> int:
    """구간 개수가 20~30개가 되도록 1억·2억·5억·10억 중에서 고른다 (단위 만원)."""
    span = max(values) - min(values)
    for width in (10_000, 20_000, 50_000, 100_000):
        if span / width <= 30:
            return width
    return 100_000


def volume_by_price(sales: List[Dict[str, str]]) -> List[Dict]:
    out = []
    for pyeong in sorted({r["평형"] for r in sales}, key=int):
        rows = [r for r in sales if r["평형"] == pyeong and r.get("거래금액_만원")]
        if not rows:
            continue
        values = [float(r["거래금액_만원"]) for r in rows]
        width = bucket_width(values)

        counts: Dict[int, Dict[str, int]] = defaultdict(lambda: {"전기간": 0, "최근5년": 0})
        for r in rows:
            edge = int(float(r["거래금액_만원"]) // width) * width
            counts[edge]["전기간"] += 1
            if r["계약일자"] >= RECENT_5Y_START:
                counts[edge]["최근5년"] += 1

        for edge in sorted(counts):
            out.append({
                "평형": pyeong,
                "구간폭_만원": width,
                "구간시작_만원": edge,
                "구간끝_만원": edge + width - 1,
                "구간표기": f"{edge/10_000:.0f}~{(edge+width)/10_000:.0f}억",
                "전기간_건수": counts[edge]["전기간"],
                "최근5년_건수": counts[edge]["최근5년"],
            })
    return out


def turnover(sales: List[Dict[str, str]]) -> Dict[str, float]:
    n = len(sales)
    return {
        "매매_건수": n,
        "세대수": UNITS_TOTAL,
        "회전율": round(n / UNITS_TOTAL, 3),
        "미거래_세대_하한_비율": round(max(0.0, 1 - n / UNITS_TOTAL), 3),
    }


# -------------------------------------------------------------- 리포트
def bar(count: int, peak: int, width: int = 30) -> str:
    return "█" * max(1, round(count / peak * width)) if count else ""


def build_report(series: List[Dict], mult: List[Dict], vbp: List[Dict],
                 turn: Dict[str, float], sales: List[Dict[str, str]]) -> str:
    lines = [
        "# 래미안퍼스티지 시세 변화 분석",
        "",
        f"매매 {turn['매매_건수']}건(해제 제외) · 세대수 {turn['세대수']:,} · "
        f"회전율 {turn['회전율']}회 · 미거래 세대 하한 {turn['미거래_세대_하한_비율']*100:.0f}%",
        "",
        f"실질값은 한국 소비자물가지수로 {BASE_YEAR}년 가치로 환산한 것입니다. "
        "2026년 물가지수는 아직 공표 전이라 2025년 값을 그대로 적용했습니다.",
        "출처: World Bank, World Development Indicators, FP.CPI.TOTL (2026-08-20 조회).",
        "",
        "## 1. 분양권 → 최근 12개월, 명목배수와 실질배수",
        "",
        "| 평형 | 분양권 평당가 | 최근 평당가 | 명목배수 | 실질배수 |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in mult:
        lines.append(
            f"| {r['평형']}평 | {r['분양권_명목_평당_만원']:,}만원 "
            f"| {r['최근12개월_명목_평당_만원']:,}만원 "
            f"| {r['명목배수']}배 | **{r['실질배수']}배** |"
        )

    lines += ["", "## 2. 평형별 매물대 — 거래금액 기준", "",
              "가로 막대는 그 금액대에서 체결된 매매 건수입니다. "
              "주식 매물대와 같은 정의이며, **현재 보유자의 매입가 분포가 아닙니다** "
              "(동·호가 비공개라 세대 단위 추적이 불가능합니다).", ""]

    for pyeong in sorted({r["평형"] for r in vbp}, key=int):
        rows = [r for r in vbp if r["평형"] == pyeong]
        peak = max(r["전기간_건수"] for r in rows)
        total = sum(r["전기간_건수"] for r in rows)
        recent_total = sum(r["최근5년_건수"] for r in rows)
        lines += [f"### {pyeong}평 — 전 기간 {total}건 (그중 최근 5년 {recent_total}건)", "", "```"]
        for r in rows:
            if r["전기간_건수"] == 0:
                continue
            mark = f"  (최근5년 {r['최근5년_건수']}건)" if r["최근5년_건수"] else ""
            lines.append(
                f"{r['구간표기']:>12}  {bar(r['전기간_건수'], peak):<30} "
                f"{r['전기간_건수']:4d}건{mark}"
            )
        lines += ["```", ""]

    lines += ["## 3. 평당가 시계열 (평형별 분기 중위값)", "",
              f"전체 {len(series)}행은 `평당가_시계열_평형별.csv` 에 있습니다. "
              "아래는 26평만 연도별로 추린 것입니다.", "",
              "| 연도 | 명목 중위 평당가 | 실질 중위 평당가 | 건수 |", "|---|---:|---:|---:|"]
    by_year: Dict[int, List[Dict[str, str]]] = defaultdict(list)
    for r in sales:
        if r["평형"] == "26" and r.get("평당_만원"):
            by_year[year_of(r)].append(r)
    for y in sorted(by_year):
        rows = by_year[y]
        nom = statistics.median(float(r["평당_만원"]) for r in rows)
        rel = statistics.median(real(float(r["평당_만원"]), year_of(r)) for r in rows)
        lines.append(f"| {y} | {nom:,.0f}만원 | {rel:,.0f}만원 | {len(rows)}건 |")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", default="data/firstige", help="전건 CSV가 있는 폴더")
    parser.add_argument("--outdir", default="data/firstige/analysis", help="분석 결과 저장 폴더")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    indir, outdir = Path(args.indir), Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    sales = live_sales(load_csv(indir / "firstige_매매_전건.csv"))
    bunyang = live_sales(load_csv(indir / "firstige_분양권_전건.csv"))
    if not sales:
        log.error("매매 전건 CSV가 비어 있습니다: %s", indir)
        return 1
    log.info("매매 %s건(해제 제외) / 분양권 %s건", len(sales), len(bunyang))

    series = price_series(sales)
    mult = multiples(sales, bunyang)
    vbp = volume_by_price(sales)
    turn = turnover(sales)

    write_csv(outdir / "평당가_시계열_평형별.csv", series, list(series[0].keys()))
    write_csv(outdir / "실질배수_평형별.csv", mult, list(mult[0].keys()))
    write_csv(outdir / "매물대_평형별.csv", vbp, list(vbp[0].keys()))
    (outdir / "REPORT_분석.md").write_text(
        build_report(series, mult, vbp, turn, sales), encoding="utf-8")

    log.info("완료 — 시계열 %s행 / 배수 %s행 / 매물대 %s행 -> %s",
             len(series), len(mult), len(vbp), outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
