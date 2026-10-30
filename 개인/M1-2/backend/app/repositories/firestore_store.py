"""Firestore 저장소: 배포에서 쓰는 실제 데이터베이스.

컬렉션 구조
  data/{자동ID}           date(YYYY-MM-DD), value(숫자), memo, created_at, updated_at
  conversations/{자동ID}  title, messages[{role, content, created_at, model?, tool_calls?}],
                          message_count, preview, created_at, updated_at

Firestore 호출이 실패하면(데이터베이스 없음, 권한 없음, 키 무효, 무료 한도 초과 등)
StorageUnavailableError(503)로 바꾸고 "무엇을 고치면 되는지" 한국어로 알려 준다.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from ..errors import StorageUnavailableError
from .base import DocumentStore

logger = logging.getLogger(__name__)

# Firestore 일괄 쓰기 한 번에 최대 500건. 여유를 두고 400건씩 나눈다.
_BATCH_SIZE = 400


def firestore_error_message(exc: Exception) -> str:
    name = type(exc).__name__
    try:
        from google.api_core import exceptions as gexc
    except ImportError:  # pragma: no cover
        gexc = None
    if gexc is not None:
        if isinstance(exc, gexc.NotFound):
            return ("Firestore 데이터베이스를 찾지 못했습니다. Firebase 콘솔에서 Firestore 데이터베이스를 만들었는지, "
                    "FIRESTORE_DATABASE_ID 값이 맞는지 확인하세요.")
        if isinstance(exc, gexc.PermissionDenied):
            return "서비스 계정에 Firestore 권한이 없습니다. 같은 Firebase 프로젝트에서 받은 키인지 확인하세요."
        if isinstance(exc, gexc.Unauthenticated):
            return "서비스 계정 키 인증에 실패했습니다. 키를 새로 발급해 다시 넣으세요."
        if isinstance(exc, gexc.ResourceExhausted):
            return "Firestore 무료 사용량(하루 읽기·쓰기 한도)을 넘었습니다. 내일 다시 시도하세요."
        if isinstance(exc, (gexc.ServiceUnavailable, gexc.DeadlineExceeded, gexc.RetryError)):
            return "Firestore에 잠시 연결하지 못했습니다. 잠시 뒤 다시 시도하세요."
    if name == "RefreshError":  # google.auth: 키가 삭제되었거나 내용이 틀림
        return "서비스 계정 키로 인증하지 못했습니다. 키가 삭제되었거나 잘못되었는지 확인하세요."
    return f"Firestore 요청이 실패했습니다 ({name})."


@contextmanager
def _guard() -> Iterator[None]:
    try:
        yield
    except StorageUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Firestore 오류: %s", type(exc).__name__)
        raise StorageUnavailableError(firestore_error_message(exc)) from exc


class FirestoreStore(DocumentStore):
    backend_name = "firestore"

    def __init__(self, client: Any) -> None:
        self._db = client

    def list_documents(self, collection, order_by=None, descending=False, limit=None):
        with _guard():
            query = self._db.collection(collection)
            if order_by:
                query = query.order_by(order_by, direction="DESCENDING" if descending else "ASCENDING")
            if limit is not None:
                query = query.limit(limit)
            return [{**(snap.to_dict() or {}), "id": snap.id} for snap in query.stream()]

    def get_document(self, collection, doc_id):
        with _guard():
            snap = self._db.collection(collection).document(doc_id).get()
            if not snap.exists:
                return None
            return {**(snap.to_dict() or {}), "id": snap.id}

    def create_document(self, collection, data):
        with _guard():
            ref = self._db.collection(collection).document()  # 자동 ID
            ref.set(data)
            return {**data, "id": ref.id}

    def update_document(self, collection, doc_id, changes):
        with _guard():
            ref = self._db.collection(collection).document(doc_id)
            snap = ref.get()
            if not snap.exists:
                return None
            ref.update(changes)
            return {**(snap.to_dict() or {}), **changes, "id": doc_id}

    def delete_document(self, collection, doc_id):
        with _guard():
            ref = self._db.collection(collection).document(doc_id)
            if not ref.get().exists:
                return False
            ref.delete()
            return True

    def find_documents(self, collection, field, value, limit=5):
        with _guard():
            col = self._db.collection(collection)
            try:
                from google.cloud.firestore_v1.base_query import FieldFilter

                query = col.where(filter=FieldFilter(field, "==", value))
            except (ImportError, TypeError):  # 테스트용 mock-firestore는 예전 방식만 지원
                query = col.where(field, "==", value)
            return [{**(s.to_dict() or {}), "id": s.id} for s in query.limit(limit).stream()]

    def batch_create(self, collection, rows):
        with _guard():
            col = self._db.collection(collection)
            written = 0
            for start in range(0, len(rows), _BATCH_SIZE):
                batch = self._db.batch()
                for row in rows[start : start + _BATCH_SIZE]:
                    batch.set(col.document(), row)
                batch.commit()
                written += len(rows[start : start + _BATCH_SIZE])
            return written

    def delete_many(self, collection, doc_ids):
        with _guard():
            col = self._db.collection(collection)
            deleted = 0
            for start in range(0, len(doc_ids), _BATCH_SIZE):
                batch = self._db.batch()
                for doc_id in doc_ids[start : start + _BATCH_SIZE]:
                    batch.delete(col.document(doc_id))
                batch.commit()
                deleted += len(doc_ids[start : start + _BATCH_SIZE])
            return deleted
