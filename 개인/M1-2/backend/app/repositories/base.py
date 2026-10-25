"""저장소 인터페이스.

서비스 계층은 이 인터페이스만 알고, 실제 저장소(Firestore 또는 메모리)는 모른다.
그래서 배포에서는 Firestore를, 자동 테스트에서는 키 없이 메모리 저장소를 같은 코드로 쓴다.
각 문서는 dict이며, 읽어 올 때 문서 ID를 "id" 키로 붙여 돌려준다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DocumentStore(ABC):
    backend_name = "base"

    @abstractmethod
    def list_documents(
        self,
        collection: str,
        order_by: str | None = None,
        descending: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """컬렉션의 문서 목록을 읽는다."""

    @abstractmethod
    def get_document(self, collection: str, doc_id: str) -> dict[str, Any] | None:
        """문서 하나를 읽는다. 없으면 None."""

    @abstractmethod
    def create_document(self, collection: str, data: dict[str, Any]) -> dict[str, Any]:
        """자동 ID로 새 문서를 만들고, id를 붙인 문서를 돌려준다."""

    @abstractmethod
    def update_document(
        self, collection: str, doc_id: str, changes: dict[str, Any]
    ) -> dict[str, Any] | None:
        """일부 필드를 바꾸고 바뀐 문서 전체를 돌려준다. 없으면 None."""

    @abstractmethod
    def delete_document(self, collection: str, doc_id: str) -> bool:
        """문서를 지운다. 없었으면 False."""

    @abstractmethod
    def batch_create(self, collection: str, rows: list[dict[str, Any]]) -> int:
        """여러 문서를 한 번에 만든다 (초기 데이터 업로드용). 만든 개수를 돌려준다."""

    def delete_many(self, collection: str, doc_ids: list[str]) -> int:
        """여러 문서를 지운다 (초기화용). 지운 개수를 돌려준다."""
        return sum(1 for doc_id in doc_ids if self.delete_document(collection, doc_id))

    def find_documents(self, collection: str, field: str, value: Any, limit: int = 5) -> list[dict[str, Any]]:
        """field == value 인 문서를 찾는다 (같은 날짜 중복 확인용)."""
        return [d for d in self.list_documents(collection) if d.get(field) == value][:limit]

    def ping(self, collection: str) -> None:
        """연결 확인: 문서 1개만 읽어 본다. 실패하면 예외."""
        self.list_documents(collection, limit=1)
