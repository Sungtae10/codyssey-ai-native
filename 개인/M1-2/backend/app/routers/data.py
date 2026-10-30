"""데이터 API: CRUD 4개 + 요약 1개 (+ 보너스: 통계, 내보내기).

주의: /summary, /statistics, /export를 /{record_id}보다 먼저 선언해 경로가 겹치지 않게 한다.
"""
from __future__ import annotations

import datetime as dt
import json
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query, Response, status

from ..container import Container, get_container
from ..schemas.chat import ID_PATTERN
from ..schemas.data import (
    DataCreate,
    DataListResponse,
    DataRecord,
    DataUpdate,
    DeleteResponse,
    StatisticsResponse,
    SummaryResponse,
)

router = APIRouter(prefix="/api/data", tags=["데이터"])


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="데이터 요약 (프롬프트 주입용)",
    description="기간, 개수, 평균·최고·최저·최신값, 최근 추세(최근 20개 평균 vs 직전 20개 평균), 월별 요약. "
    "/api/chat도 매 질문마다 같은 함수로 요약을 만들어 시스템 프롬프트에 넣습니다.",
)
def get_summary(c: Container = Depends(get_container)):
    return c.data.summary()


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    summary="확장 통계 (보너스)",
    description="이동평균(5·20·60), 일간 변동성, 고점 대비 최대 하락, 저점 대비 최대 상승, 큰 변동일, 월별 변화율.",
)
def get_statistics(c: Container = Depends(get_container)):
    return c.data.statistics()


@router.get("/export", summary="데이터 내보내기 CSV/JSON (보너스)")
def export_data(
    format: Literal["csv", "json"] = Query("csv", description="csv 또는 json"),
    c: Container = Depends(get_container),
):
    stamp = dt.date.today().strftime("%Y%m%d")
    if format == "json":
        body = json.dumps(c.data.export_rows(), ensure_ascii=False, indent=2)
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="usdkrw_data_{stamp}.json"'},
        )
    return Response(
        content=c.data.export_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="usdkrw_data_{stamp}.csv"'},
    )


@router.get("", response_model=DataListResponse, summary="데이터 목록 조회")
def list_data(
    start: dt.date | None = Query(None, description="시작일 (YYYY-MM-DD, 포함)"),
    end: dt.date | None = Query(None, description="종료일 (YYYY-MM-DD, 포함)"),
    order: Literal["asc", "desc"] = Query("asc", description="날짜 정렬"),
    limit: int | None = Query(None, ge=1, le=5000, description="최대 개수"),
    c: Container = Depends(get_container),
):
    items = c.data.list(
        start=start.isoformat() if start else None,
        end=end.isoformat() if end else None,
        order=order,
        limit=limit,
    )
    return {"count": len(items), "items": items}


@router.post("", response_model=DataRecord, status_code=status.HTTP_201_CREATED, summary="새 데이터 추가")
def create_data(payload: DataCreate, c: Container = Depends(get_container)):
    return c.data.create(payload)


@router.put("/{record_id}", response_model=DataRecord, summary="데이터 수정")
def update_data(
    payload: DataUpdate,
    record_id: str = Path(..., pattern=ID_PATTERN, description="데이터 ID"),
    c: Container = Depends(get_container),
):
    return c.data.update(record_id, payload)


@router.delete("/{record_id}", response_model=DeleteResponse, summary="데이터 삭제")
def delete_data(
    record_id: str = Path(..., pattern=ID_PATTERN, description="데이터 ID"),
    c: Container = Depends(get_container),
):
    c.data.delete(record_id)
    return {"id": record_id, "deleted": True}
