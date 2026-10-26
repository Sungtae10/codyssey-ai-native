"""FastAPI 앱 조립: CORS, 예외 처리, 라우터 등록."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .config import Settings, load_settings
from .container import build_container
from .errors import AppError
from .repositories.base import DocumentStore
from .routers import chat, conversations, data, health, tools
from .services.seed import seed_if_empty

logger = logging.getLogger("app")

DESCRIPTION = """
**내 데이터를 아는 AI 비서**: 원/달러 환율(USD/KRW) 시계열을 Firestore에 저장하고,
데이터 요약을 GPT 시스템 프롬프트에 넣어(컨텍스트 주입) 맞춤형 답을 줍니다.

- 데이터 API: `POST/GET /api/data`, `PUT/DELETE /api/data/{id}`, `GET /api/data/summary`
- 대화 기록 API: `POST/GET /api/conversations`, `GET/DELETE /api/conversations/{id}`
- AI 채팅: `POST /api/chat` (요약 조회 → 프롬프트 주입 → GPT 호출 → 자동 저장)
- 보너스: `GET /api/data/statistics`, `GET /api/data/export`, `GET/POST /api/tools` (Function Calling·MCP)

Render 무료 서버는 15분 동안 요청이 없으면 잠들어, 첫 요청이 1분 정도 걸릴 수 있습니다.
"""

TAGS = [
    {"name": "데이터", "description": "시계열 데이터 CRUD와 요약"},
    {"name": "대화 기록", "description": "대화 저장, 목록, 불러오기, 삭제"},
    {"name": "AI 채팅", "description": "데이터 요약을 주입한 GPT 대화"},
    {"name": "도구 (Function Calling·MCP)", "description": "GPT와 외부 클라이언트가 함께 쓰는 읽기 전용 도구"},
    {"name": "상태", "description": "서버 상태 확인"},
]


def _first_error_message(errors: list[dict[str, Any]]) -> str:
    if not errors:
        return "입력값을 확인하세요."
    err = errors[0]
    loc = ".".join(str(part) for part in err.get("loc", []) if part not in ("body", "query", "path"))
    msg = str(err.get("msg", "")).replace("Value error, ", "")
    return f"입력값을 확인하세요: {loc} ({msg})" if loc else f"입력값을 확인하세요: {msg}"


def create_app(
    settings: Settings | None = None,
    store: DocumentStore | None = None,
    llm: Any | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    container = build_container(settings, store=store, llm=llm)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # SEED_IF_EMPTY=true(Render 설정)이면 서버가 켜질 때 data 컬렉션이 완전히 비어 있는 경우에만
        # CSV 251개를 올린다. 실패해도 서버는 켜지고, 원인은 /health와 로그에 남는다.
        if settings.seed_if_empty and await run_in_threadpool(seed_if_empty, container.store, settings):
            container.data.invalidate()
        yield

    app = FastAPI(
        title="나만의 AI 비서 API (USD/KRW)",
        description=DESCRIPTION,
        version="1.0.0",
        openapi_tags=TAGS,
        lifespan=lifespan,
    )
    app.state.container = container

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = jsonable_encoder(exc.errors())
        return JSONResponse(status_code=422, content={"detail": _first_error_message(errors), "errors": errors})

    # 예상하지 못한 오류도 CORS 헤더가 붙은 JSON으로 돌려주려고, CORS보다 안쪽에 둔다.
    @app.middleware("http")
    async def _catch_all(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:  # noqa: BLE001
            logger.exception("처리하지 못한 오류: %s %s", request.method, request.url.path)
            return JSONResponse(status_code=500, content={"detail": "서버 내부 오류가 발생했습니다."})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=settings.allowed_origin_regex,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    for module in (health, data, conversations, chat, tools):
        app.include_router(module.router)
    return app
