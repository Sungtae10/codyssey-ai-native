"""시스템 프롬프트 만들기 (컨텍스트 주입).

원리: GPT는 사용자의 데이터를 모른다. 그래서 매 질문마다
  ① /api/data/summary와 같은 요약을 계산하고
  ② 그 요약을 글로 바꿔 시스템 프롬프트의 [사용자 데이터 요약] 칸에 끼워 넣은 뒤
  ③ 질문과 함께 보낸다.
그러면 GPT는 "내 데이터"를 근거로 답한다. 요약에 없는 세부 값은 도구(function calling)로 더 읽는다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

KST = timezone(timedelta(hours=9))
MAX_MONTHS = 13


def _fmt(value: float | None, unit: str) -> str:
    if value is None:
        return "-"
    return f"{value:,.2f}{unit}"


def summary_to_text(summary: dict[str, Any]) -> str:
    ds = summary["dataset"]
    unit = ds.get("unit", "")
    m = summary.get("metrics")
    lines = [
        f"- 데이터: {ds['name']} (단위: {unit}, 출처: {ds['source']})",
        f"- 데이터 기간: {summary['period']}",
        f"- 총 레코드: {summary['count']}개",
    ]
    if m:
        lines.append(
            "- 주요 지표: "
            f"평균 {_fmt(m['average'], unit)}, 최고 {_fmt(m['max'], unit)} ({m['max_date']}), "
            f"최저 {_fmt(m['min'], unit)} ({m['min_date']}), 최신 {_fmt(m['latest'], unit)} ({m['latest_date']}), "
            f"기간 첫 값 대비 {m['change']:+,.2f}{unit} ({m['change_pct']:+.2f}%), 표준편차 {m['std']:,.2f}{unit}"
        )
    lines.append(f"- 최근 트렌드: {summary['trend']}")
    if summary.get("monthly"):
        months = summary["monthly"][-MAX_MONTHS:]  # 데이터가 늘어도 프롬프트 길이가 무한히 커지지 않게
        monthly = ", ".join(
            f"{row['month']} 평균 {row['average']:,.2f} (최저 {row['min']:,.2f}, 최고 {row['max']:,.2f}, {row['count']}개)"
            for row in months
        )
        note = f" (최근 {MAX_MONTHS}개월만 표시)" if len(summary["monthly"]) > MAX_MONTHS else ""
        lines.append(f"- 월별{note}: {monthly}")
    if summary.get("recent"):
        recent = ", ".join(f"{p['date']} {p['value']:,.2f}" for p in summary["recent"])
        lines.append(f"- 최근 값: {recent}")
    return "\n".join(lines)


def build_system_prompt(summary: dict[str, Any], tools_enabled: bool, now: datetime | None = None) -> str:
    today = (now or datetime.now(KST)).astimezone(KST).date().isoformat()
    end_date = summary.get("end_date") or "없음"
    tool_rule = (
        "2. 요약에 없는 구체적인 값이 필요하면 추측하지 말고 도구를 부르세요. 특정 날짜·기간은 get_data_by_range, "
        "가장 높거나 낮은 날은 get_top_records, 이동평균·변동성·가장 크게 움직인 날·월별 변화는 get_statistics, "
        "이전 대화는 list_conversations와 get_conversation. 요약만으로 답할 수 있으면 도구를 부르지 마세요."
        if tools_enabled
        else "2. 요약에 없는 값은 모른다고 말하고, 데이터 관리 화면에서 확인하도록 안내하세요."
    )
    return f"""당신은 사용자가 저장한 데이터를 함께 보는 데이터 분석 비서입니다.

[사용자 데이터 요약]
{summary_to_text(summary)}

위 데이터를 기반으로 맞춤형 답변을 제공하세요.

[답변 규칙]
1. 숫자는 위 요약과 도구 결과에 있는 값만 쓰고, 날짜와 단위를 함께 적으세요. 없는 값을 지어내지 마세요.
{tool_rule}
3. 오늘은 {today}이고, 데이터의 마지막 날짜는 {end_date}입니다. '이번 달', '최근' 같은 말은 데이터의 마지막 날짜 기준으로 풀고, 어느 날짜까지의 값인지 밝히세요.
4. 값이 왜 움직였는지는 이 데이터만으로 확인할 수 없습니다. 원인을 물으면 데이터로 확인되는 사실과 일반적인 가능성을 나눠 말하고 단정하지 마세요.
5. 환전·투자 시점을 권하거나 앞으로의 값을 단정해 예측하지 마세요.
6. 한국어로, 핵심부터 3~6문장으로 간결하게 답하세요."""
