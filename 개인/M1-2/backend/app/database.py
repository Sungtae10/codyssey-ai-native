"""저장소 연결을 만든다.

- firestore: FIREBASE_SERVICE_ACCOUNT_JSON(서비스 계정 키 JSON 전체 문자열, 또는 base64) 또는
  FIREBASE_SERVICE_ACCOUNT_PATH(키 파일 경로)로 firebase-admin을 초기화한다.
- memory: 키 없이 실행. data/usdkrw_daily.csv를 읽어 채운다 (테스트와 화면 미리보기용).

연결은 첫 요청 때 한 번 만든다. 설정이 잘못되어도 서버는 켜지고, /health와 각 API가
"무엇을 고치면 되는지" 한국어로 알려 준다 (503).
"""
from __future__ import annotations

import base64
import binascii
import csv
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import BACKEND_DIR, Settings
from .errors import StorageUnavailableError
from .repositories.base import DocumentStore
from .repositories.memory_store import MemoryStore

logger = logging.getLogger(__name__)

_REQUIRED_KEYS = ("type", "project_id", "private_key", "client_email")


def utc_now_iso() -> str:
    # 밀리초까지 남겨 같은 초에 저장된 대화도 최근 순서가 정확히 갈리게 한다 (문자열 정렬 = 시간 정렬)
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def load_service_account_info(settings: Settings) -> dict[str, Any]:
    """환경 변수에서 서비스 계정 키(JSON)를 읽어 dict로 돌려준다. 키 값은 로그에 남기지 않는다."""
    raw = settings.firebase_service_account_json
    if raw:
        text = raw.strip()
        if not text.startswith("{"):
            try:  # base64로 넣은 경우
                text = base64.b64decode(text, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError) as exc:
                raise StorageUnavailableError(
                    "FIREBASE_SERVICE_ACCOUNT_JSON 형식이 올바르지 않습니다. "
                    "키 파일(.json)의 내용 전체를 { 부터 } 까지 그대로 붙여 넣으세요."
                ) from exc
        try:
            info = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StorageUnavailableError(
                "FIREBASE_SERVICE_ACCOUNT_JSON을 JSON으로 읽지 못했습니다. "
                "중괄호 { } 를 포함한 키 파일 내용 전체를 한 번에 붙여 넣었는지 확인하세요."
            ) from exc
    elif settings.firebase_service_account_path:
        path = Path(settings.firebase_service_account_path).expanduser()
        if not path.is_absolute():  # 상대 경로는 backend 폴더 기준
            path = BACKEND_DIR / path
        if not path.is_file():
            raise StorageUnavailableError(f"서비스 계정 키 파일을 찾지 못했습니다: {path.name}")
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageUnavailableError("서비스 계정 키 파일을 읽지 못했습니다.") from exc
    else:
        raise StorageUnavailableError(
            "Firestore 연결 정보가 없습니다. 환경 변수 FIREBASE_SERVICE_ACCOUNT_JSON에 "
            "서비스 계정 키(JSON) 내용을 넣으세요. 키 없이 화면만 보려면 STORAGE_BACKEND=memory로 실행하세요."
        )

    if not isinstance(info, dict):
        raise StorageUnavailableError("서비스 계정 키는 JSON 객체여야 합니다.")
    missing = [key for key in _REQUIRED_KEYS if not info.get(key)]
    if missing or info.get("type") != "service_account":
        raise StorageUnavailableError(
            "서비스 계정 키가 아닙니다. Firebase 콘솔 > 프로젝트 설정 > 서비스 계정 > "
            "'새 비공개 키 생성'으로 받은 파일을 쓰세요. (빠진 항목: "
            + (", ".join(missing) if missing else "type") + ")"
        )
    # 환경 변수에 붙여 넣는 과정에서 줄바꿈이 \\n 글자로 남은 경우를 고친다.
    if "\\n" in info["private_key"]:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    return info


def _create_firestore_store(settings: Settings) -> DocumentStore:
    info = load_service_account_info(settings)
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError as exc:  # requirements.txt 설치 누락
        raise StorageUnavailableError("firebase-admin 패키지가 설치되지 않았습니다.") from exc

    from .repositories.firestore_store import FirestoreStore

    try:
        try:
            app = firebase_admin.get_app()
        except ValueError:
            app = firebase_admin.initialize_app(credentials.Certificate(info))
        if settings.firestore_database_id:
            client = firestore.client(app=app, database_id=settings.firestore_database_id)
        else:
            client = firestore.client(app=app)
    except Exception as exc:  # 키 내용 오류 등
        logger.exception("Firestore 초기화 실패")
        raise StorageUnavailableError(
            f"Firestore에 연결하지 못했습니다 ({type(exc).__name__}). 서비스 계정 키와 프로젝트를 확인하세요."
        ) from exc
    logger.info("Firestore 연결 준비 완료 (project_id=%s)", info.get("project_id"))
    return FirestoreStore(client)


def read_seed_csv(path: str | Path) -> list[dict[str, Any]]:
    """CSV(date,value,memo)를 읽어 저장할 문서 목록으로 바꾼다."""
    now = utc_now_iso()
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "date": row["date"].strip(),
                    "value": float(row["value"]),
                    "memo": (row.get("memo") or "").strip(),
                    "created_at": now,
                    "updated_at": now,
                }
            )
    return rows


def _create_memory_store(settings: Settings) -> DocumentStore:
    store = MemoryStore()
    seed = settings.memory_seed_csv
    if seed and Path(seed).is_file():
        store.batch_create(settings.data_collection, read_seed_csv(seed))
        logger.info("메모리 저장소에 예시 데이터를 채웠습니다: %s", Path(seed).name)
    return store


class StoreProvider:
    """첫 요청 때 저장소를 한 번 만들고, 실패 이유를 기억해 /health에 보여 준다."""

    def __init__(self, settings: Settings, store: DocumentStore | None = None) -> None:
        self._settings = settings
        self._store = store
        self._error: str | None = None
        self._lock = threading.Lock()
        self._probe_ok_until = 0.0

    @property
    def backend(self) -> str:
        if self._store is not None:
            return self._store.backend_name
        return self._settings.storage_backend

    def get(self) -> DocumentStore:
        if self._store is not None:
            return self._store
        with self._lock:
            if self._store is None:
                try:
                    if self._settings.storage_backend == "memory":
                        self._store = _create_memory_store(self._settings)
                    else:
                        self._store = _create_firestore_store(self._settings)
                    self._error = None
                except StorageUnavailableError as exc:
                    self._error = exc.message
                    raise
        return self._store

    def status(self) -> dict[str, Any]:
        """/health용 상태. 연결을 만든 뒤 문서 1개를 실제로 읽어 확인한다.
        성공하면 60초 동안은 다시 읽지 않는다 (무료 읽기 횟수 절약)."""
        try:
            store = self.get()
            if time.monotonic() >= self._probe_ok_until:
                store.ping(self._settings.data_collection)
                self._probe_ok_until = time.monotonic() + 60
            return {"backend": self.backend, "ready": True, "error": None}
        except StorageUnavailableError as exc:
            return {"backend": self.backend, "ready": False, "error": exc.message}
        except Exception as exc:  # noqa: BLE001  (예상하지 못한 저장소 오류도 상태로 보여 줌)
            logger.warning("저장소 상태 확인 실패: %s", type(exc).__name__)
            return {"backend": self.backend, "ready": False, "error": f"저장소 확인에 실패했습니다 ({type(exc).__name__})."}
