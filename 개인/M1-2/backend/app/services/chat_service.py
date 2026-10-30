"""AI 채팅 서비스: 컨텍스트 주입 + 도구 호출 + 자동 저장.

POST /api/chat 한 번의 흐름
  ① 데이터 요약 조회   DataService.summary()  (GET /api/data/summary와 같은 함수)
  ② 시스템 프롬프트에 요약 삽입   build_system_prompt()
  ③ GPT 호출   필요하면 GPT가 도구를 부르고, 서버가 실행해 결과를 돌려준 뒤 다시 GPT 호출 (최대 N회)
  ④ 질문과 답을 conversations 컬렉션에 저장 (conversation_id가 없으면 새 대화 생성)
"""
from __future__ import annotations

import json
import time
from typing import Any

from ..config import Settings
from ..database import utc_now_iso
from ..errors import AIServiceError
from ..schemas.chat import ChatRequest
from .ai_client import LLMClient
from .conversation_service import ConversationService
from .data_service import DataService
from .prompt import build_system_prompt
from .tools import ToolError, ToolExecutor

MAX_CALLS_PER_ROUND = 6
MAX_TOOL_RESULT_CHARS = 12000


class ChatService:
    def __init__(
        self,
        data: DataService,
        conversations: ConversationService,
        llm: LLMClient,
        tools: ToolExecutor,
        settings: Settings,
    ) -> None:
        self._data = data
        self._conversations = conversations
        self._llm = llm
        self._tools = tools
        self._settings = settings

    def chat(self, request: ChatRequest) -> dict[str, Any]:
        history: list[dict[str, str]] = []
        if request.conversation_id:
            conv = self._conversations.get(request.conversation_id)  # 없으면 404
            self._conversations.ensure_room(conv)  # 너무 긴 대화면 OpenAI를 부르기 전에 멈춤 (413)
            past = [m for m in conv["messages"] if m.get("role") in ("user", "assistant") and m.get("content")]
            if self._settings.history_messages > 0:
                history = [{"role": m["role"], "content": m["content"]} for m in past[-self._settings.history_messages :]]

        summary = self._data.summary()  # ① 요약 조회
        system_prompt = build_system_prompt(summary, tools_enabled=self._settings.enable_tools)  # ② 주입
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": request.message},
        ]
        reply, model, tool_logs, usage = self._run(messages)  # ③ GPT 호출

        now = utc_now_iso()
        user_message = {"role": "user", "content": request.message, "created_at": now}
        assistant_message = {
            "role": "assistant",
            "content": reply,
            "created_at": now,
            "model": model,
            "tool_calls": tool_logs,
        }
        conv = self._conversations.save_chat_turn(request.conversation_id, user_message, assistant_message)  # ④ 저장

        metrics = summary.get("metrics") or {}
        return {
            "conversation_id": conv["id"],
            "conversation_title": conv["title"],
            "reply": reply,
            "model": model,
            "tool_calls": tool_logs,
            "summary_used": {
                "period": summary["period"],
                "count": summary["count"],
                "trend": summary["trend"],
                "average": metrics.get("average"),
                "max": metrics.get("max"),
                "min": metrics.get("min"),
                "latest": metrics.get("latest"),
            },
            "usage": usage or None,
            "created_at": now,
        }

    def _run(self, messages: list[dict[str, Any]]) -> tuple[str, str, list[dict[str, Any]], dict[str, int]]:
        tools = self._tools.specs() if self._settings.enable_tools else None
        max_rounds = self._settings.max_tool_rounds
        logs: list[dict[str, Any]] = []
        usage: dict[str, int] = {}
        model: str | None = None
        # 한 질문 전체 시간 상한. 화면은 150초까지 기다리므로(잠든 서버 깨우기 포함) 그보다 짧게 끝낸다.
        deadline = time.monotonic() + self._settings.chat_deadline_seconds

        for round_no in range(max_rounds + 1):
            last_round = round_no == max_rounds
            if tools:
                result = self._llm.complete(
                    messages, tools=tools, tool_choice="none" if last_round else "auto", model=model, deadline=deadline
                )
            else:
                result = self._llm.complete(messages, model=model, deadline=deadline)
            model = result.model  # 같은 질문 안에서는 처음 답한 모델을 계속 쓴다
            for key, value in result.usage.items():
                usage[key] = usage.get(key, 0) + value

            if tools and result.tool_calls and not last_round:
                messages.append(result.assistant_message())
                for index, call in enumerate(result.tool_calls):
                    messages.append(self._run_tool(call, logs, skip=index >= MAX_CALLS_PER_ROUND))
                continue

            reply = (result.content or "").strip()
            if not reply:
                hint = " (답변 길이 제한에 걸림: OPENAI_MAX_TOKENS를 늘리세요)" if result.finish_reason == "length" else ""
                raise AIServiceError("AI 답변이 비어 있습니다" + hint + ".", 502)
            return reply, model, logs, usage

        raise AIServiceError("AI 답변을 만들지 못했습니다.", 502)  # 도달하지 않음 (마지막 회차는 도구 금지)

    def _run_tool(self, call: dict[str, Any], logs: list[dict[str, Any]], skip: bool) -> dict[str, Any]:
        reason = None
        args: dict[str, Any] = {}
        if skip:
            output: dict[str, Any] = {"error": "한 번에 부를 수 있는 도구 수를 넘었습니다."}
        else:
            try:
                args = self._tools.parse_arguments(call.get("arguments"))
                reason = args.get("reason")
                output = self._tools.execute(call["name"], args)
            except ToolError as exc:
                output = {"error": str(exc)}
        logs.append(
            {
                "name": call["name"],
                "arguments": {k: v for k, v in args.items() if k != "reason"},
                "reason": str(reason)[:200] if reason else None,
                "ok": "error" not in output,
            }
        )
        content = json.dumps(output, ensure_ascii=False, default=str)
        if len(content) > MAX_TOOL_RESULT_CHARS:
            content = content[:MAX_TOOL_RESULT_CHARS] + '..."(잘림)"'
        return {"role": "tool", "tool_call_id": call["id"], "content": content}
