"""
MCP 서버 (보너스): 백엔드의 AI 도구를 외부 AI 클라이언트(Claude Desktop 등)에서 쓰게 해 준다.

흐름
  외부 AI 클라이언트 ──(MCP, stdio)──▶ 이 서버 ──(HTTP)──▶ 배포된 FastAPI 백엔드
      POST /api/tools/{도구 이름}  : GPT function calling과 똑같은 도구 실행기(app/services/tools.py)
      POST /api/chat               : 데이터 요약을 주입한 AI 비서에게 질문 (ask_assistant)

실행
  pip install -r requirements.txt
  API_BASE_URL=https://<내-render-주소>.onrender.com python server.py

주의: stdio 방식에서는 표준 출력(stdout)이 통신 통로라 print를 쓰지 않는다.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
# Render 무료 서버는 잠들었다 깨는 데 1분 정도 걸릴 수 있어 넉넉히 기다린다.
HTTP_TIMEOUT = float(os.environ.get("MCP_HTTP_TIMEOUT", "120"))
DEFAULT_REASON = "MCP 클라이언트 요청"

server = MCPServer(
    name="usdkrw-assistant",
    instructions=(
        "원/달러 환율(USD/KRW) 일별 데이터(최근 1년, FRED H.10)를 다루는 도구입니다. "
        "숫자는 도구 결과에 있는 값만 쓰고, 환율이 움직인 원인은 이 데이터로 확인할 수 없음을 밝혀 주세요."
    ),
)


async def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(f"{API_BASE_URL}{path}", json=payload)
    except httpx.HTTPError as exc:
        return {"error": f"백엔드({API_BASE_URL})에 연결하지 못했습니다: {type(exc).__name__}"}
    try:
        body = response.json()
    except ValueError:
        return {"error": f"백엔드 응답을 읽지 못했습니다 (HTTP {response.status_code})"}
    if response.status_code >= 400:
        return {"error": body.get("detail", f"HTTP {response.status_code}")}
    return body


async def _tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    body = await _post(f"/api/tools/{name}", arguments)
    return body.get("result", body)


@server.tool(description="저장된 환율 데이터 전체 요약: 기간, 개수, 평균·최고·최저·최신값, 최근 추세, 월별 평균")
async def get_data_summary(reason: str = DEFAULT_REASON) -> dict[str, Any]:
    return await _tool("get_data_summary", {"reason": reason})


@server.tool(description="특정 기간의 날짜별 환율과 그 기간 통계. 날짜는 YYYY-MM-DD 또는 YYYY-MM")
async def get_data_by_range(start_date: str, end_date: str, reason: str = DEFAULT_REASON) -> dict[str, Any]:
    return await _tool("get_data_by_range", {"start_date": start_date, "end_date": end_date, "reason": reason})


@server.tool(description="환율이 가장 높은(desc) 또는 가장 낮은(asc) 날 limit개 (1~10)")
async def get_top_records(order: str = "desc", limit: int = 5, reason: str = DEFAULT_REASON) -> dict[str, Any]:
    return await _tool("get_top_records", {"order": order, "limit": limit, "reason": reason})


@server.tool(description="이동평균, 일간 변동성, 고점 대비 최대 하락, 가장 크게 움직인 날, 월별 변화율")
async def get_statistics(reason: str = DEFAULT_REASON) -> dict[str, Any]:
    return await _tool("get_statistics", {"reason": reason})


@server.tool(description="AI 비서와 나눈 최근 대화 목록 (제목, ID, 날짜)")
async def list_conversations(limit: int = 10, reason: str = DEFAULT_REASON) -> dict[str, Any]:
    return await _tool("list_conversations", {"limit": limit, "reason": reason})


@server.tool(description="대화 ID로 이전 대화 메시지 읽기")
async def get_conversation(conversation_id: str, reason: str = DEFAULT_REASON) -> dict[str, Any]:
    return await _tool("get_conversation", {"conversation_id": conversation_id, "reason": reason})


@server.tool(description="웹 서비스의 AI 비서에게 직접 질문 (데이터 요약 주입 + 대화 자동 저장)")
async def ask_assistant(message: str, conversation_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    body = await _post("/api/chat", payload)
    if "error" in body:
        return body
    return {
        "reply": body.get("reply"),
        "model": body.get("model"),
        "conversation_id": body.get("conversation_id"),
        "tool_calls": body.get("tool_calls", []),
    }


if __name__ == "__main__":
    server.run("stdio")
