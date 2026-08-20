#!/usr/bin/env python3
"""firstige_report.py 를 네트워크 없이 검증한다 (월별 XML 캐시를 심어 실행)."""
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.molit_rtms_service import month_range  # noqa: E402

HDR = ('<?xml version="1.0" encoding="UTF-8"?><response><header>'
       '<resultCode>000</resultCode><resultMsg>OK</resultMsg></header><body><items>')
FTR = '</items><numOfRows>1000</numOfRows><pageNo>1</pageNo><totalCount>{n}</totalCount></body></response>'


def trade_item(apt, area, floor, y, m, d, amount, rgst="", cdeal=""):
    return (f"<item><aptNm>{apt}</aptNm><umdNm>반포동</umdNm><jibun>18-1</jibun>"
            f"<excluUseAr>{area}</excluUseAr><floor>{floor}</floor><buildYear>2009</buildYear>"
            f"<dealYear>{y}</dealYear><dealMonth>{m}</dealMonth><dealDay>{d}</dealDay>"
            f"<dealAmount>{amount}</dealAmount><rgstDate>{rgst}</rgstDate>"
            f"<cdealType>{cdeal}</cdealType><sggCd>11650</sggCd></item>")


def rent_item(apt, area, floor, y, m, d, deposit, rent):
    return (f"<item><aptNm>{apt}</aptNm><umdNm>반포동</umdNm><jibun>18-1</jibun>"
            f"<excluUseAr>{area}</excluUseAr><floor>{floor}</floor><buildYear>2009</buildYear>"
            f"<dealYear>{y}</dealYear><dealMonth>{m}</dealMonth><dealDay>{d}</dealDay>"
            f"<deposit>{deposit}</deposit><monthlyRent>{rent}</monthlyRent>"
            f"<sggCd>11650</sggCd></item>")


def wrap(items):
    return HDR + "".join(items) + FTR.format(n=len(items))


EMPTY = wrap([])

TRADE_2025 = wrap([
    trade_item("래미안퍼스티지", "84.93", 25, 2025, 6, 17, "545,000", "25.07.30"),
    trade_item("래미안 퍼스티지", "84.93", 15, 2025, 6, 20, "515,000", "25.08.02"),   # 공백 표기
    trade_item("래미안퍼스티지", "59.96", 8, 2025, 6, 25, "400,000", ""),
    trade_item("래미안퍼스티지", "198.04", 13, 2025, 6, 28, "805,000", "", "O"),      # 해제 거래
    trade_item("반포자이", "84.94", 10, 2025, 6, 11, "510,000"),                      # 다른 단지
])
TRADE_2024 = wrap([
    trade_item("래미안퍼스티지", "84.93", 20, 2024, 5, 3, "430,000"),
])
RENT_2025 = wrap([
    rent_item("래미안퍼스티지", "84.93", 23, 2025, 6, 18, "170,000", "0"),   # 전세
    rent_item("래미안퍼스티지", "84.93", 7, 2025, 6, 14, "80,500", "440"),   # 월세
    rent_item("래미안퍼스티지", "59.96", 11, 2025, 6, 9, "103,000", "0"),    # 전세
    rent_item("아크로리버파크", "84.97", 3, 2025, 6, 5, "150,000", "0"),     # 다른 단지
])


def seed(outdir: Path):
    for kind in ("매매", "전월세"):
        d = outdir / "_cache" / kind / "11650"
        d.mkdir(parents=True, exist_ok=True)
        for ym in month_range("202405", "202506"):
            if kind == "매매":
                body = TRADE_2025 if ym == "202506" else (TRADE_2024 if ym == "202405" else EMPTY)
            else:
                body = RENT_2025 if ym == "202506" else EMPTY
            (d / f"{ym}_p1.xml").write_text(body, encoding="utf-8")


def read(path: Path):
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def check(label, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {label}{' — ' + detail if detail else ''}")
    return cond


def main() -> int:
    outdir = ROOT / "data" / "_firstige_test"
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    seed(outdir)

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "firstige_report.py"),
         "--service-key", "OFFLINE", "--start", "202405", "--rent-start", "202405",
         "--end", "202506", "--outdir", str(outdir)],
        capture_output=True, text=True,
    )
    ok = check("종료코드 0", proc.returncode == 0, proc.stderr[-500:])

    sale = read(outdir / "firstige_매매_전건.csv")
    jeonse = read(outdir / "firstige_전세_전건.csv")
    wolse = read(outdir / "firstige_월세_전건.csv")

    # 202405 1건 + 202506 4건(반포자이 제외) = 5건
    ok &= check("퍼스티지 매매 5건만 수집", len(sale) == 5, f"{len(sale)}건")
    ok &= check("공백 표기 '래미안 퍼스티지'도 매칭", any(r["층"] == "15" for r in sale))
    ok &= check("반포자이 제외", all("자이" not in r["단지명"] for r in sale))
    ok &= check("전세 2건 / 월세 1건 분리", len(jeonse) == 2 and len(wolse) == 1,
                f"전세{len(jeonse)}/월세{len(wolse)}")
    ok &= check("아크로리버파크 제외", all("아크로" not in r["단지명"] for r in jeonse))

    row84 = next(r for r in sale if r["전용면적"] == "84.93" and r["층"] == "25")
    ok &= check("평형 환산 84.93㎡ -> 26평", row84["평형"] == "26", row84["평형"])
    ok &= check("평당가 계산", row84.get("평당_만원", "").startswith("2121"), row84.get("평당_만원", ""))

    agg = read(outdir / "firstige_평형별_매매.csv")
    a26 = next(r for r in agg if r["평형"] == "26")
    ok &= check("26평 3건 집계(2024·2025)", a26["건수"] == "3", a26["건수"])
    ok &= check("26평 평균 (43+54.5+51.5)/3 = 49.67억",
                a26["평균_만원"] == "496667", a26["평균_만원"])
    ok &= check("26평 등기일자 보유 2건", a26["등기일자보유"] == "2", a26["등기일자보유"])
    ok &= check("해제 거래(60평) 집계 제외", all(r["평형"] != "60" for r in agg),
                str([r["평형"] for r in agg]))

    pivot = read(outdir / "firstige_평형별연도별_매매.csv")
    p26 = next(r for r in pivot if r["평형"] == "26")
    ok &= check("피벗 2024 평균 43억", p26["2024"] == "430000", p26["2024"])
    ok &= check("피벗 2025 평균 53억", p26["2025"] == "530000", p26["2025"])

    jagg = read(outdir / "firstige_평형별_전세.csv")
    ok &= check("전세 평형별 26평·18평", {r["평형"] for r in jagg} == {"26", "18"},
                str({r["평형"] for r in jagg}))

    wagg = read(outdir / "firstige_평형별_월세.csv")
    ok &= check("월세 평균 월세 440만원", wagg[0].get("평균_월세_만원") == "440",
                wagg[0].get("평균_월세_만원", ""))

    report = (outdir / "REPORT_firstige.md").read_text(encoding="utf-8")
    for section in ("1. 매매 — 평형별", "3. 전세 — 평형별", "5. 월세 — 평형별"):
        ok &= check(f"리포트 '{section}' 포함", section in report)
    # 총 5건 중 해제 1건 -> 집계 대상 4건
    ok &= check("리포트에 해제 1건 표기", "| 매매 | 5 | 1 | 4 |" in report.replace(",", ""))

    shutil.rmtree(outdir)
    print("\n=== 전체 통과 ===" if ok else "\n=== 실패 항목 있음 ===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
