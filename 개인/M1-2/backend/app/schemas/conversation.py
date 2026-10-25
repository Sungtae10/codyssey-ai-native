"""대화 기록 API의 요청·응답 모델.

대화 불러오기 방식: (A) 사용
- GET /api/conversations       → 목록만 (messages 없음, 가볍게)
- GET /api/conversations/{id}  → 그 대화의 messages 전체
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .data import clean_text

Role = Literal["user", "assistant"]


class MessageIn(BaseModel):
    role: Role
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def _content(cls, v: str) -> str:
        v = clean_text(v)
        if not v:
            raise ValueError("빈 메시지는 저장할 수 없습니다.")
        return v


class ToolCallLog(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = Field(None, description="AI가 이 도구를 부른 이유 (도구 인자 reason)")
    ok: bool = True


class Message(BaseModel):
    role: Role
    content: str
    created_at: str | None = None
    model: str | None = None
    tool_calls: list[ToolCallLog] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "10월 환율 정리",
                    "messages": [
                        {"role": "user", "content": "이번 달 환율 흐름 어때?"},
                        {"role": "assistant", "content": "10월 1~16일 기준으로 ..."},
                    ],
                }
            ]
        }
    )

    title: str | None = Field(None, max_length=100, description="비우면 첫 질문으로 만듭니다")
    messages: list[MessageIn] = Field(..., min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def _title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = clean_text(v)
        return v or None


class ConversationSummary(BaseModel):
    id: str
    title: str
    message_count: int
    preview: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class ConversationDetail(ConversationSummary):
    messages: list[Message]


class ConversationListResponse(BaseModel):
    count: int
    items: list[ConversationSummary]
