"""
analyze_data.py
CSV를 분석해 요약 정보를 만든다. 서버(/api/data/summary)와 같은 함수(app/services/analysis.py)를 쓰므로
여기서 나온 숫자와 API 응답 숫자가 같다.

실행 (backend 폴더에서)
    python scripts/analyze_data.py
산출: ../docs/analysis_summary.json (요약 + 확장 통계)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings  # noqa: E402
from app.services.analysis import compute_statistics, compute_summary  # noqa: E402

CSV_PATH = BACKEND_DIR / "data" / "usdkrw_daily.csv"
OUT_PATH = BACKEND_DIR.parent / "docs" / "analysis_summary.json"


def main() -> int:
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        records = [{"date": r["date"], "value": float(r["value"]), "memo": r["memo"]} for r in csv.DictReader(f)]

    s = Settings()  # 기본 설정값(추세 비교 20개, 기준 0.5%)
    dataset = {"name": s.dataset_name, "unit": s.dataset_unit, "source": s.dataset_source}
    summary = compute_summary(records, dataset, s.trend_window, s.trend_threshold_pct)
    stats = compute_statistics(records)
    summary.pop("generated_at")
    stats.pop("generated_at")

    m = summary["metrics"]
    print("=== 데이터 요약 ===")
    print(f"기간: {summary['period']}  |  개수: {summary['count']}개")
    print(f"평균 {m['average']:,.2f}원  |  최고 {m['max']:,.2f}원 ({m['max_date']})  |  최저 {m['min']:,.2f}원 ({m['min_date']})")
    print(f"최신 {m['latest']:,.2f}원 ({m['latest_date']})  |  기간 변화 {m['change']:+,.2f}원 ({m['change_pct']:+.2f}%)")
    print(f"추세: {summary['trend']}")
    print("\n=== 월별 평균 ===")
    for row in summary["monthly"]:
        change = f"{row['change_pct']:+.2f}%" if row["change_pct"] is not None else "  -  "
        print(f"{row['month']}  평균 {row['average']:,.2f}  최저 {row['min']:,.2f}  최고 {row['max']:,.2f}  "
              f"월말 {row['last']:,.2f}  전월 대비 {change}  ({row['count']}개)")
    print("\n=== 확장 통계 ===")
    v = stats["volatility"]
    print(f"이동평균 MA5/20/60: {stats['moving_averages']}")
    print(f"일간 변동률 표준편차 {v['daily_std_pct']}%, 연환산 {v['annualized_pct']}%, 하루 평균 변동폭 {v['avg_abs_change']}원")
    dd = stats["max_drawdown"]
    print(f"고점 대비 최대 하락: {dd['pct']}% ({dd['start_date']} {dd['start_value']:,.2f} → {dd['end_date']} {dd['end_value']:,.2f})")
    print(f"상승일 {stats['up_days']} / 하락일 {stats['down_days']} / 보합일 {stats['flat_days']}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"summary": summary, "statistics": stats}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {OUT_PATH.relative_to(BACKEND_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
