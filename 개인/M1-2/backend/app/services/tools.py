"""AI 도구 (Function Calling, 보너스).

같은 도구 목록을 두 곳에서 쓴다.
1) /api/chat: GPT가 스스로 필요하다고 판단하면 도구를 부른다 (function calling).
2) /api/tools/{name}: 외부 클라이언트(MCP 서버)가 같은 도구를 HTTP로 부른다.

모든 도구에는 reason 인자가 있다. GPT가 "왜 이 도구를 부르는지"를 한 문장으로 적게 해서,
화면과 대화 기록에 호출 근거로 남긴다. 도구는 모두 읽기 전용이다 (데이터를 바꾸지 않는다).
"""
from __future__ import annotations

import calendar
import json
import re
from datetime import date
from typing import Any

from ..errors import AppError
from .conversation_service import ConversationService
from .data_service import DataService

_REASON = {
    "type": "string",
    "description": "이 도구를 부르는 이유를 한국어 한 문장으로 (예: '10월 값을 날짜별로 확인하려고')",
}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_data_summary",
            "description": "저장된 데이터 전체의 최신 요약(기간, 개수, 평균·최고·최저, 최근 추세, 월별 평균)을 다시 읽는다. "
            "시스템 프롬프트의 요약이 최신인지 확인하거나 대화 중 데이터가 바뀌었을 수 있을 때 쓴다.",
            "parameters": {
                "type": "object",
                "properties": {"reason": _REASON},
                "required": ["reason"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_by_range",
            "description": "특정 기간(시작일~종료일)의 날짜별 값과 그 기간의 평균·최고·최저·변화율을 읽는다. "
            "'10월 첫째 주', '3월 값', '어제' 처럼 요약에 없는 구체적인 날짜나 기간이 필요할 때 쓴다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "시작일 YYYY-MM-DD (또는 YYYY-MM)"},
                    "end_date": {"type": "string", "description": "종료일 YYYY-MM-DD (또는 YYYY-MM)"},
                    "reason": _REASON,
                },
                "required": ["start_date", "end_date", "reason"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_records",
            "description": "값이 가장 높은(desc) 또는 가장 낮은(asc) 날을 순서대로 읽는다. '가장 높았던 날 3개' 같은 질문에 쓴다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order": {"type": "string", "enum": ["desc", "asc"], "description": "desc=높은 순, asc=낮은 순"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10, "description": "개수 (1~10)"},
                    "reason": _REASON,
                },
                "required": ["order", "limit", "reason"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_statistics",
            "description": "확장 통계를 읽는다: 이동평균(5·20·60), 일간 변동성, 고점 대비 최대 하락, 저점 대비 최대 상승, "
            "하루 상승·하락 폭이 가장 컸던 날, 상승일·하락일 수, 월별 통계와 전월 대비 변화율.",
            "parameters": {
                "type": "object",
                "properties": {"reason": _REASON},
                "required": ["reason"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_conversations",
            "description": "최근 대화 목록(제목, 날짜, ID)을 읽는다. 사용자가 '지난번에 물어본 것'처럼 이전 대화를 언급할 때 쓴다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "description": "개수 (1~20)"},
                    "reason": _REASON,
                },
                "required": ["limit", "reason"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_conversation",
            "description": "대화 ID로 이전 대화의 메시지를 읽는다. list_conversations로 ID를 먼저 확인한 뒤 쓴다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "string", "description": "대화 ID"},
                    "reason": _REASON,
                },
                "required": ["conversation_id", "reason"],
                "additionalProperties": False,
            },
        },
    },
]

TOOL_NAMES = [spec["function"]["name"] for spec in TOOL_SPECS]
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class ToolError(ValueError):
    pass


def _parse_day(text: Any, end: bool) -> str:
    if not isinstance(text, str):
        raise ToolError("날짜는 문자열(YYYY-MM-DD)이어야 합니다.")
    text = text.strip()
    try:
        if _MONTH_RE.match(text):
            year, month = int(text[:4]), int(text[5:7])
            day = calendar.monthrange(year, month)[1] if end else 1
            return date(year, month, day).isoformat()
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ToolError(f"날짜 형식이 올바르지 않습니다: {text}") from exc


def _int_arg(args: dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    value = args.get(key, default)
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))


class ToolExecutor:
    def __init__(self, data: DataService, conversations: ConversationService) -> None:
        self._data = data
        self._conversations = conversations

    @staticmethod
    def specs() -> list[dict[str, Any]]:
        return TOOL_SPECS

    @staticmethod
    def parse_arguments(raw: str | dict[str, Any] | None) -> dict[str, Any]:
        if raw is None or raw == "":
            return {}
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ToolError("도구 인자를 JSON으로 읽지 못했습니다.") from exc
        if not isinstance(parsed, dict):
            raise ToolError("도구 인자는 JSON 객체여야 합니다.")
        return parsed

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """도구를 실행한다. 실패하면 예외 대신 {"error": ...}를 돌려줘 GPT가 상황을 알 수 있게 한다."""
        try:
            if name == "get_data_summary":
                return {"summary": self._data.summary()}
            if name == "get_data_by_range":
                start = _parse_day(args.get("start_date"), end=False)
                end = _parse_day(args.get("end_date"), end=True)
                if start > end:
                    start, end = end, start
                return self._data.range_report(start, end)
            if name == "get_top_records":
                order = args.get("order", "desc")
                order = order if order in ("asc", "desc") else "desc"
                limit = _int_arg(args, "limit", 5, 1, 10)
                return {"order": order, "records": self._data.top(order=order, limit=limit)}
            if name == "get_statistics":
                stats = self._data.statistics()
                stats.pop("generated_at", None)
                return stats
            if name == "list_conversations":
                limit = _int_arg(args, "limit", 10, 1, 20)
                items = self._conversations.list(limit=limit)
                return {"conversations": [{k: c[k] for k in ("id", "title", "message_count", "updated_at")} for c in items]}
            if name == "get_conversation":
                conv_id = str(args.get("conversation_id", "")).strip()
                if not _ID_RE.match(conv_id):
                    raise ToolError("conversation_id 형식이 올바르지 않습니다.")
                conv = self._conversations.get(conv_id)
                messages = [
                    {"role": m.get("role"), "content": str(m.get("content", ""))[:600], "created_at": m.get("created_at")}
                    for m in conv["messages"][-20:]
                ]
                return {"id": conv["id"], "title": conv["title"], "messages": messages}
            return {"error": f"알 수 없는 도구입니다: {name}. 사용 가능: {', '.join(TOOL_NAMES)}"}
        except ToolError as exc:
            return {"error": str(exc)}
        except AppError as exc:
            return {"error": exc.message}
