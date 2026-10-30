"""AI 채팅 API의 요청·응답 모델."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .conversation import ToolCallLog
from .data import clean_text

ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"message": "이번 달 환율 흐름 어때?", "conversation_id": None}]}
    )

    message: str = Field(..., min_length=1, max_length=1000, description="질문 (최대 1000자)")
    conversation_id: str | None = Field(
        None, pattern=ID_PATTERN, description="이어서 대화할 때 대화 ID. 비우면 새 대화를 만들어 저장합니다"
    )

    @field_validator("message")
    @classmethod
    def _message(cls, v: str) -> str:
        v = clean_text(v)
        if not v:
            raise ValueError("질문을 입력하세요.")
        return v


class ChatResponse(BaseModel):
    conversation_id: str
    conversation_title: str
    reply: str
    model: str = Field(..., description="실제로 답한 모델")
    tool_calls: list[ToolCallLog] = Field(default_factory=list)
    summary_used: dict[str, Any] = Field(default_factory=dict, description="시스템 프롬프트에 넣은 요약 (일부)")
    usage: dict[str, int] | None = None
    created_at: str
