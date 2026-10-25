"""AI 채팅 API 테스트: 컨텍스트 주입, 이어 대화, 도구 호출, 자동 저장, 비용 보호."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.factory import create_app
from app.services.ai_client import LLMResult
from conftest import FakeLLM, answer, make_settings, tool_call


def test_chat_injects_summary_and_saves(client, fake_llm):
    fake_llm.script = [answer("10월은 1,334.03원까지 내려왔어요.")]
    r = client.post("/api/chat", json={"message": "이번 달 환율 흐름 어때?"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["reply"].startswith("10월") and data["model"] == "fake-model"
    assert data["summary_used"]["count"] == 251 and data["summary_used"]["trend"].startswith("하락")

    sent = fake_llm.calls[0]["messages"]
    system = sent[0]["content"]
    assert sent[0]["role"] == "system" and "[사용자 데이터 요약]" in system
    assert "2025-10-16 ~ 2026-10-16" in system and "총 레코드: 251개" in system
    assert "최고 1,555.96원 (2026-06-05)" in system and "최근 트렌드: 하락" in system
    assert sent[-1] == {"role": "user", "content": "이번 달 환율 흐름 어때?"}
    assert fake_llm.calls[0]["tools"] and fake_llm.calls[0]["tool_choice"] == "auto"

    conv = client.get(f"/api/conversations/{data['conversation_id']}").json()
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]
    assert conv["messages"][1]["model"] == "fake-model"
    assert conv["title"] == "이번 달 환율 흐름 어때?"


def test_chat_continues_conversation_with_history(client, fake_llm):
    fake_llm.script = [answer("첫 답"), answer("둘째 답")]
    first = client.post("/api/chat", json={"message": "첫 질문"}).json()
    second = client.post("/api/chat", json={"message": "둘째 질문", "conversation_id": first["conversation_id"]}).json()
    assert second["conversation_id"] == first["conversation_id"]
    sent = fake_llm.calls[1]["messages"]
    assert [m["role"] for m in sent] == ["system", "user", "assistant", "user"]
    assert sent[1]["content"] == "첫 질문" and sent[2]["content"] == "첫 답"
    conv = client.get(f"/api/conversations/{first['conversation_id']}").json()
    assert conv["message_count"] == 4
    assert client.post("/api/chat", json={"message": "x", "conversation_id": "unknownId"}).status_code == 404


def test_chat_tool_calling_flow(client, fake_llm):
    args = json.dumps({"start_date": "2026-10-01", "end_date": "2026-10-16", "reason": "10월 날짜별 값을 보려고"})
    fake_llm.script = [tool_call("get_data_by_range", args), answer("10월 최고는 1,364.83원이었어요.")]
    r = client.post("/api/chat", json={"message": "10월 날짜별로 보여줘"})
    assert r.status_code == 200, r.text
    logs = r.json()["tool_calls"]
    assert logs == [
        {"name": "get_data_by_range", "arguments": {"start_date": "2026-10-01", "end_date": "2026-10-16"},
         "reason": "10월 날짜별 값을 보려고", "ok": True}
    ]
    second_call = fake_llm.calls[1]["messages"]
    assert second_call[-2]["role"] == "assistant" and second_call[-2]["tool_calls"][0]["id"] == "call_1"
    tool_msg = second_call[-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "call_1"
    payload = json.loads(tool_msg["content"])
    assert payload["count"] == 11 and payload["max"] == 1364.83 and len(payload["records"]) == 11

    conv = client.get(f"/api/conversations/{r.json()['conversation_id']}").json()
    assert conv["messages"][1]["tool_calls"][0]["name"] == "get_data_by_range"


def test_tool_loop_stops_after_max_rounds(fake_llm):
    settings = make_settings(max_tool_rounds=2)
    app = create_app(settings, llm=fake_llm)
    c = TestClient(app)
    args = json.dumps({"reason": "확인"})
    fake_llm.script = [
        tool_call("get_data_summary", args, "a"),
        tool_call("get_data_summary", args, "b"),
        answer("마지막 답"),
    ]
    r = c.post("/api/chat", json={"message": "q"})
    assert r.status_code == 200 and r.json()["reply"] == "마지막 답"
    assert [call["tool_choice"] for call in fake_llm.calls] == ["auto", "auto", "none"]


def test_bad_tool_arguments_are_reported_not_crashing(client, fake_llm):
    fake_llm.script = [tool_call("get_data_by_range", "{not json"), answer("다시 확인할게요")]
    r = client.post("/api/chat", json={"message": "q"})
    assert r.status_code == 200
    assert r.json()["tool_calls"][0]["ok"] is False
    assert "error" in json.loads(fake_llm.calls[1]["messages"][-1]["content"])


def test_empty_reply_is_error_and_not_saved(client, fake_llm):
    fake_llm.script = [LLMResult(content="", tool_calls=[], model="m", finish_reason="length", usage={})]
    r = client.post("/api/chat", json={"message": "q"})
    assert r.status_code == 502 and "OPENAI_MAX_TOKENS" in r.json()["detail"]
    assert client.get("/api/conversations").json()["count"] == 0


def test_rate_limit_per_minute():
    app = create_app(make_settings(chat_rate_limit_per_minute=2), llm=FakeLLM())
    c = TestClient(app)
    assert c.post("/api/chat", json={"message": "1"}).status_code == 200
    assert c.post("/api/chat", json={"message": "2"}).status_code == 200
    r = c.post("/api/chat", json={"message": "3"})
    assert r.status_code == 429 and "초 뒤" in r.json()["detail"]
    # 다른 IP(프록시 헤더)는 따로 센다
    assert c.post("/api/chat", json={"message": "4"}, headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 200


def test_chat_validation_and_missing_key():
    c = TestClient(create_app(make_settings(openai_api_key=None)))  # 실제 LLMClient, 키 없음
    assert c.post("/api/chat", json={"message": ""}).status_code == 422
    assert c.post("/api/chat", json={"message": "a" * 1001}).status_code == 422
    assert c.post("/api/chat", json={"message": "q", "conversation_id": "../etc"}).status_code == 422
    r = c.post("/api/chat", json={"message": "안녕"})
    assert r.status_code == 503 and "OPENAI_API_KEY" in r.json()["detail"]


def test_tools_disabled_sends_no_tools(fake_llm):
    c = TestClient(create_app(make_settings(enable_tools=False), llm=fake_llm))
    assert c.post("/api/chat", json={"message": "q"}).status_code == 200
    assert fake_llm.calls[0]["tools"] is None
    assert "도구" not in fake_llm.calls[0]["messages"][0]["content"].split("[답변 규칙]")[1].split("\n")[2]
