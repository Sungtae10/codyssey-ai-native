"""FirestoreStore 코드 경로 테스트.

실제 Firestore 대신 같은 모양의 API를 흉내 내는 mock-firestore 라이브러리를 쓴다.
(mock-firestore에는 batch가 없어 아주 작은 가짜 batch를 붙인다.)
실제 Firestore 연결은 배포 후 /health와 화면에서 확인한다.
"""
from __future__ import annotations

import pytest

mockfirestore = pytest.importorskip("mockfirestore")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import read_seed_csv  # noqa: E402
from app.factory import create_app  # noqa: E402
from app.repositories.firestore_store import FirestoreStore  # noqa: E402
from conftest import CSV_PATH, FakeLLM, answer, make_settings  # noqa: E402


class _Batch:
    def __init__(self):
        self.ops = []

    def set(self, ref, data):
        self.ops.append(("set", ref, data))

    def delete(self, ref):
        self.ops.append(("delete", ref, None))

    def commit(self):
        for op, ref, data in self.ops:
            ref.set(data) if op == "set" else ref.delete()


class MockDB(mockfirestore.MockFirestore):
    def batch(self):
        return _Batch()


@pytest.fixture
def store():
    s = FirestoreStore(MockDB())
    s.batch_create("data", read_seed_csv(CSV_PATH))
    return s


def test_store_basic_operations(store):
    assert len(store.list_documents("data")) == 251
    first = store.list_documents("data", order_by="date", limit=1)[0]
    assert first["date"] == "2025-10-16" and len(first["id"]) == 20
    last = store.list_documents("data", order_by="date", descending=True, limit=1)[0]
    assert last["date"] == "2026-10-16"

    created = store.create_document("data", {"date": "2026-10-19", "value": 1.0, "memo": ""})
    assert store.get_document("data", created["id"])["value"] == 1.0
    updated = store.update_document("data", created["id"], {"value": 2.0})
    assert updated["value"] == 2.0 and updated["date"] == "2026-10-19"
    assert store.update_document("data", "missing", {"value": 1}) is None
    assert store.delete_document("data", created["id"]) is True
    assert store.delete_document("data", created["id"]) is False
    assert store.get_document("data", created["id"]) is None


def test_store_delete_many(store):
    ids = [d["id"] for d in store.list_documents("data")][:10]
    assert store.delete_many("data", ids) == 10
    assert len(store.list_documents("data")) == 241


def test_full_api_on_firestore_store(store):
    fake = FakeLLM([answer("답")])
    c = TestClient(create_app(make_settings(storage_backend="firestore"), store=store, llm=fake))
    assert c.get("/health").json()["storage"] == {"backend": "firestore", "ready": True, "error": None}
    assert c.get("/api/data/summary").json()["count"] == 251
    rec = c.post("/api/data", json={"date": "2026-10-19", "value": 1336.1, "memo": "m"}).json()
    assert c.put(f"/api/data/{rec['id']}", json={"memo": "수정"}).json()["memo"] == "수정"
    assert c.delete(f"/api/data/{rec['id']}").status_code == 200
    chat = c.post("/api/chat", json={"message": "안녕"}).json()
    listed = c.get("/api/conversations").json()["items"]
    assert listed[0]["id"] == chat["conversation_id"] and listed[0]["message_count"] == 2
