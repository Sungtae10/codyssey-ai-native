"""데이터 서비스: CRUD 규칙 + 요약/통계 계산.

- 같은 날짜는 하나만 저장한다 (시계열에서 하루에 값이 둘이면 추세 계산이 틀어지므로). 중복이면 409.
  중복 확인은 캐시가 아니라 저장소에서 그 날짜만 바로 찾아보고, 확인과 쓰기를 잠금 안에서 한 번에 한다.
- Firestore 읽기 횟수를 아끼려고 전체 목록을 잠시(기본 60초) 메모리에 들고 있고,
  추가·수정·삭제가 일어나면 바로 비운다. 동시에 여러 요청이 와도 저장소 전체 읽기는 한 번만 한다.
"""
from __future__ import annotations

import csv
import io
import threading
import time
from typing import Any, Callable

from ..config import Settings
from ..database import utc_now_iso
from ..errors import ConflictError, NotFoundError
from ..repositories.base import DocumentStore
from ..schemas.data import DataCreate, DataUpdate
from . import analysis


def _to_record(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": doc["id"],
        "date": str(doc.get("date", "")),
        "value": float(doc.get("value", 0.0)),
        "memo": doc.get("memo", "") or "",
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


class DataService:
    def __init__(self, store_getter: Callable[[], DocumentStore], settings: Settings) -> None:
        self._store = store_getter
        self._settings = settings
        self._collection = settings.data_collection
        self._cache: list[dict[str, Any]] | None = None
        self._cache_at = 0.0
        self._generation = 0  # 쓰기가 일어날 때마다 1씩 올림 (오래된 읽기 결과가 캐시에 들어가지 않게)
        self._lock = threading.Lock()  # 캐시 값 보호
        self._refill_lock = threading.Lock()  # 저장소 전체 읽기는 한 번에 한 요청만
        self._write_lock = threading.Lock()  # 날짜 중복 확인 + 쓰기를 한 덩어리로

    # ---------- 내부 ----------
    def _fresh(self) -> bool:
        ttl = self._settings.data_cache_seconds
        return self._cache is not None and (time.monotonic() - self._cache_at) < ttl

    def _all(self) -> list[dict[str, Any]]:
        with self._lock:
            if self._fresh():
                return list(self._cache)
        with self._refill_lock:
            with self._lock:
                if self._fresh():  # 기다리는 동안 다른 요청이 이미 채웠으면 그대로 씀
                    return list(self._cache)
                generation = self._generation
            docs = self._store().list_documents(self._collection, order_by="date")
            records = analysis.sort_records(_to_record(d) for d in docs if d.get("date"))
            with self._lock:
                if generation == self._generation:  # 읽는 사이 쓰기가 있었으면 캐시에 넣지 않음
                    self._cache = records
                    self._cache_at = time.monotonic()
            return list(records)

    def invalidate(self) -> None:
        with self._lock:
            self._cache = None
            self._generation += 1

    def _dataset(self) -> dict[str, str]:
        s = self._settings
        return {"name": s.dataset_name, "unit": s.dataset_unit, "source": s.dataset_source}

    def _ensure_unique_date(self, store: DocumentStore, date_str: str, exclude_id: str | None = None) -> None:
        # 캐시가 아니라 저장소에서 그 날짜 문서만 찾는다 (Firestore 읽기 1~2건)
        for doc in store.find_documents(self._collection, "date", date_str):
            if doc["id"] != exclude_id:
                raise ConflictError(f"{date_str} 날짜의 데이터가 이미 있습니다. 목록에서 수정하세요.")

    # ---------- CRUD ----------
    def list(
        self,
        start: str | None = None,
        end: str | None = None,
        order: str = "asc",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        items = [r for r in self._all() if (not start or r["date"] >= start) and (not end or r["date"] <= end)]
        if order == "desc":
            items.reverse()
        if limit is not None:
            items = items[:limit]
        return items

    def create(self, payload: DataCreate) -> dict[str, Any]:
        date_str = payload.date.isoformat()
        store = self._store()
        with self._write_lock:
            self._ensure_unique_date(store, date_str)
            now = utc_now_iso()
            doc = store.create_document(
                self._collection,
                {"date": date_str, "value": payload.value, "memo": payload.memo, "created_at": now, "updated_at": now},
            )
            self.invalidate()
        return _to_record(doc)

    def update(self, record_id: str, payload: DataUpdate) -> dict[str, Any]:
        store = self._store()
        with self._write_lock:
            if store.get_document(self._collection, record_id) is None:
                raise NotFoundError(f"id={record_id} 데이터를 찾지 못했습니다.")
            changes: dict[str, Any] = {}
            if payload.date is not None:
                changes["date"] = payload.date.isoformat()
                self._ensure_unique_date(store, changes["date"], exclude_id=record_id)
            if payload.value is not None:
                changes["value"] = payload.value
            if payload.memo is not None:
                changes["memo"] = payload.memo
            changes["updated_at"] = utc_now_iso()
            doc = store.update_document(self._collection, record_id, changes)
            self.invalidate()
        if doc is None:
            raise NotFoundError(f"id={record_id} 데이터를 찾지 못했습니다.")
        return _to_record(doc)

    def delete(self, record_id: str) -> None:
        store = self._store()
        with self._write_lock:
            deleted = store.delete_document(self._collection, record_id)
            self.invalidate()
        if not deleted:
            raise NotFoundError(f"id={record_id} 데이터를 찾지 못했습니다.")

    # ---------- 분석 ----------
    def summary(self) -> dict[str, Any]:
        s = self._settings
        return analysis.compute_summary(
            self._all(), self._dataset(), trend_window=s.trend_window, threshold_pct=s.trend_threshold_pct
        )

    def statistics(self) -> dict[str, Any]:
        return analysis.compute_statistics(self._all())

    def range_report(self, start: str, end: str, max_rows: int = 62) -> dict[str, Any]:
        rows = self.list(start=start, end=end)
        report: dict[str, Any] = {"start": start, "end": end, **analysis.range_stats(rows)}
        if len(rows) <= max_rows:
            report["records"] = [{"date": r["date"], "value": r["value"], "memo": r["memo"]} for r in rows]
        else:
            report["records_omitted"] = True
            report["note"] = f"{len(rows)}개라 원본 대신 통계와 월별 요약만 줍니다."
            report["monthly"] = analysis.monthly_stats(rows)
        return report

    def top(self, order: str = "desc", limit: int = 5) -> list[dict[str, Any]]:
        return analysis.top_records(self._all(), order=order, limit=limit)

    # ---------- 내보내기 (보너스) ----------
    def export_rows(self) -> list[dict[str, Any]]:
        return [{"date": r["date"], "value": r["value"], "memo": r["memo"]} for r in self._all()]

    def export_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["date", "value", "memo"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(self.export_rows())
        # 엑셀에서 한글이 깨지지 않도록 BOM을 붙인다
        return "﻿" + buf.getvalue()
