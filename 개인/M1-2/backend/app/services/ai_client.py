"""OpenAI GPT 호출 래퍼 (Chat Completions API).

모델 선택 (2026-10 OpenAI 공식 문서 기준)
- 기본 gpt-6-luna: 가장 저렴한 GPT-6 모델(100만 토큰당 입력 $0.10, 출력 $0.50).
  Chat Completions에서 도구 호출(function calling)은 reasoning_effort="none"일 때만 지원되므로
  기본값을 none으로 둔다. 이렇게 하면 추론 토큰이 생기지 않아 max_completion_tokens 전부가 답변에 쓰인다.
- 대체 gpt-4o-mini: 기본 모델을 쓸 수 없을 때(권한 없음, 모델 없음, 요청 형식 오류) 한 번 바꿔 다시 부른다.
  어떤 모델이 실제로 답했는지는 응답의 model 필드와 대화 기록에 남긴다.

비용 보호: 답변 길이는 OPENAI_MAX_TOKENS(기본 700)로 제한한다.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import openai

from ..config import Settings
from ..errors import AIServiceError, RateLimitedError

logger = logging.getLogger(__name__)

_PRIMARY_COOLDOWN_SECONDS = 600
_REASONING_PREFIXES = ("gpt-6", "gpt-5", "o1", "o3", "o4")


def supports_reasoning_effort(model: str) -> bool:
    return model.startswith(_REASONING_PREFIXES)


@dataclass
class LLMResult:
    content: str | None
    tool_calls: list[dict[str, Any]]
    model: str
    finish_reason: str | None
    usage: dict[str, int] = field(default_factory=dict)

    def assistant_message(self) -> dict[str, Any]:
        """도구 호출 루프에서 대화 내역에 다시 넣을 assistant 메시지."""
        msg: dict[str, Any] = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = [
                {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                for tc in self.tool_calls
            ]
        return msg


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: openai.OpenAI | None = None
        self._primary_blocked_until = 0.0
        self._lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return self._settings.openai_configured

    def _get_client(self) -> openai.OpenAI:
        if not self._settings.openai_api_key:
            raise AIServiceError("OPENAI_API_KEY 환경 변수가 없습니다. 서버 설정에 키를 넣어 주세요.", 503)
        if self._client is None:
            kwargs: dict[str, Any] = {
                "api_key": self._settings.openai_api_key,
                "timeout": float(self._settings.openai_timeout_seconds),
                # 재시도는 하지 않는다: 한 질문 전체 시간 상한(CHAT_DEADLINE_SECONDS)을 지키고,
                # 기본 모델이 안 되면 대체 모델로 바꾸는 것으로 대응한다.
                "max_retries": 0,
            }
            if self._settings.openai_base_url:
                kwargs["base_url"] = self._settings.openai_base_url
            self._client = openai.OpenAI(**kwargs)
        return self._client

    def _models(self) -> list[str]:
        primary = self._settings.openai_model
        fallback = self._settings.openai_fallback_model
        models = [primary]
        if fallback and fallback != primary:
            models.append(fallback)
            with self._lock:
                if time.monotonic() < self._primary_blocked_until:
                    models = [fallback]
        return models

    def _params(self, model: str, messages, tools, tool_choice, minimal: bool) -> dict[str, Any]:
        s = self._settings
        params: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": s.openai_max_tokens,
        }
        effort = s.openai_reasoning_effort
        if not minimal and effort and supports_reasoning_effort(model):
            params["reasoning_effort"] = effort
        # temperature는 추론이 켜진 모델에서 거부될 수 있어, 설정했을 때만 보낸다.
        reasoning_on = "reasoning_effort" in params and params["reasoning_effort"] != "none"
        if not minimal and s.openai_temperature is not None and not reasoning_on:
            params["temperature"] = s.openai_temperature
        if tools:
            params["tools"] = tools
            params["tool_choice"] = tool_choice
        return params

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        model: str | None = None,
        deadline: float | None = None,
    ) -> LLMResult:
        """model을 주면 그 모델만 쓴다 (한 질문 안에서 도구 호출을 이어 갈 때 같은 모델 유지).
        deadline(time.monotonic 기준)을 주면 그 시각까지 남은 시간만큼만 기다린다."""
        client = self._get_client()
        models = [model] if model else self._models()
        last_error: Exception | None = None
        for index, model in enumerate(models):
            is_last = index == len(models) - 1
            block_primary = False
            for minimal in (False, True):
                params = self._params(model, messages, tools, tool_choice, minimal)
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining < 3:
                        raise AIServiceError("AI 답변 시간이 초과되었습니다. 질문을 조금 짧게 해서 다시 보내 주세요.", 504)
                    params["timeout"] = min(float(self._settings.openai_timeout_seconds), remaining)
                try:
                    resp = client.chat.completions.create(**params)
                    return self._to_result(resp, model)
                except openai.BadRequestError as exc:
                    last_error = exc
                    text = str(exc).lower()
                    # 선택 매개변수(reasoning_effort, temperature)를 모델이 거부하면 빼고 한 번 더
                    if not minimal and ("unsupported" in text or "unrecognized" in text or "not supported" in text):
                        logger.warning("%s: 선택 매개변수를 빼고 다시 시도 (%s)", model, exc.__class__.__name__)
                        continue
                    if not is_last:
                        break
                    raise AIServiceError(f"OpenAI 요청 형식 오류 ({model}): {self._short(exc)}", 502) from exc
                except (openai.NotFoundError, openai.PermissionDeniedError) as exc:
                    last_error = exc
                    if not is_last:
                        block_primary = True  # 모델 권한 문제는 10분 동안 바로 대체 모델을 쓴다
                        break
                    raise AIServiceError(
                        f"모델 {model}을(를) 쓸 수 없습니다. OPENAI_MODEL 값과 계정 권한을 확인하세요.", 502
                    ) from exc
                except openai.AuthenticationError as exc:
                    raise AIServiceError("OpenAI API 키가 올바르지 않습니다. OPENAI_API_KEY를 확인하세요.", 502) from exc
                except openai.RateLimitError as exc:
                    raise RateLimitedError(
                        "OpenAI 사용 한도에 걸렸습니다 (요청이 많거나 크레딧 부족). 잠시 뒤 다시 시도하세요.", 429
                    ) from exc
                except openai.APITimeoutError as exc:
                    raise AIServiceError("AI 응답 시간이 초과되었습니다. 다시 시도하세요.", 504) from exc
                except openai.APIConnectionError as exc:
                    raise AIServiceError("OpenAI 서버에 연결하지 못했습니다.", 502) from exc
                except openai.APIStatusError as exc:
                    raise AIServiceError(f"OpenAI 오류 (HTTP {exc.status_code})", 502) from exc
            # 여기까지 오면 이 모델은 실패. 다음(대체) 모델로 넘어간다.
            logger.warning("모델 %s 실패 → 대체 모델로 전환 (%s)", model, type(last_error).__name__)
            if block_primary and model == self._settings.openai_model:
                with self._lock:
                    self._primary_blocked_until = time.monotonic() + _PRIMARY_COOLDOWN_SECONDS
        raise AIServiceError("AI 응답을 받지 못했습니다.", 502)

    @staticmethod
    def _short(exc: Exception, limit: int = 160) -> str:
        text = str(exc).replace("\n", " ")
        return text if len(text) <= limit else text[:limit] + "..."

    @staticmethod
    def _to_result(resp: Any, model: str) -> LLMResult:
        choice = resp.choices[0]
        msg = choice.message
        calls = []
        for tc in msg.tool_calls or []:
            fn = getattr(tc, "function", None)
            if fn is None:
                continue
            calls.append({"id": tc.id, "name": fn.name, "arguments": fn.arguments or "{}"})
        usage = {}
        if getattr(resp, "usage", None) is not None:
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = getattr(resp.usage, key, None)
                if isinstance(value, int):
                    usage[key] = value
        return LLMResult(
            content=msg.content,
            tool_calls=calls,
            model=model,
            finish_reason=choice.finish_reason,
            usage=usage,
        )
