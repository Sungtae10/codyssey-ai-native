"""대화 기록 API 테스트 (저장, 목록, 불러오기, 삭제)."""
from __future__ import annotations

import time


def test_conversation_crud(client):
    body = {
        "messages": [
            {"role": "user", "content": "이번 달 환율 흐름 어때? 아주 길게 써 보는 질문이라 제목이 잘리는지 확인합니다"},
            {"role": "assistant", "content": "10월 1~16일 기준으로 하락 흐름입니다."},
        ]
    }
    r = client.post("/api/conversations", json=body)
    assert r.status_code == 201, r.text
    conv = r.json()
    assert conv["message_count"] == 2 and len(conv["title"]) <= 40 and conv["title"].endswith("…")
    assert conv["preview"].startswith("10월")

    r = client.get("/api/conversations")
    assert r.status_code == 200 and r.json()["count"] == 1
    item = r.json()["items"][0]
    assert "messages" not in item  # (A) 방식: 목록에는 messages 없음

    r = client.get(f"/api/conversations/{conv['id']}")
    assert r.status_code == 200 and len(r.json()["messages"]) == 2
    assert r.json()["messages"][0]["role"] == "user"

    assert client.delete(f"/api/conversations/{conv['id']}").json()["deleted"] is True
    assert client.get(f"/api/conversations/{conv['id']}").status_code == 404
    assert client.delete(f"/api/conversations/{conv['id']}").status_code == 404


def test_conversation_list_order_and_title(client):
    first = client.post("/api/conversations", json={"title": "첫 대화", "messages": [{"role": "user", "content": "a"}]}).json()
    time.sleep(0.02)  # updated_at(밀리초 단위)이 확실히 달라지도록
    second = client.post("/api/conversations", json={"messages": [{"role": "user", "content": "두 번째"}]}).json()
    ids = [c["id"] for c in client.get("/api/conversations").json()["items"]]
    assert ids == [second["id"], first["id"]]
    assert first["title"] == "첫 대화" and second["title"] == "두 번째"


def test_conversation_validation(client):
    assert client.post("/api/conversations", json={"messages": []}).status_code == 422
    assert client.post("/api/conversations", json={"messages": [{"role": "system", "content": "x"}]}).status_code == 422
    assert client.post("/api/conversations", json={"messages": [{"role": "user", "content": "   "}]}).status_code == 422
    assert client.get("/api/conversations/bad id").status_code == 422
