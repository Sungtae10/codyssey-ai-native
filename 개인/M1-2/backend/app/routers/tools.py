"""도구 API (보너스): GPT function calling과 같은 도구를 외부 클라이언트(MCP 서버)가 HTTP로 부른다."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Path

from ..container import Container, get_container
from ..errors import NotFoundError
from ..services.tools import TOOL_NAMES

router = APIRouter(prefix="/api/tools", tags=["도구 (Function Calling·MCP)"])


@router.get("", summary="도구 목록과 JSON 스키마")
def list_tools(c: Container = Depends(get_container)) -> dict[str, Any]:
    return {"count": len(TOOL_NAMES), "tools": c.tools.specs()}


@router.post("/{name}", summary="도구 실행 (읽기 전용)")
def run_tool(
    name: str = Path(..., description="도구 이름"),
    arguments: dict[str, Any] = Body(default_factory=dict, examples=[{"start_date": "2026-10-01", "end_date": "2026-10-16", "reason": "10월 값 확인"}]),
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    if name not in TOOL_NAMES:
        raise NotFoundError(f"알 수 없는 도구입니다: {name}")
    result = c.tools.execute(name, arguments)
    return {"tool": name, "ok": "error" not in result, "result": result}
