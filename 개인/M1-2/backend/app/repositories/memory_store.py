"""메모리 저장소: 자동 테스트와 키 없는 로컬 미리보기용.

서버를 끄면 내용이 사라진다. 배포(Render)에서는 쓰지 않는다 (STORAGE_BACKEND=firestore가 기본값).
"""
from __future__ import annotations

import copy
import secrets
import string
import threading
from typing import Any

from .base import DocumentStore

_ID_CHARS = string.ascii_letters + string.digits


def _new_id() -> str:
    # Firestore 자동 ID와 같은 모양(영문 대소문자+숫자 20자)
    return "".join(secrets.choice(_ID_CHARS) for _ in range(20))


class MemoryStore(DocumentStore):
    backend_name = "memory"

    def __init__(self) -> None:
        self._collections: dict[str, dict[str, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def _col(self, collection: str) -> dict[str, dict[str, Any]]:
        return self._collections.setdefault(collection, {})

    def list_documents(self, collection, order_by=None, descending=False, limit=None):
        with self._lock:
            docs = [{**copy.deepcopy(d), "id": doc_id} for doc_id, d in self._col(collection).items()]
        if order_by:
            docs = [d for d in docs if order_by in d]
            docs.sort(key=lambda d: d[order_by], reverse=descending)
        if limit is not None:
            docs = docs[:limit]
        return docs

    def get_document(self, collection, doc_id):
        with self._lock:
            doc = self._col(collection).get(doc_id)
            return {**copy.deepcopy(doc), "id": doc_id} if doc is not None else None

    def create_document(self, collection, data):
        with self._lock:
            doc_id = _new_id()
            self._col(collection)[doc_id] = copy.deepcopy(data)
        return {**copy.deepcopy(data), "id": doc_id}

    def update_document(self, collection, doc_id, changes):
        with self._lock:
            doc = self._col(collection).get(doc_id)
            if doc is None:
                return None
            doc.update(copy.deepcopy(changes))
            return {**copy.deepcopy(doc), "id": doc_id}

    def delete_document(self, collection, doc_id):
        with self._lock:
            return self._col(collection).pop(doc_id, None) is not None

    def batch_create(self, collection, rows):
        with self._lock:
            col = self._col(collection)
            for row in rows:
                col[_new_id()] = copy.deepcopy(row)
        return len(rows)
