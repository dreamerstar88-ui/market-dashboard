#!/usr/bin/env python3
"""보유 가격대 분포 — 합계가 세대수인 매물대.

지금까지 만든 '매물대'는 주식 차트 정의를 그대로 옮긴 것이라 합계가 거래 건수였다.
이 스크립트는 합계가 **세대수**인 분포를 만든다. 즉 "지금 이 단지 사람들이
얼마에 사서 들고 있나"에 해당하는 그림이다.

동·호가 비공개라 세대 단위 추적은 불가능하다. 대신 분포 수준에서 추적한다.

  · 분양 시점에 전 세대가 분양가 한 칸에 있다.
  · 매매가 한 건 일어나면 한 세대가 어딘가에서 빠져나와 체결가 칸으로 들어간다.
  · 누가 팔았는지 모르므로 **보유자 누구나 똑같은 확률로 판다**고 놓는다.
    그러면 각 칸은 자기 비중만큼 잃는다 — 모든 칸에 (1 - 1/N) 을 곱하고
    체결가 칸에 1을 더하면 된다. 합계는 항상 N 으로 유지된다.
    이건 표본추출이 아니라 기댓값이라 결과가 매번 같다.

이 가정의 한계
  · 실제로는 손바뀜이 균등하지 않다. 자주 팔리는 물건이 따로 있고
    실거주자는 거의 팔지 않는다. 그러면 실제 미거래 세대는 이 계산보다 많아진다.
  · 조합원 물량의 실제 매입가는 옛 아파트 취득가 + 추가분담금이라 알 수 없다.
    여기서는 전부 분양가 자리에 두고, 그 덩어리를 '원분양 보유'로 따로 표기한다.

사용법:
    python scripts/firstige_holdings.py --outdir data/firstige/analysis
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
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
    BUNYANGGA, PYEONG_TARGET_AREA_PREFIX, load_csv, live_sales, quarter_of,
)

log = logging.getLogger("firstige_holdings")
BUCKET = 20_000          # 구간폭 2억 (만원)


def bucket_of(price: float) -> int:
    return int(price // BUCKET) * BUCKET


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", default="data/firstige")
    parser.add_argument("--outdir", default="data/firstige/analysis")
    parser.add_argument("--area", default=PYEONG_TARGET_AREA_PREFIX,
                        help="전용면적 앞자리 (기본 84)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    indir, outdir = Path(args.indir), Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    def pick(rows):
        return [r for r in rows if r["전용면적"].startswith(args.area) and r.get("거래금액_만원")]

    trades = pick(live_sales(load_csv(indir / "firstige_매매_전건.csv")))
    presale = pick(live_sales(load_csv(indir / "firstige_분양권_전건.csv")))
    events = sorted(trades + presale, key=lambda r: r["계약일자"])

    units = {r["전용면적"]: int(r["세대수"]) for r in load_csv(indir / "세대수_전용면적별.csv")}
    N = sum(v for k, v in units.items() if k.startswith(args.area))
    if not N:
        log.error("세대수를 못 찾았습니다 (전용 %s㎡대)", args.area)
        return 1

    low, high = BUNYANGGA[args.area]
    launch_bucket = bucket_of((low + high) / 2)
    log.info("전용 %s㎡대 · %s세대 · 거래 %s건(매매 %s + 분양권 %s) · 분양가 칸 %s",
             args.area, N, len(events), len(trades), len(presale), launch_bucket)

    # 상태: 아직 한 번도 안 팔린 원분양 물량 + 팔려서 매입가가 정해진 물량
    orig = float(N)
    held: Dict[int, float] = defaultdict(float)
    decay = 1.0 - 1.0 / N

    snapshots: List[Dict] = []
    last_q = None

    def snapshot(q: str, date: str) -> Dict:
        return {
            "q": q, "date": date,
            "orig": round(orig, 1),
            "origPct": round(orig / N * 100, 1),
            "launchBucket": launch_bucket,
            "buckets": [{"edge": e, "count": round(c, 2)}
                        for e, c in sorted(held.items()) if c >= 0.05],
            "total": round(orig + sum(held.values()), 1),
        }

    for ev in events:
        q = quarter_of(ev["계약일자"])
        if last_q is not None and q != last_q:
            snapshots.append(snapshot(last_q, ev["계약일자"]))
        # 보유자 누구나 똑같은 확률로 판다 → 모든 칸이 자기 비중만큼 잃는다
        orig *= decay
        for e in list(held):
            held[e] *= decay
        held[bucket_of(float(ev["거래금액_만원"]))] += 1.0
        last_q = q
    snapshots.append(snapshot(last_q, events[-1]["계약일자"]))

    # 검산 — 합계는 항상 세대수여야 한다
    bad = [s for s in snapshots if abs(s["total"] - N) > 0.5]
    if bad:
        log.error("합계가 세대수와 어긋난 분기 %s개", len(bad))
        return 1
    log.info("검산 통과 — 모든 분기에서 합계 = %s세대", N)

    final = snapshots[-1]
    log.info("최종 — 원분양 보유 %.0f세대(%.1f%%) / 거래로 매입가 정해진 물량 %.0f세대",
             final["orig"], final["origPct"], N - final["orig"])

    out = {
        "meta": {
            "area": args.area, "units": N, "bucket": BUCKET,
            "launchLow": low, "launchHigh": high, "launchBucket": launch_bucket,
            "events": len(events), "trades": len(trades), "presale": len(presale),
            "assumption": "보유자 누구나 똑같은 확률로 판다고 놓고 기댓값으로 계산",
        },
        "snapshots": snapshots,
    }
    (outdir / f"보유분포_{args.area}.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")

    with (outdir / f"보유분포_{args.area}_최종.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["구간시작_만원", "구간표기", "보유세대_추정"])
        w.writerow([launch_bucket, "원분양 보유(한 번도 안 팔린 집)", round(final["orig"], 1)])
        for bk in final["buckets"]:
            w.writerow([bk["edge"], f"{bk['edge']/10_000:.0f}~{(bk['edge']+BUCKET)/10_000:.0f}억",
                        round(bk["count"], 1)])

    log.info("완료 — 분기 %s개 -> %s", len(snapshots), outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
