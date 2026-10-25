"""설정·보안 관련 테스트: 서비스 계정 키 읽기, Firestore 미설정 시 안내, CORS, 예상 못 한 오류 처리, 도구 API."""
from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient

from app.database import load_service_account_info
from app.errors import StorageUnavailableError
from app.factory import create_app
from app.repositories.memory_store import MemoryStore
from conftest import FakeLLM, make_settings

FAKE_KEY = {
    "type": "service_account",
    "project_id": "demo-project",
    "private_key": "-----BEGIN PRIVATE KEY-----\\nABC\\n-----END PRIVATE KEY-----\\n",
    "client_email": "bot@demo-project.iam.gserviceaccount.com",
}


def test_service_account_json_plain_base64_and_escaped_newlines():
    info = load_service_account_info(make_settings(firebase_service_account_json=json.dumps(FAKE_KEY)))
    assert info["project_id"] == "demo-project" and "\n" in info["private_key"] and "\\n" not in info["private_key"]
    b64 = base64.b64encode(json.dumps(FAKE_KEY).encode()).decode()
    assert load_service_account_info(make_settings(firebase_service_account_json=b64))["client_email"].startswith("bot@")


@pytest.mark.parametrize(
    "raw,needle",
    [
        (None, "FIREBASE_SERVICE_ACCOUNT_JSON"),
        ("{not json", "JSON으로 읽지 못했습니다"),
        ("@@@", "형식이 올바르지 않습니다"),
        (json.dumps({"type": "authorized_user"}), "서비스 계정 키가 아닙니다"),
    ],
)
def test_service_account_errors(raw, needle):
    with pytest.raises(StorageUnavailableError) as info:
        load_service_account_info(make_settings(firebase_service_account_json=raw))
    assert needle in info.value.message


def test_firestore_not_configured_gives_clear_503_and_health_degraded():
    c = TestClient(create_app(make_settings(storage_backend="firestore"), llm=FakeLLM()))
    health = c.get("/health").json()
    assert health["status"] == "degraded" and health["storage"]["ready"] is False
    assert "FIREBASE_SERVICE_ACCOUNT_JSON" in health["storage"]["error"]
    r = c.get("/api/data")
    assert r.status_code == 503 and "FIREBASE_SERVICE_ACCOUNT_JSON" in r.json()["detail"]
    assert c.get("/docs").status_code == 200  # Swagger는 그대로 열림


def test_cors_allowed_and_blocked_origins(client):
    pre = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    r = client.options("/api/chat", headers={"Origin": "https://my-app.vercel.app", **pre})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "https://my-app.vercel.app"
    r = client.options("/api/chat", headers={"Origin": "https://evil.example.com", **pre})
    assert "access-control-allow-origin" not in r.headers
    r = client.get("/api/data/export", headers={"Origin": "http://localhost:5500"})
    assert "content-disposition" in r.headers["access-control-expose-headers"].lower()


def test_origin_regex_for_vercel_previews():
    c = TestClient(create_app(make_settings(allowed_origin_regex=r"https://.*\.vercel\.app"), llm=FakeLLM()))
    r = c.get("/health", headers={"Origin": "https://preview-abc.vercel.app"})
    assert r.headers.get("access-control-allow-origin") == "https://preview-abc.vercel.app"


class BrokenStore(MemoryStore):
    def list_documents(self, *args, **kwargs):
        raise RuntimeError("boom")


def test_unexpected_error_returns_json_500_with_cors():
    c = TestClient(create_app(make_settings(), store=BrokenStore(), llm=FakeLLM()), raise_server_exceptions=False)
    r = c.get("/api/data", headers={"Origin": "http://localhost:5500"})
    assert r.status_code == 500 and r.json() == {"detail": "서버 내부 오류가 발생했습니다."}
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5500"


def test_tools_api(client):
    r = client.get("/api/tools")
    names = [t["function"]["name"] for t in r.json()["tools"]]
    assert names == ["get_data_summary", "get_data_by_range", "get_top_records", "get_statistics",
                     "list_conversations", "get_conversation"]
    for spec in r.json()["tools"]:
        assert "reason" in spec["function"]["parameters"]["required"]

    r = client.post("/api/tools/get_data_by_range", json={"start_date": "2026-09", "end_date": "2026-09"})
    res = r.json()["result"]
    assert r.json()["ok"] and res["start"] == "2026-09-01" and res["end"] == "2026-09-30" and res["count"] == 21

    r = client.post("/api/tools/get_data_by_range", json={"start_date": "2025-10-01", "end_date": "2026-10-31"})
    assert r.json()["result"]["records_omitted"] is True and len(r.json()["result"]["monthly"]) == 13

    r = client.post("/api/tools/get_top_records", json={"order": "desc", "limit": 50})
    assert len(r.json()["result"]["records"]) == 10 and r.json()["result"]["records"][0]["value"] == 1555.96

    assert client.post("/api/tools/get_conversation", json={"conversation_id": "../x"}).json()["ok"] is False
    assert client.post("/api/tools/delete_everything", json={}).status_code == 404
