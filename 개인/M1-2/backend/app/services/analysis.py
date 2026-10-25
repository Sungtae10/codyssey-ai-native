"""시계열 분석 (순수 함수, 외부 연결 없음).

입력은 [{"date": "YYYY-MM-DD", "value": 숫자, ...}] 목록이다.
- compute_summary: 기간, 개수, 기본 통계, 최근 추세, 월별 요약 → /api/data/summary, 시스템 프롬프트
- compute_statistics: 이동평균, 변동성, 최대 낙폭, 큰 변동일 등 → /api/data/statistics (보너스)
- range_stats / top_records: AI 도구 호출용 (특정 기간 값, 최고·최저 값)

추세 판단 규칙 (설명 가능하게 단순하게 정함)
- 최근 N개(기본 20개, 약 한 달치 고시일)의 평균과 그 직전 N개의 평균을 비교한다.
- 변화율이 +기준(기본 0.5%)보다 크면 "상승", -기준보다 작으면 "하락", 그 사이면 "보합".
- 기준 0.5%의 근거: 이 데이터의 하루 평균 변동폭이 약 6.86원(평균 환율의 약 0.47%)이다.
  한 달 평균이 하루치 변동 정도도 움직이지 않았다면 방향이 있다고 보기 어렵다고 판단했다.
- 보조 지표로 최근 N개에 직선을 맞춘 기울기(한 칸당 변화량)를 같이 준다.
"""
from __future__ import annotations

import math
from collections import OrderedDict
from datetime import datetime, timezone
from statistics import mean, median, quantiles, stdev
from typing import Any, Iterable

TRADING_DAYS_PER_YEAR = 252


def _r(value: float, digits: int = 2) -> float:
    return round(float(value), digits) + 0.0  # + 0.0: -0.0을 0.0으로 바꿔 "-0.00%" 표시를 막는다


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sort_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=lambda r: r["date"])


def _pct(new: float, base: float) -> float | None:
    if base == 0:
        return None
    return (new / base - 1.0) * 100.0


def _slope(values: list[float]) -> float:
    """최소제곱 직선의 기울기 (x = 0, 1, 2, ...)."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = mean(values)
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def monthly_stats(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: "OrderedDict[str, list[float]]" = OrderedDict()
    for rec in sort_records(records):
        groups.setdefault(rec["date"][:7], []).append(float(rec["value"]))
    out: list[dict[str, Any]] = []
    prev_last: float | None = None
    for month, vals in groups.items():
        change = _pct(vals[-1], prev_last) if prev_last is not None else None
        out.append(
            {
                "month": month,
                "count": len(vals),
                "average": _r(mean(vals)),
                "min": _r(min(vals)),
                "max": _r(max(vals)),
                "first": _r(vals[0]),
                "last": _r(vals[-1]),
                "change_pct": _r(change) if change is not None else None,
            }
        )
        prev_last = vals[-1]
    return out


def compute_trend(values: list[float], window: int, threshold_pct: float) -> dict[str, Any] | None:
    n = len(values)
    if n < 6:
        return None
    w = max(3, min(window, n // 2))
    recent = values[-w:]
    previous = values[-2 * w : -w]
    recent_avg = mean(recent)
    previous_avg = mean(previous)
    change = _pct(recent_avg, previous_avg) or 0.0
    if change > threshold_pct:
        direction = "상승"
    elif change < -threshold_pct:
        direction = "하락"
    else:
        direction = "보합"
    return {
        "direction": direction,
        "window": w,
        "recent_average": _r(recent_avg),
        "previous_average": _r(previous_avg),
        "change_pct": _r(change),
        "slope_per_point": _r(_slope(recent)),
        "threshold_pct": _r(threshold_pct),
    }


def trend_text(trend: dict[str, Any] | None, unit: str) -> str:
    if trend is None:
        return "판단 불가 (데이터가 6개 미만)"
    return (
        f"{trend['direction']} (최근 {trend['window']}개 평균 {trend['recent_average']:,.2f}{unit}, "
        f"직전 {trend['window']}개 평균 대비 {trend['change_pct']:+.2f}%)"
    )


def compute_summary(
    records: list[dict[str, Any]],
    dataset: dict[str, str],
    trend_window: int = 20,
    threshold_pct: float = 0.5,
    recent_count: int = 10,
) -> dict[str, Any]:
    recs = sort_records(records)
    unit = dataset.get("unit", "")
    if not recs:
        return {
            "dataset": dataset,
            "period": "데이터 없음",
            "start_date": None,
            "end_date": None,
            "count": 0,
            "metrics": None,
            "trend": "데이터 없음",
            "trend_detail": None,
            "monthly": [],
            "recent": [],
            "generated_at": now_iso(),
        }

    values = [float(r["value"]) for r in recs]
    max_i = max(range(len(values)), key=lambda i: values[i])
    min_i = min(range(len(values)), key=lambda i: values[i])
    change = values[-1] - values[0]
    change_pct = _pct(values[-1], values[0])
    trend = compute_trend(values, trend_window, threshold_pct)
    return {
        "dataset": dataset,
        "period": f"{recs[0]['date']} ~ {recs[-1]['date']}",
        "start_date": recs[0]["date"],
        "end_date": recs[-1]["date"],
        "count": len(recs),
        "metrics": {
            "average": _r(mean(values)),
            "max": _r(values[max_i]),
            "max_date": recs[max_i]["date"],
            "min": _r(values[min_i]),
            "min_date": recs[min_i]["date"],
            "latest": _r(values[-1]),
            "latest_date": recs[-1]["date"],
            "first": _r(values[0]),
            "first_date": recs[0]["date"],
            "change": _r(change),
            "change_pct": _r(change_pct) if change_pct is not None else 0.0,
            "std": _r(stdev(values)) if len(values) > 1 else 0.0,
        },
        "trend": trend_text(trend, unit),
        "trend_detail": trend,
        "monthly": monthly_stats(recs),
        "recent": [{"date": r["date"], "value": _r(r["value"])} for r in recs[-recent_count:]],
        "generated_at": now_iso(),
    }


def _daily_moves(recs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    moves = []
    for prev, cur in zip(recs, recs[1:]):
        base = float(prev["value"])
        val = float(cur["value"])
        pct = _pct(val, base)
        if pct is None:
            continue
        moves.append({"date": cur["date"], "value": _r(val), "change": _r(val - base), "change_pct": _r(pct, 3)})
    return moves


def _extreme_run(recs: list[dict[str, Any]], fall: bool) -> dict[str, Any] | None:
    """fall=True: 고점(start) 대비 이후 저점(end)까지 최대 하락률.
    fall=False: 저점(start) 대비 이후 고점(end)까지 최대 상승률."""
    if len(recs) < 2:
        return None
    best = 0.0
    best_pair: tuple[int, int] | None = None
    anchor = 0
    for i in range(1, len(recs)):
        v = float(recs[i]["value"])
        a = float(recs[anchor]["value"])
        if (fall and v > a) or (not fall and v < a):
            anchor = i
            continue
        pct = _pct(v, a)
        if pct is None:
            continue
        if (fall and pct < best) or (not fall and pct > best):
            best = pct
            best_pair = (anchor, i)
    if best_pair is None:
        return None
    a, b = best_pair
    return {
        "pct": _r(best),
        "start_date": recs[a]["date"],
        "start_value": _r(recs[a]["value"]),
        "end_date": recs[b]["date"],
        "end_value": _r(recs[b]["value"]),
    }


def compute_statistics(records: list[dict[str, Any]], top_n: int = 5) -> dict[str, Any]:
    recs = sort_records(records)
    values = [float(r["value"]) for r in recs]
    n = len(values)
    period = f"{recs[0]['date']} ~ {recs[-1]['date']}" if recs else "데이터 없음"

    def ma(k: int) -> float | None:
        return _r(mean(values[-k:])) if n >= k else None

    moves = _daily_moves(recs)
    pcts = [m["change_pct"] for m in moves]
    daily_std = stdev(pcts) if len(pcts) > 1 else None
    ma20 = ma(20)
    latest_vs_ma20 = _pct(values[-1], ma20) if (ma20 not in (None, 0) and n) else None

    if n >= 2:
        q1, _, q3 = quantiles(values, n=4, method="inclusive")
        quart = {"p25": _r(q1), "median": _r(median(values)), "p75": _r(q3)}
    elif n == 1:
        quart = {"p25": _r(values[0]), "median": _r(values[0]), "p75": _r(values[0])}
    else:
        quart = {"p25": None, "median": None, "p75": None}

    return {
        "count": n,
        "period": period,
        "moving_averages": {"ma5": ma(5), "ma20": ma20, "ma60": ma(60)},
        "latest_vs_ma20_pct": _r(latest_vs_ma20) if latest_vs_ma20 is not None else None,
        "volatility": {
            "daily_std_pct": _r(daily_std, 3) if daily_std is not None else None,
            "annualized_pct": _r(daily_std * math.sqrt(TRADING_DAYS_PER_YEAR)) if daily_std is not None else None,
            "avg_abs_change": _r(mean(abs(m["change"]) for m in moves)) if moves else None,
        },
        "max_drawdown": _extreme_run(recs, fall=True),
        "max_rally": _extreme_run(recs, fall=False),
        "quartiles": quart,
        "top_rises": [m for m in sorted(moves, key=lambda m: m["change_pct"], reverse=True) if m["change_pct"] > 0][:top_n],
        "top_falls": [m for m in sorted(moves, key=lambda m: m["change_pct"]) if m["change_pct"] < 0][:top_n],
        "up_days": sum(1 for m in moves if m["change"] > 0),
        "down_days": sum(1 for m in moves if m["change"] < 0),
        "flat_days": sum(1 for m in moves if m["change"] == 0),
        "monthly": monthly_stats(recs),
        "generated_at": now_iso(),
    }


def range_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    """특정 기간 레코드의 요약 (AI 도구 get_data_by_range가 씀)."""
    recs = sort_records(records)
    if not recs:
        return {"count": 0}
    values = [float(r["value"]) for r in recs]
    max_i = max(range(len(values)), key=lambda i: values[i])
    min_i = min(range(len(values)), key=lambda i: values[i])
    change_pct = _pct(values[-1], values[0])
    return {
        "count": len(recs),
        "first_date": recs[0]["date"],
        "last_date": recs[-1]["date"],
        "average": _r(mean(values)),
        "max": _r(values[max_i]),
        "max_date": recs[max_i]["date"],
        "min": _r(values[min_i]),
        "min_date": recs[min_i]["date"],
        "first": _r(values[0]),
        "last": _r(values[-1]),
        "change": _r(values[-1] - values[0]),
        "change_pct": _r(change_pct) if change_pct is not None else None,
    }


def top_records(records: list[dict[str, Any]], order: str = "desc", limit: int = 5) -> list[dict[str, Any]]:
    """값이 가장 큰(desc) 또는 작은(asc) 레코드 limit개. 같은 값이면 이른 날짜 먼저."""
    reverse = order != "asc"
    ranked = sorted(records, key=lambda r: (-float(r["value"]) if reverse else float(r["value"]), r["date"]))
    return [{"date": r["date"], "value": _r(r["value"]), "memo": r.get("memo", "")} for r in ranked[:limit]]
