"""서버가 켜질 때 비어 있는 data 컬렉션에 초기 데이터를 올리는 기능(SEED_IF_EMPTY) 점검."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import load_settings
from app.database import StoreProvider
from app.errors import StorageUnavailableError
from app.factory import create_app
from app.repositories.memory_store import MemoryStore
from app.services.seed import seed_if_empty

from conftest import CSV_PATH, FakeLLM, make_settings


def seed_settings(**overrides):
    base = dict(seed_if_empty=True, seed_csv=CSV_PATH)
    base.update(overrides)
    return make_settings(**base)


def test_seed_fills_empty_collection():
    store = MemoryStore()
    settings = seed_settings()
    assert seed_if_empty(StoreProvider(settings, store), settings) == 251
    assert len(store.list_documents("data")) == 251


def test_seed_skips_when_any_document_exists():
    store = MemoryStore()
    store.create_document("data", {"date": "2026-10-16", "value": 1334.03, "memo": "직접 넣은 값"})
    settings = seed_settings()
    assert seed_if_empty(StoreProvider(settings, store), settings) == 0
    assert [d["memo"] for d in store.list_documents("data")] == ["직접 넣은 값"]  # 덮어쓰지 않음


def test_seed_is_off_by_default():
    store = MemoryStore()
    settings = make_settings()
    assert settings.seed_if_empty is False
    assert seed_if_empty(StoreProvider(settings, store), settings) == 0
    assert store.list_documents("data") == []


def test_seed_skips_when_csv_is_missing():
    store = MemoryStore()
    settings = seed_settings(seed_csv=str(CSV_PATH) + ".없음")
    assert seed_if_empty(StoreProvider(settings, store), settings) == 0
    assert store.list_documents("data") == []


def test_app_start_seeds_once_and_restart_does_not_duplicate():
    store = MemoryStore()
    with TestClient(create_app(seed_settings(), store=store, llm=FakeLLM())) as client:
        assert client.get("/api/data/summary").json()["count"] == 251
    with TestClient(create_app(seed_settings(), store=store, llm=FakeLLM())) as client:  # 다시 켜기
        assert client.get("/api/data/summary").json()["count"] == 251
    assert len(store.list_documents("data")) == 251


class BrokenStore(MemoryStore):
    def list_documents(self, *args, **kwargs):
        raise StorageUnavailableError("Firestore에 연결하지 못했습니다 (테스트용 고장).")


def test_seed_failure_keeps_server_running():
    with TestClient(create_app(seed_settings(), store=BrokenStore(), llm=FakeLLM())) as client:
        body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert body["storage"]["ready"] is False


def test_seed_flag_comes_from_environment(monkeypatch):
    monkeypatch.setenv("SEED_IF_EMPTY", "true")
    assert load_settings().seed_if_empty is True
    monkeypatch.setenv("SEED_IF_EMPTY", "false")
    assert load_settings().seed_if_empty is False
