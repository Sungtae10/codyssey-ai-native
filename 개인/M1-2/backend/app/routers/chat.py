"""AI 채팅 API (컨텍스트 주입 + 자동 저장)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..container import Container, get_container
from ..schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["AI 채팅"])


def client_ip(request: Request) -> str:
    """요청자 IP (요청 제한용, 최선 노력).
    앞단 프록시(Cloudflare)가 덮어쓰는 헤더를 먼저 보고, 없으면 X-Forwarded-For의 첫 주소를 쓴다.
    헤더는 사용자가 바꿀 수 있으므로, 비용 상한은 IP와 관계없는 서버 전체 제한이 맡는다 (rate_limit.py)."""
    for header in ("cf-connecting-ip", "true-client-ip"):
        value = request.headers.get(header, "").strip()
        if value:
            return value
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="AI 대화 (데이터 요약을 시스템 프롬프트에 주입)",
    description="① 데이터 요약 조회 → ② 시스템 프롬프트에 삽입 → ③ GPT 호출(필요하면 도구 호출) → "
    "④ conversations에 자동 저장. conversation_id를 주면 그 대화에 이어서 저장합니다.",
)
def chat(payload: ChatRequest, request: Request, c: Container = Depends(get_container)):
    c.limiter.check(client_ip(request))
    return c.chat.chat(payload)
