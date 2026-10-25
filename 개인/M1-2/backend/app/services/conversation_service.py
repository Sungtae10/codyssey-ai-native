"""대화 기록 서비스.

문서 하나 = 대화 하나. messages 배열에 질문과 답을 차례로 쌓는다.
목록(list)은 가볍게 messages를 빼고 돌려주고, 상세(get)에서 messages 전체를 준다.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

from ..config import Settings
from ..database import utc_now_iso
from ..errors import AppError, NotFoundError
from ..repositories.base import DocumentStore
from ..schemas.conversation import ConversationCreate

AUTO_TITLE_MAX = 40  # 첫 질문으로 자동으로 만드는 제목
TITLE_MAX = 100  # 사용자가 직접 정한 제목
PREVIEW_MAX = 80
MAX_MESSAGES = 200  # 대화 하나에 저장하는 메시지 수 상한
MAX_DOC_BYTES = 900_000  # Firestore 문서 한도(1MiB)보다 여유 있게


def _shorten(text: str, limit: int) -> str:
    one_line = re.sub(r"\s+", " ", text).strip()
    return one_line if len(one_line) <= limit else one_line[: limit - 1].rstrip() + "…"


def _summary(doc: dict[str, Any]) -> dict[str, Any]:
    messages = doc.get("messages") or []
    return {
        "id": doc["id"],
        "title": doc.get("title") or "제목 없음",
        "message_count": int(doc.get("message_count", len(messages))),
        "preview": doc.get("preview", ""),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def _detail(doc: dict[str, Any]) -> dict[str, Any]:
    return {**_summary(doc), "messages": list(doc.get("messages") or [])}


class ConversationService:
    def __init__(self, store_getter: Callable[[], DocumentStore], settings: Settings) -> None:
        self._store = store_getter
        self._collection = settings.conversations_collection

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        docs = self._store().list_documents(self._collection, order_by="updated_at", descending=True, limit=limit)
        return [_summary(d) for d in docs]

    def get(self, conversation_id: str) -> dict[str, Any]:
        doc = self._store().get_document(self._collection, conversation_id)
        if doc is None:
            raise NotFoundError(f"id={conversation_id} 대화를 찾지 못했습니다.")
        return _detail(doc)

    def create(self, payload: ConversationCreate) -> dict[str, Any]:
        now = utc_now_iso()
        messages = [{"role": m.role, "content": m.content, "created_at": now} for m in payload.messages]
        return self._create(messages, payload.title)

    @staticmethod
    def _check_size(messages: list[dict[str, Any]]) -> None:
        too_long = AppError("대화가 너무 길어 더 저장할 수 없어요. 새 대화를 시작하세요.", 413)
        if len(messages) > MAX_MESSAGES:
            raise too_long
        if len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) > MAX_DOC_BYTES:
            raise too_long

    def ensure_room(self, conv: dict[str, Any]) -> None:
        """채팅 한 번(메시지 2개)을 더 저장할 수 있는지 미리 확인한다 (OpenAI 호출 전)."""
        messages = conv.get("messages") or []
        if len(messages) + 2 > MAX_MESSAGES or len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) > MAX_DOC_BYTES - 20_000:
            raise AppError("대화가 너무 길어 더 저장할 수 없어요. 새 대화를 시작하세요.", 413)

    def _create(self, messages: list[dict[str, Any]], title: str | None = None) -> dict[str, Any]:
        self._check_size(messages)
        now = utc_now_iso()
        first_user = next((m["content"] for m in messages if m["role"] == "user"), messages[0]["content"])
        doc = self._store().create_document(
            self._collection,
            {
                "title": _shorten(title, TITLE_MAX) if title else _shorten(first_user, AUTO_TITLE_MAX),
                "messages": messages,
                "message_count": len(messages),
                "preview": _shorten(messages[-1]["content"], PREVIEW_MAX),
                "created_at": now,
                "updated_at": now,
            },
        )
        return _detail(doc)

    def save_chat_turn(
        self, conversation_id: str | None, user_message: dict[str, Any], assistant_message: dict[str, Any]
    ) -> dict[str, Any]:
        """채팅 한 번(질문 + 답)을 저장한다. ID가 없으면 새 대화를 만든다 (자동 저장)."""
        if conversation_id is None:
            return self._create([user_message, assistant_message])
        store = self._store()
        doc = store.get_document(self._collection, conversation_id)
        if doc is None:
            raise NotFoundError(f"id={conversation_id} 대화를 찾지 못했습니다.")
        messages = list(doc.get("messages") or []) + [user_message, assistant_message]
        self._check_size(messages)
        updated = store.update_document(
            self._collection,
            conversation_id,
            {
                "messages": messages,
                "message_count": len(messages),
                "preview": _shorten(assistant_message["content"], PREVIEW_MAX),
                "updated_at": utc_now_iso(),
            },
        )
        if updated is None:
            raise NotFoundError(f"id={conversation_id} 대화를 찾지 못했습니다.")
        return _detail(updated)

    def delete(self, conversation_id: str) -> None:
        if not self._store().delete_document(self._collection, conversation_id):
            raise NotFoundError(f"id={conversation_id} 대화를 찾지 못했습니다.")
