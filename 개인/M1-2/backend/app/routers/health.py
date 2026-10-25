"""상태 확인 API. 프론트엔드는 처음 열 때 /health를 불러 Render 무료 서버를 깨운다."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..container import Container, get_container
from ..database import utc_now_iso

router = APIRouter(tags=["상태"])


@router.get("/", summary="서비스 안내")
def root() -> dict[str, str]:
    return {"service": "나만의 AI 비서 API (USD/KRW)", "docs": "/docs", "health": "/health"}


@router.get("/health", summary="서버 상태 (저장소 연결, OpenAI 설정 여부)")
def health(c: Container = Depends(get_container)) -> dict[str, Any]:
    storage = c.store.status()
    s = c.settings
    return {
        "status": "ok" if storage["ready"] else "degraded",
        "storage": storage,
        "openai": {
            "configured": s.openai_configured,
            "model": s.openai_model,
            "fallback_model": s.openai_fallback_model,
            "tools_enabled": s.enable_tools,
        },
        "time": utc_now_iso(),
    }
