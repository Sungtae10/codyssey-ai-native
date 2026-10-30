"""OpenAI SDK 경로 테스트: 실제 openai 라이브러리로 요청을 만들고, HTTP만 가짜로 바꿔 확인한다.

확인하는 것
- 기본 모델 gpt-6-luna에 reasoning_effort="none", max_completion_tokens를 보낸다 (temperature는 안 보냄)
- 기본 모델이 404(권한·모델 없음)면 gpt-4o-mini로 바꾸고, 대체 모델에는 reasoning_effort를 보내지 않는다
- 선택 매개변수를 거부(400 unsupported)하면 빼고 다시 보낸다
- 401, 429 등은 알아보기 쉬운 한국어 오류로 바꾼다
"""
from __future__ import annotations

import json

import httpx
import openai
import pytest

from app.errors import AIServiceError, RateLimitedError
from app.services.ai_client import LLMClient
from app.services.tools import TOOL_SPECS
from conftest import make_settings


def ok_body(model: str, content: str = "답", tool_calls=None):
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message = {"role": "assistant", "content": None, "tool_calls": tool_calls}
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1761379200,
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if tool_calls else "stop"}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 7, "total_tokens": 57},
    }


def make_client(handler, **settings_overrides) -> tuple[LLMClient, list[dict]]:
    seen: list[dict] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        return handler(body)

    llm = LLMClient(make_settings(**settings_overrides))
    llm._client = openai.OpenAI(
        api_key="test-key",
        base_url="http://fake-openai.local/v1",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(wrapped)),
    )
    return llm, seen


def test_primary_request_shape_and_tool_parsing():
    calls = [{"id": "call_9", "type": "function", "function": {"name": "get_statistics", "arguments": '{"reason":"r"}'}}]
    llm, seen = make_client(lambda body: httpx.Response(200, json=ok_body(body["model"], tool_calls=calls)))
    result = llm.complete([{"role": "user", "content": "q"}], tools=TOOL_SPECS)
    body = seen[0]
    assert body["model"] == "gpt-6-luna" and body["reasoning_effort"] == "none"
    assert body["max_completion_tokens"] == 700 and "temperature" not in body and "max_tokens" not in body
    assert body["tool_choice"] == "auto" and len(body["tools"]) == 6
    assert result.model == "gpt-6-luna" and result.tool_calls == [
        {"id": "call_9", "name": "get_statistics", "arguments": '{"reason":"r"}'}
    ]
    assert result.usage == {"prompt_tokens": 50, "completion_tokens": 7, "total_tokens": 57}
    assert result.assistant_message()["tool_calls"][0]["function"]["name"] == "get_statistics"


def test_fallback_when_primary_model_unavailable():
    def handler(body):
        if body["model"] == "gpt-6-luna":
            return httpx.Response(404, json={"error": {"message": "The model `gpt-6-luna` does not exist", "code": "model_not_found"}})
        return httpx.Response(200, json=ok_body(body["model"], "대체 모델 답"))

    llm, seen = make_client(handler)
    result = llm.complete([{"role": "user", "content": "q"}])
    assert [b["model"] for b in seen] == ["gpt-6-luna", "gpt-4o-mini"]
    assert "reasoning_effort" not in seen[1]
    assert result.model == "gpt-4o-mini" and result.content == "대체 모델 답"
    llm.complete([{"role": "user", "content": "q2"}])  # 10분 동안은 기본 모델을 건너뜀
    assert [b["model"] for b in seen] == ["gpt-6-luna", "gpt-4o-mini", "gpt-4o-mini"]


def test_retry_without_optional_params_on_unsupported():
    def handler(body):
        if "reasoning_effort" in body:
            return httpx.Response(400, json={"error": {"message": "Unsupported parameter: 'reasoning_effort'"}})
        return httpx.Response(200, json=ok_body(body["model"]))

    llm, seen = make_client(handler, openai_temperature=0.2)
    result = llm.complete([{"role": "user", "content": "q"}])
    assert len(seen) == 2 and seen[1]["model"] == "gpt-6-luna" and "reasoning_effort" not in seen[1]
    assert "temperature" in seen[0] and "temperature" not in seen[1]
    assert result.model == "gpt-6-luna"


def test_fallback_model_never_gets_reasoning_effort_even_if_primary_is_classic():
    llm, seen = make_client(lambda body: httpx.Response(200, json=ok_body(body["model"])), openai_model="gpt-4o-mini")
    llm.complete([{"role": "user", "content": "q"}])
    assert seen[0]["model"] == "gpt-4o-mini" and "reasoning_effort" not in seen[0]


@pytest.mark.parametrize(
    "status,exc_type,needle",
    [(401, AIServiceError, "OPENAI_API_KEY"), (429, RateLimitedError, "사용 한도"), (500, AIServiceError, "HTTP 500")],
)
def test_error_mapping(status, exc_type, needle):
    llm, _ = make_client(lambda body: httpx.Response(status, json={"error": {"message": "x"}}), openai_fallback_model=None)
    with pytest.raises(exc_type) as info:
        llm.complete([{"role": "user", "content": "q"}])
    assert needle in info.value.message


def test_sticky_model_parameter():
    llm, seen = make_client(lambda body: httpx.Response(200, json=ok_body(body["model"])))
    llm.complete([{"role": "user", "content": "q"}], model="gpt-4o-mini")
    assert [b["model"] for b in seen] == ["gpt-4o-mini"]
