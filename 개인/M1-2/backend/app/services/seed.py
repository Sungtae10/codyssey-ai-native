"""비어 있는 data 컬렉션에 초기 데이터(CSV 251개)를 한 번 올린다.

Render에서 SEED_IF_EMPTY=true로 켜 두면, 서버가 켜질 때 Firestore의 data 컬렉션이
완전히 비어 있는 경우에만 CSV를 올린다. 그래서 내 컴퓨터에서 seed 스크립트를 따로 돌리지 않아도
배포 직후 251개가 들어 있다. 문서가 하나라도 있으면 아무것도 하지 않는다 (화면에서 고친 값을 덮어쓰지 않음).
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..config import Settings
from ..database import StoreProvider, read_seed_csv

logger = logging.getLogger("app.seed")


def seed_if_empty(provider: StoreProvider, settings: Settings) -> int:
    """비어 있으면 CSV를 올리고 올린 개수를 돌려준다. 꺼져 있거나 이미 있으면 0.

    저장소에 문제가 있어도 예외를 밖으로 내보내지 않는다. 서버는 그대로 켜지고,
    원인은 /health와 Render 로그에서 확인한다.
    """
    if not settings.seed_if_empty:
        return 0
    csv_path = settings.seed_csv
    if not csv_path or not Path(csv_path).is_file():
        logger.warning("[seed] CSV 파일이 없어 건너뜁니다: %s", csv_path)
        return 0
    collection = settings.data_collection
    try:
        store = provider.get()
        if store.list_documents(collection, limit=1):
            logger.info("[seed] '%s' 컬렉션에 이미 문서가 있어 건너뜁니다", collection)
            return 0
        written = store.batch_create(collection, read_seed_csv(csv_path))
    except Exception as exc:  # noqa: BLE001
        reason = getattr(exc, "message", None) or type(exc).__name__
        logger.warning("[seed] 초기 데이터를 올리지 못했습니다: %s", reason)
        return 0
    logger.info("[seed] '%s' 컬렉션이 비어 있어 %d개를 올렸습니다", collection, written)
    return written
