"""환경 변수를 한곳에서 읽어 Settings 객체로 만든다.

키(OPENAI_API_KEY, FIREBASE_SERVICE_ACCOUNT_JSON)는 코드에 쓰지 않고 환경 변수로만 받는다.
로컬에서는 backend/.env 파일을 python-dotenv가 읽는다 (.env는 Git에 올리지 않는다).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _str(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = _str(name)
    try:
        value = int(raw) if raw is not None else default
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _float(name: str, default: float | None) -> float | None:
    raw = _str(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    raw = _str(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _list(name: str, default: str) -> list[str]:
    raw = _str(name, default) or ""
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # 저장소: firestore(배포 기본값) 또는 memory(테스트, 키 없이 화면 미리보기)
    storage_backend: str = "firestore"
    firebase_service_account_json: str | None = None
    firebase_service_account_path: str | None = None
    firestore_database_id: str | None = None
    data_collection: str = "data"
    conversations_collection: str = "conversations"
    memory_seed_csv: str | None = str(BACKEND_DIR / "data" / "usdkrw_daily.csv")
    # 서버가 켜질 때 data 컬렉션이 완전히 비어 있으면 이 CSV를 한 번 올린다 (render.yaml에서 true)
    seed_if_empty: bool = False
    seed_csv: str | None = str(BACKEND_DIR / "data" / "usdkrw_daily.csv")

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-6-luna"
    openai_fallback_model: str | None = "gpt-4o-mini"
    openai_reasoning_effort: str | None = "none"
    openai_max_tokens: int = 700
    openai_temperature: float | None = None
    openai_timeout_seconds: int = 60
    openai_base_url: str | None = None

    # 채팅 동작과 비용 보호
    enable_tools: bool = True
    max_tool_rounds: int = 3
    history_messages: int = 10
    chat_rate_limit_per_minute: int = 10
    chat_daily_limit: int = 300
    chat_global_rate_limit_per_minute: int = 30
    chat_daily_limit_per_ip: int = 100
    chat_deadline_seconds: int = 75

    # CORS
    allowed_origins: list[str] = field(default_factory=list)
    allowed_origin_regex: str | None = None

    # 데이터 설명 (시스템 프롬프트에 들어감)
    dataset_name: str = "원/달러 환율 (USD/KRW)"
    dataset_unit: str = "원"
    dataset_source: str = "미국 연방준비제도 H.10 (FRED DEXKOUS, 뉴욕 정오 매입환율)"
    trend_window: int = 20
    trend_threshold_pct: float = 0.5
    data_cache_seconds: int = 60

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key)


def load_settings() -> Settings:
    """현재 환경 변수로 Settings를 만든다. 테스트는 Settings(...)를 직접 만들어 넘긴다."""
    backend = (_str("STORAGE_BACKEND", "firestore") or "firestore").lower()
    if backend not in {"firestore", "memory"}:
        backend = "firestore"
    effort = _str("OPENAI_REASONING_EFFORT", "none")
    if effort and effort.lower() in {"off", "unset", "default"}:
        effort = None
    return Settings(
        storage_backend=backend,
        firebase_service_account_json=_str("FIREBASE_SERVICE_ACCOUNT_JSON"),
        firebase_service_account_path=_str("FIREBASE_SERVICE_ACCOUNT_PATH")
        or _str("GOOGLE_APPLICATION_CREDENTIALS"),
        firestore_database_id=_str("FIRESTORE_DATABASE_ID"),
        data_collection=_str("DATA_COLLECTION", "data") or "data",
        conversations_collection=_str("CONVERSATIONS_COLLECTION", "conversations") or "conversations",
        memory_seed_csv=_str("MEMORY_SEED_CSV", str(BACKEND_DIR / "data" / "usdkrw_daily.csv")),
        seed_if_empty=_bool("SEED_IF_EMPTY", False),
        seed_csv=_str("SEED_CSV", str(BACKEND_DIR / "data" / "usdkrw_daily.csv")),
        openai_api_key=_str("OPENAI_API_KEY"),
        openai_model=_str("OPENAI_MODEL", "gpt-6-luna") or "gpt-6-luna",
        openai_fallback_model=_str("OPENAI_FALLBACK_MODEL", "gpt-4o-mini"),
        openai_reasoning_effort=effort,
        openai_max_tokens=_int("OPENAI_MAX_TOKENS", 700, 100, 4000),
        openai_temperature=_float("OPENAI_TEMPERATURE", None),
        openai_timeout_seconds=_int("OPENAI_TIMEOUT_SECONDS", 60, 5, 300),
        openai_base_url=_str("OPENAI_BASE_URL"),
        enable_tools=_bool("ENABLE_TOOLS", True),
        max_tool_rounds=_int("MAX_TOOL_ROUNDS", 3, 1, 5),
        history_messages=_int("HISTORY_MESSAGES", 10, 0, 40),
        chat_rate_limit_per_minute=_int("CHAT_RATE_LIMIT_PER_MINUTE", 10, 1, 120),
        chat_daily_limit=_int("CHAT_DAILY_LIMIT", 300, 1, 100000),
        chat_global_rate_limit_per_minute=_int("CHAT_GLOBAL_RATE_LIMIT_PER_MINUTE", 30, 1, 1000),
        chat_daily_limit_per_ip=_int("CHAT_DAILY_LIMIT_PER_IP", 100, 1, 100000),
        chat_deadline_seconds=_int("CHAT_DEADLINE_SECONDS", 75, 20, 300),
        allowed_origins=_list(
            "ALLOWED_ORIGINS",
            "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,http://127.0.0.1:3000",
        ),
        allowed_origin_regex=_str("ALLOWED_ORIGIN_REGEX"),
        dataset_name=_str("DATASET_NAME", "원/달러 환율 (USD/KRW)") or "원/달러 환율 (USD/KRW)",
        dataset_unit=_str("DATASET_UNIT", "원") or "원",
        dataset_source=_str(
            "DATASET_SOURCE", "미국 연방준비제도 H.10 (FRED DEXKOUS, 뉴욕 정오 매입환율)"
        )
        or "미국 연방준비제도 H.10",
        trend_window=_int("TREND_WINDOW", 20, 3, 120),
        trend_threshold_pct=_float("TREND_THRESHOLD_PCT", 0.5) or 0.5,
        data_cache_seconds=_int("DATA_CACHE_SECONDS", 60, 0, 3600),
    )
