"""2차 검토에서 나온 지적을 고친 부분의 테스트.

- 캐시: 읽는 도중 쓰기가 일어나면 오래된 목록을 캐시에 넣지 않는다
- 날짜 중복 확인: 캐시가 아니라 저장소를 직접 확인한다
- Firestore 실행 중 오류: 원인별 한국어 안내(503), /health도 실제 읽기로 확인
- 요청 제한: 서버 전체 분당 제한, IP별 하루 제한, 프록시 헤더 우선순위
- 대화: 직접 정한 제목 100자 유지, 대화 크기 상한(413), 월별 프롬프트 13개월 상한, 질문 전체 시간 상한(504)
"""
from __future__ import annotations

import json
import time

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from app.database import read_seed_csv
from app.errors import AIServiceError, RateLimitedError, StorageUnavailableError
from app.factory import create_app
from app.rate_limit import RateLimiter
from app.repositories.firestore_store import FirestoreStore, firestore_error_message
from app.repositories.memory_store import MemoryStore
from app.services.ai_client import LLMClient
from app.services.conversation_service import MAX_MESSAGES
from app.services.prompt import summary_to_text
from conftest import CSV_PATH, FakeLLM, answer, make_settings


class HookStore(MemoryStore):
    """전체 목록을 읽은 직후 한 번, 다른 요청의 쓰기를 흉내 낸다."""

    def __init__(self):
        super().__init__()
        self.hook = None

    def list_documents(self, *args, **kwargs):
        docs = super().list_documents(*args, **kwargs)
        if self.hook and kwargs.get("order_by") == "date":
            hook, self.hook = self.hook, None
            hook()
        return docs


def seeded(store_cls=MemoryStore):
    store = store_cls()
    store.batch_create("data", read_seed_csv(CSV_PATH))
    return store


def test_stale_read_is_not_cached_after_concurrent_write():
    store = seeded(HookStore)
    app = create_app(make_settings(), store=store, llm=FakeLLM())
    data = app.state.container.data
    from app.schemas.data import DataCreate

    store.hook = lambda: data.create(DataCreate(date="2026-10-19", value=1336.5, memo="동시 쓰기"))
    first = data.summary()
    assert first["count"] == 251  # 쓰기 전에 읽은 결과
    assert data.summary()["count"] == 252  # 오래된 결과가 캐시에 남지 않아 바로 반영됨


def test_duplicate_check_reads_store_not_cache():
    store = seeded()
    c = TestClient(create_app(make_settings(), store=store, llm=FakeLLM()))
    assert c.get("/api/data/summary").json()["count"] == 251  # 캐시 채움
    store.create_document("data", {"date": "2026-10-19", "value": 1.0, "memo": "다른 경로로 저장"})
    r = c.post("/api/data", json={"date": "2026-10-19", "value": 1336.5})
    assert r.status_code == 409


class FailingStore(MemoryStore):
    def __init__(self, exc):
        super().__init__()
        self.exc = exc

    def list_documents(self, *args, **kwargs):
        raise self.exc


def test_health_probe_reports_runtime_storage_errors():
    store = FailingStore(StorageUnavailableError("Firestore 데이터베이스를 찾지 못했습니다."))
    c = TestClient(create_app(make_settings(), store=store, llm=FakeLLM()))
    health = c.get("/health").json()
    assert health["status"] == "degraded" and "찾지 못했습니다" in health["storage"]["error"]


def test_firestore_error_messages():
    from google.api_core import exceptions as gexc

    assert "데이터베이스를 찾지 못했습니다" in firestore_error_message(gexc.NotFound("x"))
    assert "권한이 없습니다" in firestore_error_message(gexc.PermissionDenied("x"))
    assert "무료 사용량" in firestore_error_message(gexc.ResourceExhausted("x"))
    assert "잠시 연결하지 못했습니다" in firestore_error_message(gexc.ServiceUnavailable("x"))
    RefreshError = type("RefreshError", (Exception,), {})
    assert "인증하지 못했습니다" in firestore_error_message(RefreshError("x"))


class BrokenDB:
    def collection(self, name):
        from google.api_core import exceptions as gexc

        raise gexc.NotFound("The database (default) does not exist")


def test_firestore_store_maps_errors_to_503():
    store = FirestoreStore(BrokenDB())
    with pytest.raises(StorageUnavailableError):
        store.list_documents("data")
    c = TestClient(create_app(make_settings(storage_backend="firestore"), store=store, llm=FakeLLM()))
    r = c.get("/api/data")
    assert r.status_code == 503 and "데이터베이스를 찾지 못했습니다" in r.json()["detail"]
    assert c.get("/health").json()["storage"]["ready"] is False


def test_rate_limiter_global_and_per_ip_day():
    limiter = RateLimiter(per_minute=100, per_day=1000, global_per_minute=3, per_ip_day=1000)
    for ip in ("a", "b", "c"):
        limiter.check(ip)
    with pytest.raises(RateLimitedError) as info:
        limiter.check("d")  # IP를 바꿔도 서버 전체 분당 제한에 걸림
    assert "잠시 쉬고" in info.value.message

    limiter = RateLimiter(per_minute=100, per_day=1000, global_per_minute=100, per_ip_day=2)
    limiter.check("x")
    limiter.check("x")
    with pytest.raises(RateLimitedError) as info:
        limiter.check("x")
    assert "이 기기" in info.value.message
    limiter.check("y")  # 다른 IP는 계속 가능


def test_client_ip_prefers_proxy_set_headers():
    app = create_app(make_settings(chat_rate_limit_per_minute=1), llm=FakeLLM())
    c = TestClient(app)
    h = {"CF-Connecting-IP": "9.9.9.9", "X-Forwarded-For": "1.1.1.1"}
    assert c.post("/api/chat", json={"message": "1"}, headers=h).status_code == 200
    h2 = {"CF-Connecting-IP": "9.9.9.9", "X-Forwarded-For": "2.2.2.2"}  # XFF를 바꿔도 같은 IP로 셈
    assert c.post("/api/chat", json={"message": "2"}, headers=h2).status_code == 429


def test_explicit_title_keeps_100_chars_and_auto_title_is_40(client):
    long_title = "가" * 60
    conv = client.post("/api/conversations", json={"title": long_title, "messages": [{"role": "user", "content": "q"}]}).json()
    assert conv["title"] == long_title
    auto = client.post("/api/conversations", json={"messages": [{"role": "user", "content": "나" * 60}]}).json()
    assert len(auto["title"]) == 40 and auto["title"].endswith("…")


def test_conversation_size_limits(client, fake_llm):
    assert client.post("/api/conversations", json={"messages": [{"role": "user", "content": "q"}] * 101}).status_code == 422
    assert client.post("/api/conversations", json={"messages": [{"role": "user", "content": "가" * 4001}]}).status_code == 422
    conv = client.post("/api/conversations", json={"messages": [{"role": "user", "content": "q"}] * 100}).json()
    store = client.app.state.container.store.get()
    msgs = [{"role": "user", "content": "q"}] * MAX_MESSAGES
    store.update_document("conversations", conv["id"], {"messages": msgs, "message_count": len(msgs)})
    r = client.post("/api/chat", json={"message": "더", "conversation_id": conv["id"]})
    assert r.status_code == 413 and "새 대화" in r.json()["detail"]
    assert fake_llm.calls == []  # OpenAI를 부르기 전에 멈춤 (비용 없음)


def test_prompt_monthly_lines_are_capped():
    monthly = [{"month": f"2025-{m:02d}", "average": 1.0, "min": 1.0, "max": 1.0, "count": 1} for m in range(1, 13)]
    monthly += [{"month": f"2026-{m:02d}", "average": 2.0, "min": 2.0, "max": 2.0, "count": 1} for m in range(1, 9)]
    summary = {"dataset": {"name": "n", "unit": "원", "source": "s"}, "period": "p", "count": 20, "metrics": None,
               "trend": "보합", "monthly": monthly, "recent": []}
    text = summary_to_text(summary)
    assert "최근 13개월만 표시" in text and "2025-07" not in text and "2025-08" in text and "2026-08" in text


def test_deadline_stops_before_calling_openai():
    llm = LLMClient(make_settings())
    seen = []
    llm._client = openai.OpenAI(
        api_key="k", base_url="http://fake.local/v1", max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(lambda req: seen.append(1) or httpx.Response(500))),
    )
    with pytest.raises(AIServiceError) as info:
        llm.complete([{"role": "user", "content": "q"}], deadline=time.monotonic() + 1)
    assert info.value.status_code == 504 and seen == []


def test_chat_passes_deadline_to_llm(client, fake_llm):
    fake_llm.script = [answer("답")]
    before = time.monotonic()
    assert client.post("/api/chat", json={"message": "q"}).status_code == 200
    deadline = fake_llm.calls[0]["deadline"]
    assert before + 70 < deadline < time.monotonic() + 76  # 기본 75초
