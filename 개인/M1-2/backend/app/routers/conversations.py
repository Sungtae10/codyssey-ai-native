"""대화 기록 API.

대화 불러오기는 (A) 방식: 목록은 messages 없이, 상세 조회에서 messages 전체를 준다.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, status

from ..container import Container, get_container
from ..schemas.chat import ID_PATTERN
from ..schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationListResponse,
)
from ..schemas.data import DeleteResponse

router = APIRouter(prefix="/api/conversations", tags=["대화 기록"])


@router.post(
    "",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="대화 저장",
    description="messages 목록을 새 대화로 저장합니다. (/api/chat은 질문할 때마다 자동으로 저장합니다)",
)
def create_conversation(payload: ConversationCreate, c: Container = Depends(get_container)):
    return c.conversations.create(payload)


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="대화 목록 조회 (messages 미포함)",
    description="최근에 바뀐 순서. 목록을 가볍게 하려고 messages는 넣지 않습니다. 전체 메시지는 GET /api/conversations/{id}.",
)
def list_conversations(
    limit: int = Query(50, ge=1, le=200, description="최대 개수"),
    c: Container = Depends(get_container),
):
    items = c.conversations.list(limit=limit)
    return {"count": len(items), "items": items}


@router.get("/{conversation_id}", response_model=ConversationDetail, summary="특정 대화 불러오기 (messages 전체)")
def get_conversation(
    conversation_id: str = Path(..., pattern=ID_PATTERN, description="대화 ID"),
    c: Container = Depends(get_container),
):
    return c.conversations.get(conversation_id)


@router.delete("/{conversation_id}", response_model=DeleteResponse, summary="대화 삭제")
def delete_conversation(
    conversation_id: str = Path(..., pattern=ID_PATTERN, description="대화 ID"),
    c: Container = Depends(get_container),
):
    c.conversations.delete(conversation_id)
    return {"id": conversation_id, "deleted": True}
