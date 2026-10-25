"""
prepare_data.py
원/달러(USD/KRW) 일별 환율 데이터를 내려받아 (date, value, memo) CSV로 정리한다.

- 출처: 미국 연방준비제도(Federal Reserve) H.10 "Foreign Exchange Rates"
        (뉴욕 시장 정오 매입환율, FRED 시리즈 DEXKOUS와 같은 값)
- 배포 미러: GitHub datasets/exchange-rates (data/daily.csv)
- 기본 구간: 2025-10-16 ~ 2026-10-16 (최근 1년, 고시일 251개)
- 결측(빈 값)은 미국 공휴일 등 고시가 없던 날이므로 값을 만들어 넣지 않고 행을 뺀다.

실행 예시
    python scripts/prepare_data.py                       # 인터넷에서 받아 정리
    python scripts/prepare_data.py --local daily.csv     # 이미 받은 파일로 정리
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import urllib.request
from datetime import date
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/datasets/exchange-rates/master/data/daily.csv"
COUNTRY = "South Korea"
MEMO = "FRED H.10"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "usdkrw_daily.csv"


def read_source(local: str | None) -> list[dict]:
    if local:
        text = Path(local).read_text(encoding="utf-8")
    else:
        print(f"[1/3] 내려받기: {SOURCE_URL}")
        with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
            text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def main() -> int:
    parser = argparse.ArgumentParser(description="USD/KRW 일별 환율 CSV 만들기")
    parser.add_argument("--start", default="2025-10-16", help="시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-10-16", help="종료일 (YYYY-MM-DD)")
    parser.add_argument("--local", default=None, help="이미 받은 daily.csv 경로")
    parser.add_argument("--out", default=str(OUT_PATH), help="저장 경로")
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    rows = read_source(args.local)

    print(f"[2/3] {COUNTRY} 행만 고르기: {start} ~ {end}")
    picked, missing = [], []
    for row in rows:
        if row.get("Country") != COUNTRY:
            continue
        day = date.fromisoformat(row["Date"])
        if not (start <= day <= end):
            continue
        raw = (row.get("Exchange rate") or "").strip()
        if not raw:
            missing.append(day.isoformat())
            continue
        picked.append({"date": day.isoformat(), "value": round(float(raw), 2), "memo": MEMO})

    picked.sort(key=lambda r: r["date"])
    dates = [r["date"] for r in picked]
    if len(dates) != len(set(dates)):
        print("중복 날짜가 있습니다. 원본을 확인하세요.", file=sys.stderr)
        return 1
    if len(picked) < 100:
        print(f"데이터가 {len(picked)}개뿐입니다. 100개 이상이 필요합니다.", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "value", "memo"])
        writer.writeheader()
        writer.writerows(picked)

    print("[3/3] 저장 완료")
    print(f"  파일: {out}")
    print(f"  기간: {picked[0]['date']} ~ {picked[-1]['date']}")
    print(f"  개수: {len(picked)}개 (값이 없는 고시 휴일 {len(missing)}일 제외)")
    if missing:
        print(f"  제외한 날짜: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
