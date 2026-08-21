#!/usr/bin/env python3
"""영상 렌더러에 넘길 데이터 묶음(JSON)을 만든다.

전용 84㎡(시장 통칭 34평) 하나로 이야기를 끌고 간다. 자막 표기도 '전용 84㎡(34평)'.

분기마다 두 가지를 함께 담는다 — 가격과 보유 분포가 같이 움직이는 그림을 위해서다.
  · 가격    그 분기까지의 중위 거래금액 (명목·실질). 거래가 없는 분기는 직전 값을 잇는다
  · 보유분포 그 시점에 세대들이 어느 가격대에 있는지. **합계는 항상 세대수**

보유 분포 계산 (firstige_holdings.py 와 같은 방식)
  분양 시점에 전 세대가 분양가 칸에 있다. 거래가 한 건 일어나면 한 세대가
  어딘가에서 빠져나와 체결가 칸으로 들어간다. 누가 팔았는지 모르므로
  '보유자 누구나 똑같은 확률로 판다'고 놓고 기댓값으로 옮긴다 —
  모든 칸에 (1 - 1/N) 을 곱하고 체결가 칸에 1을 더한다. 합계는 N 으로 유지된다.

사용법:
    python scripts/firstige_video_data.py --outfile ../../backtest-reels/content/apt-firstige-84.json
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
BUCKET = 20_000   # 보유 분포 구간폭 2억 (만원)


def quarters_between(first: str, last: str) -> List[str]:
    y0, q0 = int(first[:4]), int(first[-1])
    y1, q1 = int(last[:4]), int(last[-1])
    out = []
    y, q = y0, q0
    while (y, q) <= (y1, q1):
        out.append(f"{y}-Q{q}")
        q += 1
        if q == 5:
            q, y = 1, y + 1
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", default="data/firstige")
    parser.add_argument("--outfile", default="data/firstige/video_84.json")
    parser.add_argument("--area", default=PYEONG_TARGET_AREA_PREFIX)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    indir = Path(args.indir)
    pick = lambda rows: [r for r in rows
                         if r["전용면적"].startswith(args.area) and r.get("거래금액_만원")]
    trades = pick(live_sales(load_csv(indir / "firstige_매매_전건.csv")))
    presale = pick(live_sales(load_csv(indir / "firstige_분양권_전건.csv")))
    events = sorted(trades + presale, key=lambda r: r["계약일자"])

    units = {r["전용면적"]: int(r["세대수"]) for r in load_csv(indir / "세대수_전용면적별.csv")}
    N = sum(v for k, v in units.items() if k.startswith(args.area))
    low, high = BUNYANGGA[args.area]
    launch_bucket = int(((low + high) / 2) // BUCKET) * BUCKET
    log.info("전용 %s㎡대 · %s세대 · 매매 %s건 + 분양권 %s건", args.area, N, len(trades), len(presale))

    qs = quarters_between(quarter_of(events[0]["계약일자"]),
                          quarter_of(events[-1]["계약일자"]))

    # 분기별 거래 묶기
    by_q_trade: Dict[str, List] = defaultdict(list)   # 매매만 (가격선용)
    by_q_event: Dict[str, List] = defaultdict(list)   # 매매 + 분양권 (분포용)
    for r in trades:
        by_q_trade[quarter_of(r["계약일자"])].append(r)
    for r in events:
        by_q_event[quarter_of(r["계약일자"])].append(r)

    orig = float(N)
    held: Dict[int, float] = defaultdict(float)
    decay = 1.0 - 1.0 / N

    timeline = []
    last_nom = last_real = None
    for q in qs:
        for ev in by_q_event[q]:
            orig *= decay
            for e in list(held):
                held[e] *= decay
            held[int(float(ev["거래금액_만원"]) // BUCKET) * BUCKET] += 1.0

        rows = by_q_trade[q]
        if rows:
            last_nom = round(statistics.median(float(r["거래금액_만원"]) for r in rows))
            last_real = round(statistics.median(real(float(r["거래금액_만원"]), year_of(r))
                                                for r in rows))
        total = orig + sum(held.values())
        assert abs(total - N) < 0.5, f"{q} 합계 {total} != {N}"
        timeline.append({
            "q": q,
            "n": len(rows),
            "nominal": last_nom,
            "real": last_real,
            "orig": round(orig, 1),
            "buckets": [{"edge": e, "count": round(c, 1)}
                        for e, c in sorted(held.items()) if c >= 0.05],
        })
    log.info("검산 통과 — 모든 분기에서 보유 합계 = %s세대", N)

    # ── 요약
    final = timeline[-1]
    fin = {b["edge"]: b["count"] for b in final["buckets"]}
    below18 = final["orig"] + sum(c for e, c in fin.items() if e < 180_000)
    above50 = sum(c for e, c in fin.items() if e >= 500_000)
    mid = (low + high) / 2
    mid_real = real(mid, BUNYANG_YEAR)
    recent = [r for r in trades if r["계약일자"] >= "2025-08-01"]
    now_med = statistics.median(float(r["거래금액_만원"]) for r in recent)
    top = max(final["buckets"], key=lambda b: b["count"])

    data = {
        "meta": {
            "complex": "래미안퍼스티지",
            "typeLabel": "전용 84㎡(34평)",
            "units": N,
            "bucket": BUCKET,
            "baseYear": BASE_YEAR,
            "assumption": "보유자 누구나 똑같은 확률로 판다고 놓고 기댓값으로 계산",
        },
        "conditions": [
            "전용 84㎡(34평) · 955세대",
            f"국토부 실거래가 매매 {len(trades):,}건 + 분양권 {len(presale)}건",
            f"{events[0]['계약일자']} ~ {events[-1]['계약일자']}",
        ],
        "launch": {"date": "2008-10", "low": low, "high": high,
                   "mid": round(mid), "midReal": round(mid_real),
                   "bucket": launch_bucket},
        "timeline": timeline,
        "marks": [
            {"q": quarter_of(trades[0]["계약일자"]), "label": "입주", "sub": "2009-07"},
            {"q": "2013-Q4", "label": "실질 최저", "sub": "2013년"},
            {"q": max((t for t in timeline if t["nominal"]),
                      key=lambda t: t["nominal"])["q"], "label": "최고가", "sub": ""},
        ],
        "summary": {
            "launchMid": round(mid), "launchMidReal": round(mid_real),
            "nowMedian": round(now_med), "nowCount": len(recent),
            "nominalMultiple": round(now_med / mid, 2),
            "realMultiple": round(now_med / mid_real, 2),
            "origHold": round(final["orig"]),
            "origPct": round(final["orig"] / N * 100),
            "below18": round(below18), "below18Pct": round(below18 / N * 100),
            "above50": round(above50, 1), "above50Pct": round(above50 / N * 100, 1),
            "topBucket": f"{top['edge']/10_000:.0f}~{(top['edge']+BUCKET)/10_000:.0f}억",
            "topCount": round(top["count"]),
            "tradesCount": len(trades),
        },
    }

    out = Path(args.outfile)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    log.info("완료 — 분기 %s개 · 원분양 잔존 %s세대(%s%%) -> %s",
             len(timeline), data["summary"]["origHold"], data["summary"]["origPct"], out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
