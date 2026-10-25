"""분석 함수 단위 테스트: 손으로 계산할 수 있는 작은 데이터로 확인한다."""
from __future__ import annotations

import csv
from statistics import mean, stdev

from app.services import analysis
from conftest import CSV_PATH

DATASET = {"name": "테스트", "unit": "원", "source": "테스트"}


def recs(values, start_month="2026-01"):
    return [{"date": f"{start_month}-{i + 1:02d}", "value": v} for i, v in enumerate(values)]


def test_summary_basic_numbers():
    data = recs([10, 20, 30, 40])
    s = analysis.compute_summary(data, DATASET, trend_window=20, threshold_pct=0.5)
    m = s["metrics"]
    assert s["count"] == 4 and s["period"] == "2026-01-01 ~ 2026-01-04"
    assert m["average"] == 25.0 and m["max"] == 40 and m["max_date"] == "2026-01-04"
    assert m["min"] == 10 and m["min_date"] == "2026-01-01"
    assert m["change"] == 30 and m["change_pct"] == 300.0
    assert s["trend_detail"] is None and s["trend"].startswith("판단 불가")  # 6개 미만


def test_trend_up_down_flat():
    up = analysis.compute_trend([100] * 5 + [110] * 5, window=5, threshold_pct=0.5)
    assert up["direction"] == "상승" and up["change_pct"] == 10.0 and up["window"] == 5
    down = analysis.compute_trend([110] * 5 + [100] * 5, window=5, threshold_pct=0.5)
    assert down["direction"] == "하락"
    flat = analysis.compute_trend([100] * 5 + [100.4] * 5, window=5, threshold_pct=0.5)
    assert flat["direction"] == "보합"  # +0.4%는 기준 0.5% 안쪽


def test_trend_window_shrinks_for_short_series():
    t = analysis.compute_trend(list(range(1, 13)), window=20, threshold_pct=0.5)
    assert t["window"] == 6  # 12개면 6 vs 6


def test_monthly_stats_and_negative_zero():
    data = [
        {"date": "2026-01-30", "value": 100.0},
        {"date": "2026-01-31", "value": 100.0},
        {"date": "2026-02-02", "value": 99.999},
    ]
    rows = analysis.monthly_stats(data)
    assert [r["month"] for r in rows] == ["2026-01", "2026-02"]
    assert rows[0]["change_pct"] is None
    assert rows[1]["change_pct"] == 0.0 and str(rows[1]["change_pct"]) == "0.0"  # -0.0이 아님


def test_drawdown_and_rally():
    data = recs([100, 120, 90, 95, 130, 117])
    st = analysis.compute_statistics(data)
    dd = st["max_drawdown"]
    assert dd["start_value"] == 120 and dd["end_value"] == 90 and dd["pct"] == -25.0
    up = st["max_rally"]
    assert up["start_value"] == 90 and up["end_value"] == 130 and round(up["pct"], 2) == 44.44
    assert st["up_days"] == 3 and st["down_days"] == 2 and st["flat_days"] == 0
    assert st["top_rises"][0]["date"] == "2026-01-05"  # 95 → 130 (+36.8%)
    assert st["top_falls"][0]["date"] == "2026-01-03"  # 120 → 90 (-25%)


def test_top_records_order_and_ties():
    data = recs([5, 9, 9, 1])
    top = analysis.top_records(data, "desc", 2)
    assert [(r["date"], r["value"]) for r in top] == [("2026-01-02", 9), ("2026-01-03", 9)]
    low = analysis.top_records(data, "asc", 1)
    assert low[0]["value"] == 1


def test_empty_summary_and_statistics():
    s = analysis.compute_summary([], DATASET)
    assert s["count"] == 0 and s["metrics"] is None and s["monthly"] == []
    st = analysis.compute_statistics([])
    assert st["count"] == 0 and st["max_drawdown"] is None


def test_real_csv_matches_independent_calculation():
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = [{"date": r["date"], "value": float(r["value"])} for r in csv.DictReader(f)]
    s = analysis.compute_summary(rows, DATASET, 20, 0.5)
    values = [r["value"] for r in rows]
    assert s["count"] == 251 == len(values)
    assert s["metrics"]["average"] == round(mean(values), 2)
    assert s["metrics"]["std"] == round(stdev(values), 2)
    assert s["metrics"]["max"] == max(values) and s["metrics"]["min"] == min(values)
    recent, prev = values[-20:], values[-40:-20]
    assert s["trend_detail"]["change_pct"] == round((mean(recent) / mean(prev) - 1) * 100, 2)
    assert sum(m["count"] for m in s["monthly"]) == 251
