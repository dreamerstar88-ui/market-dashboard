#!/usr/bin/env python3
"""건축물대장 전유부로 래미안퍼스티지의 전용면적별 세대수를 확정한다.

부동산 정보 사이트가 아니라 원자료(건축물대장)로 세대수를 세는 것이 목적이다.
국토교통부 건축HUB 건축물대장정보 서비스의 '전유공용면적' 조회를 쓴다.
호(戶)마다 전유·공용 면적이 여러 줄로 나오므로 전유 + 주거용만 남겨
동·호 단위로 하나씩 세고, 전용면적별로 묶는다.

사용법:
    python scripts/firstige_units.py --outdir data/firstige

인증키는 저장소 루트의 .molit_key 를 자동으로 읽는다.
받은 원본 JSON은 --outdir/_cache_bldrgst/ 에 페이지별로 남아 재실행 시 재호출하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows 콘솔(cp949)에서 한글·기호 출력이 깨지지 않도록 표준출력을 UTF-8로 고정한다
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:  # 파이프로 리다이렉트된 경우 등
        pass

from services.molit_rtms_service import resolve_service_key  # noqa: E402

ENDPOINT = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrExposPubuseAreaInfo"
SIGUNGU_CD = "11650"      # 서울특별시 서초구
BJDONG_CD = "10700"       # 반포동
BUN, JI = "0018", "0001"  # 지번 18-1
PYEONG = 3.3058
ROWS = 1000

log = logging.getLogger("firstige_units")


def fetch_page(key: str, page: int, cache_dir: Path) -> dict:
    cached = cache_dir / f"p{page:03d}.json"
    if cached.exists() and cached.stat().st_size > 0:
        return json.loads(cached.read_text(encoding="utf-8"))

    params = {
        "serviceKey": key, "sigunguCd": SIGUNGU_CD, "bjdongCd": BJDONG_CD,
        "bun": BUN, "ji": JI, "numOfRows": str(ROWS), "pageNo": str(page), "_type": "json",
    }
    last_err = None
    for attempt in range(7):
        try:
            resp = requests.get(ENDPOINT, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            cached.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            time.sleep(0.35)   # 연속 호출이 빠르면 포털이 비JSON 응답으로 막는다
            return data
        except Exception as exc:  # 네트워크/일시 오류는 지수 백오프로 재시도
            last_err = exc
            masked = str(exc).replace(key, "***SERVICE_KEY***")
            wait = 2 ** attempt
            log.warning("p%s 실패(%s) — %ss 후 재시도", page, masked, wait)
            time.sleep(wait)
    raise RuntimeError(f"전유공용면적 p{page} 호출 실패: "
                       f"{str(last_err).replace(key, '***SERVICE_KEY***')}")


def items_of(data: dict) -> List[dict]:
    body = data["response"]["body"]
    items = body.get("items")
    if not items:
        return []
    inner = items["item"] if isinstance(items, dict) else items
    return inner if isinstance(inner, list) else [inner]


def collect(key: str, cache_dir: Path) -> List[dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    first = fetch_page(key, 1, cache_dir)
    total = int(first["response"]["body"]["totalCount"])
    rows = items_of(first)
    # 이 API는 numOfRows 를 무시하고 한 페이지에 100행만 준다.
    # 요청값이 아니라 실제로 받은 행 수로 페이지 수를 계산한다.
    page_size = len(rows) or ROWS
    pages = (total + page_size - 1) // page_size
    log.info("전유공용면적 총 %s행 / 페이지당 %s행 / %s페이지", total, page_size, pages)
    for page in range(2, pages + 1):
        rows.extend(items_of(fetch_page(key, page, cache_dir)))
        log.info("p%s 누적 %s행", page, len(rows))

    if len(rows) != total:
        log.warning("행 수 불일치 — totalCount %s vs 수집 %s", total, len(rows))
    return rows


def households(rows: List[dict]) -> Dict[tuple, float]:
    """동·호 단위로 주거용 전유면적을 합산한다."""
    per_unit: Dict[tuple, float] = defaultdict(float)
    for r in rows:
        if r.get("exposPubuseGbCdNm") != "전유":
            continue
        if r.get("mainPurpsCdNm") != "아파트":
            continue
        try:
            area = float(r.get("area") or 0)
        except (TypeError, ValueError):
            continue
        if area <= 0:
            continue
        per_unit[(str(r.get("dongNm")), str(r.get("hoNm")))] += area
    return per_unit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="data/firstige")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = collect(resolve_service_key(), outdir / "_cache_bldrgst")

    per_unit = households(rows)
    log.info("주거용 전유 세대 %s호", len(per_unit))

    by_area: Dict[str, int] = defaultdict(int)
    for area in per_unit.values():
        by_area[f"{area:.2f}"] += 1

    out = []
    for area in sorted(by_area, key=float):
        a = float(area)
        out.append({
            "전용면적": area,
            "평수": f"{a / PYEONG:.1f}",
            "평형": str(round(a / PYEONG)),
            "세대수": by_area[area],
        })

    import csv
    path = outdir / "세대수_전용면적별.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)

    by_pyeong: Dict[str, int] = defaultdict(int)
    for r in out:
        by_pyeong[r["평형"]] += r["세대수"]

    lines = ["# 래미안퍼스티지 전용면적별 세대수 (건축물대장 전유부)", "",
             "출처: 국토교통부 건축HUB 건축물대장정보 서비스, 전유공용면적 조회.",
             f"서울 서초구 반포동 18-1 · 조회 행 {len(rows):,}행 · 주거용 전유 세대 {len(per_unit):,}호", "",
             "## 전용면적별", "", "| 전용면적 | 평수 | 평형 | 세대수 |", "|---:|---:|---:|---:|"]
    for r in out:
        lines.append(f"| {r['전용면적']}㎡ | {r['평수']}평 | {r['평형']}평 | {r['세대수']:,} |")
    lines += ["", "## 평형별 (전용면적 ÷ 3.3058 반올림)", "", "| 평형 | 세대수 |", "|---:|---:|"]
    for p in sorted(by_pyeong, key=int):
        lines.append(f"| {p}평 | {by_pyeong[p]:,} |")
    lines += ["", f"**합계 {sum(by_pyeong.values()):,}세대**"]
    (outdir / "REPORT_세대수.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    log.info("완료 — 전용면적 %s종 / 합계 %s세대 -> %s",
             len(out), sum(by_pyeong.values()), outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
