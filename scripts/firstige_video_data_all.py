#!/usr/bin/env python3
"""단지 전체(7개 평형) 영상 데이터 — 평당가 축.

세로축을 평당가로 바꾸면 평형이 달라도 같은 축에 올릴 수 있다
(최근 5년 중위 평당가가 18평 15,179 ~ 67평 11,946만원/평으로 1.27배 차이).
그래서 7개 평형의 보유 분포를 한 그림에 색으로 쌓을 수 있고,
**합계가 단지 전체 세대수 2,444**가 된다.

내는 것
  timeline[] 분기마다
    medianAll   단지 전체 중위 평당가 (명목)
    realAll     같은 값의 물가 반영치
    byPyeong    평형별 중위 평당가 (거래 없는 분기는 직전 값)
    holdings[]  평당가 구간별 보유 세대수. 평형별로 나뉘고
                orig(분양가 그대로) / trad(사고팔려 매입가가 바뀜) 두 층

보유 분포 계산은 평형마다 따로 돌린다. 84㎡ 거래는 84㎡ 보유자만 할 수 있으므로.
분양 시점에 그 평형 전 세대가 '분양가 평당가' 칸에 있고, 거래가 한 건 일어나면
모든 칸에 (1 - 1/N) 을 곱하고 체결 평당가 칸에 1을 더한다. 합계는 N 으로 유지된다.

분양가는 전용 59·84·222㎡ 세 개만 공개돼 있다. 평당으로 환산하면
3,837~4,134만원/평으로 사실상 균일해서, 나머지 평형은 평수 기준 선형보간으로
추정하고 est=true 로 표시한다.

사용법:
    python scripts/firstige_video_data_all.py --outfile ../../backtest-reels/content/apt-firstige-all.json
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from firstige_analysis import (  # noqa: E402
    BASE_YEAR, BUNYANGGA, BUNYANG_YEAR,
    load_csv, live_sales, quarter_of, real, year_of,
)

log = logging.getLogger("firstige_video_data_all")
BUCKET = 1_000        # 평당가 구간폭 1,000만원/평
PYEONG = 3.3058       # 1평 = 3.3058㎡


def quarters_between(first: str, last: str) -> List[str]:
    y, q = int(first[:4]), int(first[-1])
    y1, q1 = int(last[:4]), int(last[-1])
    out = []
    while (y, q) <= (y1, q1):
        out.append(f"{y}-Q{q}")
        q += 1
        if q == 5:
            q, y = 1, y + 1
    return out


def launch_per_pyeong(area_to_pyeong: Dict[float, str]) -> Dict[str, Dict]:
    """평형별 분양가 평당가. 알려진 세 면적은 실제값, 나머지는 평수 기준 선형보간."""
    known = []
    for prefix, (low, high) in BUNYANGGA.items():
        area = next(a for a in area_to_pyeong if str(a).startswith(prefix))
        py = area / PYEONG
        known.append((py, (low + high) / 2 / py))
    known.sort()

    def interp(py: float) -> float:
        if py <= known[0][0]:
            return known[0][1]
        if py >= known[-1][0]:
            return known[-1][1]
        for (x0, y0), (x1, y1) in zip(known, known[1:]):
            if x0 <= py <= x1:
                return y0 + (y1 - y0) * (py - x0) / (x1 - x0)
        return known[-1][1]

    out: Dict[str, Dict] = {}
    for area, pyeong in area_to_pyeong.items():
        py = area / PYEONG
        exact = any(str(area).startswith(p) for p in BUNYANGGA)
        v = out.setdefault(pyeong, {"vals": [], "est": True})
        v["vals"].append(interp(py))
        if exact:
            v["est"] = False
    return {p: {"perPyeong": round(statistics.mean(v["vals"])), "est": v["est"]}
            for p, v in out.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", default="data/firstige")
    parser.add_argument("--outfile", default="data/firstige/video_all.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    indir = Path(args.indir)
    trades = [r for r in live_sales(load_csv(indir / "firstige_매매_전건.csv")) if r.get("평당_만원")]
    presale = [r for r in live_sales(load_csv(indir / "firstige_분양권_전건.csv")) if r.get("평당_만원")]

    unit_rows = load_csv(indir / "세대수_전용면적별.csv")
    units_by_pyeong: Dict[str, int] = defaultdict(int)
    area_to_pyeong: Dict[float, str] = {}
    for r in unit_rows:
        units_by_pyeong[r["평형"]] += int(r["세대수"])
        area_to_pyeong[float(r["전용면적"])] = r["평형"]
    pyeongs = sorted(units_by_pyeong, key=int)
    total_units = sum(units_by_pyeong.values())

    launch = launch_per_pyeong(area_to_pyeong)
    log.info("평형 %s · 총 %s세대", pyeongs, total_units)
    for p in pyeongs:
        log.info("  %s평 %4d세대 · 분양가 평당 %s만원%s",
                 p, units_by_pyeong[p], launch[p]["perPyeong"],
                 " (추정)" if launch[p]["est"] else "")

    # 평형별 상태
    orig = {p: float(units_by_pyeong[p]) for p in pyeongs}
    held: Dict[str, Dict[int, float]] = {p: defaultdict(float) for p in pyeongs}
    decay = {p: 1.0 - 1.0 / units_by_pyeong[p] for p in pyeongs}
    launch_bucket = {p: int(launch[p]["perPyeong"] // BUCKET) * BUCKET for p in pyeongs}

    # 분양권 자료에는 건축물대장 세대수 표에 없는 면적이 몇 건 섞여 있다
    # (분양 당시 표기 면적이 준공 후 대장과 다른 경우). 세대수를 모르면 분포를
    # 만들 수 없으므로 제외하고 몇 건인지 남긴다.
    known = set(pyeongs)
    dropped = [r for r in trades + presale if r["평형"] not in known]
    if dropped:
        log.warning("세대수 표에 없는 평형 %s건 제외: %s", len(dropped),
                    sorted({f"{r['평형']}평({r['전용면적']}㎡)" for r in dropped}))
    trades = [r for r in trades if r["평형"] in known]
    presale = [r for r in presale if r["평형"] in known]

    events = sorted(trades + presale, key=lambda r: r["계약일자"])
    by_q_event: Dict[str, List] = defaultdict(list)
    by_q_trade: Dict[str, List] = defaultdict(list)
    for r in events:
        by_q_event[quarter_of(r["계약일자"])].append(r)
    for r in trades:
        by_q_trade[quarter_of(r["계약일자"])].append(r)

    qs = quarters_between(quarter_of(events[0]["계약일자"]),
                          quarter_of(events[-1]["계약일자"]))

    last_by_p: Dict[str, float] = {}
    last_all = last_all_real = None
    timeline = []
    for q in qs:
        for ev in by_q_event[q]:
            p = ev["평형"]
            orig[p] *= decay[p]
            for e in list(held[p]):
                held[p][e] *= decay[p]
            held[p][int(float(ev["평당_만원"]) // BUCKET) * BUCKET] += 1.0

        rows = by_q_trade[q]
        if rows:
            last_all = round(statistics.median(float(r["평당_만원"]) for r in rows))
            last_all_real = round(statistics.median(
                real(float(r["평당_만원"]), year_of(r)) for r in rows))
            for p in pyeongs:
                sub = [float(r["평당_만원"]) for r in rows if r["평형"] == p]
                if sub:
                    last_by_p[p] = round(statistics.median(sub))

        edges = sorted({e for p in pyeongs for e in held[p]} | set(launch_bucket.values()))
        holdings = []
        for e in edges:
            o = [round(orig[p], 1) if launch_bucket[p] == e else 0.0 for p in pyeongs]
            t = [round(held[p].get(e, 0.0), 1) for p in pyeongs]
            if sum(o) + sum(t) < 0.05:
                continue
            holdings.append({"edge": e, "orig": o, "trad": t})

        tot = sum(orig.values()) + sum(sum(h.values()) for h in held.values())
        assert abs(tot - total_units) < 1.0, f"{q} 합계 {tot} != {total_units}"

        timeline.append({
            "q": q, "n": len(rows),
            "all": last_all, "allReal": last_all_real,
            "byP": {p: last_by_p.get(p) for p in pyeongs},
            "holdings": holdings,
        })
    log.info("검산 통과 — 모든 분기에서 보유 합계 = %s세대", total_units)

    # 요약
    fin = timeline[-1]
    orig_total = sum(orig.values())
    def band(lo, hi):
        s = 0.0
        for h in fin["holdings"]:
            if lo <= h["edge"] < hi:
                s += sum(h["orig"]) + sum(h["trad"])
        return s
    launch_hi = max(launch_bucket.values()) + BUCKET
    now_all = fin["all"]

    data = {
        "meta": {
            "complex": "래미안퍼스티지", "address": "서울 서초구 반포동 18-1",
            "units": total_units, "bucket": BUCKET, "baseYear": BASE_YEAR,
            "pyeongs": [{"p": p, "units": units_by_pyeong[p],
                         "label": {"18": "전용 59㎡", "26": "전용 84㎡", "35": "전용 115·117㎡",
                                   "41": "전용 136㎡", "51": "전용 169㎡", "60": "전용 198㎡",
                                   "67": "전용 222㎡"}.get(p, f"{p}평"),
                         "launch": launch[p]["perPyeong"], "est": launch[p]["est"]}
                        for p in pyeongs],
        },
        "conditions": [
            f"7개 평형 {total_units:,}세대 전체",
            f"국토부 실거래가 매매 {len(trades):,}건 + 분양권 {len(presale)}건",
            f"{events[0]['계약일자']} ~ {events[-1]['계약일자']}",
        ],
        "launchBand": {"low": min(launch_bucket.values()),
                       "high": launch_hi,
                       "note": "2008-10 분양 · 평당 3,837~4,134만원"},
        "marks": [
            {"q": "2009-Q3", "label": "입주", "sub": "2009-07"},
            {"q": "2013-Q4", "label": "실질 최저", "sub": "2013년"},
            {"q": max((t for t in timeline if t["all"]), key=lambda t: t["all"])["q"],
             "label": "최고가", "sub": ""},
        ],
        "timeline": timeline,
        "summary": {
            "origHold": round(orig_total), "origPct": round(orig_total / total_units * 100),
            "below6000": round(band(0, 6_000)), "below6000Pct": round(band(0, 6_000) / total_units * 100),
            "above15000": round(band(15_000, 10 ** 9)),
            "above15000Pct": round(band(15_000, 10 ** 9) / total_units * 100, 1),
            "nowAll": now_all,
            "launchMid": round(statistics.mean(launch[p]["perPyeong"] for p in pyeongs)),
            "tradesCount": len(trades),
        },
    }

    out = Path(args.outfile)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    log.info("완료 — 분기 %s · 원분양 잔존 %s세대(%s%%) · %.0fKB -> %s",
             len(timeline), data["summary"]["origHold"], data["summary"]["origPct"],
             out.stat().st_size / 1024, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
