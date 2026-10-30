"""
seed_firestore.py
data/usdkrw_daily.csv(251개)를 Firestore의 data 컬렉션에 올린다.

준비: backend/.env에 FIREBASE_SERVICE_ACCOUNT_JSON(또는 FIREBASE_SERVICE_ACCOUNT_PATH)을 넣는다.

실행 (backend 폴더에서)
    python scripts/seed_firestore.py            # 없는 날짜만 추가 (여러 번 실행해도 중복 없음)
    python scripts/seed_firestore.py --reset    # data 컬렉션을 비우고 다시 251개 올림
    python scripts/seed_firestore.py --dry-run  # 무엇을 할지 숫자만 보여 주고 쓰지 않음

Firestore 무료 한도(하루 쓰기 2만 건) 안에서 251건 쓰기면 충분하다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import load_settings  # noqa: E402
from app.database import StoreProvider, read_seed_csv  # noqa: E402
from app.errors import StorageUnavailableError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="CSV를 Firestore data 컬렉션에 올리기")
    parser.add_argument("--csv", default=str(BACKEND_DIR / "data" / "usdkrw_daily.csv"))
    parser.add_argument("--reset", action="store_true", help="기존 문서를 모두 지우고 다시 올림")
    parser.add_argument("--dry-run", action="store_true", help="쓰지 않고 계획만 출력")
    args = parser.parse_args()

    settings = load_settings()
    if settings.storage_backend != "firestore":
        print("STORAGE_BACKEND=firestore 일 때만 실행합니다 (.env 확인).", file=sys.stderr)
        return 1
    try:
        store = StoreProvider(settings).get()
    except StorageUnavailableError as exc:
        print(f"Firestore 연결 실패: {exc.message}", file=sys.stderr)
        return 1

    collection = settings.data_collection
    rows = read_seed_csv(args.csv)
    existing = store.list_documents(collection)
    print(f"[1/3] CSV {len(rows)}개, Firestore '{collection}' 컬렉션 기존 문서 {len(existing)}개")

    if args.reset:
        to_add = rows
        print(f"[2/3] --reset: 기존 {len(existing)}개를 지우고 {len(to_add)}개를 올립니다")
    else:
        have = {str(d.get("date")) for d in existing}
        to_add = [r for r in rows if r["date"] not in have]
        print(f"[2/3] 이미 있는 날짜 {len(rows) - len(to_add)}개는 건너뛰고 {len(to_add)}개를 올립니다")

    if args.dry_run:
        print("[3/3] --dry-run: 아무것도 쓰지 않았습니다")
        return 0
    if args.reset and existing:
        store.delete_many(collection, [d["id"] for d in existing])
    written = store.batch_create(collection, to_add) if to_add else 0
    total = len(store.list_documents(collection))
    print(f"[3/3] 완료: {written}개 추가, 현재 '{collection}' 문서 {total}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
