"""테스트 공통 준비: 키 없이 메모리 저장소 + 가짜 LLM으로 실제 앱 코드를 돌린다."""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings  # noqa: E402
from app.factory import create_app  # noqa: E402
from app.services.ai_client import LLMResult  # noqa: E402

CSV_PATH = str(BACKEND_DIR / "data" / "usdkrw_daily.csv")


def make_settings(**overrides: Any) -> Settings:
    base = dict(
        storage_backend="memory",
        memory_seed_csv=CSV_PATH,
        openai_api_key="test-key",
        allowed_origins=["http://localhost:5500", "https://my-app.vercel.app"],
        data_cache_seconds=60,
    )
    base.update(overrides)
    return Settings(**base)


class FakeLLM:
    """OpenAI 대신 정해 둔 응답을 돌려주고, 받은 메시지를 기록한다."""

    def __init__(self, script: list[LLMResult | Callable[..., LLMResult]] | None = None) -> None:
        self.script = list(script or [])
        self.calls: list[dict[str, Any]] = []

    def complete(self, messages, tools=None, tool_choice="auto", model=None, deadline=None):
        self.calls.append(
            {"messages": copy.deepcopy(messages), "tools": tools, "tool_choice": tool_choice, "model": model,
             "deadline": deadline}
        )
        if self.script:
            item = self.script.pop(0)
            return item(messages, tools) if callable(item) else item
        return answer("기본 답변입니다.")


def answer(text: str, model: str = "fake-model") -> LLMResult:
    return LLMResult(
        content=text,
        tool_calls=[],
        model=model,
        finish_reason="stop",
        usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    )


def tool_call(name: str, arguments: str, call_id: str = "call_1", model: str = "fake-model") -> LLMResult:
    return LLMResult(
        content=None,
        tool_calls=[{"id": call_id, "name": name, "arguments": arguments}],
        model=model,
        finish_reason="tool_calls",
        usage={"prompt_tokens": 90, "completion_tokens": 10, "total_tokens": 100},
    )


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(fake_llm: FakeLLM) -> TestClient:
    app = create_app(make_settings(), llm=fake_llm)
    return TestClient(app)
