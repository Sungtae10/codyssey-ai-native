"""데이터 API의 요청·응답 모델 (Pydantic).

요청 모델은 들어오는 값을 검사한다: 날짜 형식과 범위(미래 금지), 숫자(0보다 큼, 무한대·NaN·true/false·문자 금지), 메모 길이.
검사에 걸리면 FastAPI가 422 응답을 돌려주므로, 잘못된 값이 Firestore에 저장되지 않는다.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

KST = dt.timezone(dt.timedelta(hours=9))
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
MIN_DATE = dt.date(1900, 1, 1)


def clean_text(value: str) -> str:
    return _CONTROL_CHARS.sub("", value).strip()


def check_date(value: dt.date) -> dt.date:
    # 한국 시간 기준 오늘까지만 허용 (환율은 아직 오지 않은 날의 값이 있을 수 없음)
    today = dt.datetime.now(KST).date()
    if value < MIN_DATE:
        raise ValueError("1900-01-01 이후 날짜만 입력할 수 있습니다.")
    if value > today:
        raise ValueError(f"미래 날짜는 입력할 수 없습니다 (오늘 {today.isoformat()}까지).")
    return value


def check_number(value: object) -> object:
    """JSON 숫자만 받는다. true/false나 "1334" 같은 문자는 숫자로 바꾸지 않고 거절한다."""
    if value is None:
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value는 숫자여야 합니다 (예: 1334.03).")
    return value


class DataCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"date": "2026-10-16", "value": 1334.03, "memo": "직접 입력 예시"}]}
    )

    date: dt.date = Field(..., description="날짜 (YYYY-MM-DD). 하루에 값은 하나만 저장합니다.")
    value: float = Field(..., gt=0, le=1e7, allow_inf_nan=False, description="값 (0보다 큰 숫자, 원/달러 환율)")
    memo: str = Field("", max_length=200, description="메모 (최대 200자)")

    @field_validator("date")
    @classmethod
    def _date_range(cls, v: dt.date) -> dt.date:
        return check_date(v)

    @field_validator("value", mode="before")
    @classmethod
    def _value_type(cls, v: object) -> object:
        return check_number(v)

    @field_validator("memo")
    @classmethod
    def _memo(cls, v: str) -> str:
        return clean_text(v)


class DataUpdate(BaseModel):
    """바꿀 항목만 보내면 된다. 하나도 없으면 422."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"value": 1335.5, "memo": "값 수정 예시"}]})

    date: dt.date | None = Field(None, description="날짜 (YYYY-MM-DD)")
    value: float | None = Field(None, gt=0, le=1e7, allow_inf_nan=False, description="값 (0보다 큰 숫자)")
    memo: str | None = Field(None, max_length=200, description="메모 (최대 200자)")

    @field_validator("date")
    @classmethod
    def _date_range(cls, v: dt.date | None) -> dt.date | None:
        return check_date(v) if v is not None else v

    @field_validator("value", mode="before")
    @classmethod
    def _value_type(cls, v: object) -> object:
        return check_number(v)

    @field_validator("memo")
    @classmethod
    def _memo(cls, v: str | None) -> str | None:
        return clean_text(v) if v is not None else v

    @model_validator(mode="after")
    def _at_least_one(self) -> "DataUpdate":
        if self.date is None and self.value is None and self.memo is None:
            raise ValueError("date, value, memo 중 하나 이상을 보내야 합니다.")
        return self


class DataRecord(BaseModel):
    id: str
    date: str
    value: float
    memo: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class DataListResponse(BaseModel):
    count: int
    items: list[DataRecord]


class DeleteResponse(BaseModel):
    id: str
    deleted: bool = True


class DataPoint(BaseModel):
    date: str
    value: float


class DatasetInfo(BaseModel):
    name: str
    unit: str
    source: str


class SummaryMetrics(BaseModel):
    average: float
    max: float
    max_date: str
    min: float
    min_date: str
    latest: float
    latest_date: str
    first: float
    first_date: str
    change: float = Field(..., description="기간 첫 값 대비 마지막 값의 차이")
    change_pct: float = Field(..., description="기간 첫 값 대비 마지막 값의 변화율(%)")
    std: float = Field(..., description="표준편차")


class TrendInfo(BaseModel):
    direction: Literal["상승", "하락", "보합"]
    window: int = Field(..., description="비교에 쓴 개수 (최근 N개 vs 직전 N개)")
    recent_average: float
    previous_average: float
    change_pct: float
    slope_per_point: float = Field(..., description="최근 N개 값의 직선 기울기 (한 칸당 변화량)")
    threshold_pct: float


class MonthlyStat(BaseModel):
    month: str
    count: int
    average: float
    min: float
    max: float
    first: float
    last: float
    change_pct: float | None = Field(None, description="직전 달 마지막 값 대비 이번 달 마지막 값 변화율(%)")


class SummaryResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "dataset": {"name": "원/달러 환율 (USD/KRW)", "unit": "원", "source": "FRED H.10"},
                    "period": "2025-10-16 ~ 2026-10-16",
                    "start_date": "2025-10-16",
                    "end_date": "2026-10-16",
                    "count": 251,
                    "metrics": {
                        "average": 1454.44,
                        "max": 1555.96,
                        "max_date": "2026-06-05",
                        "min": 1334.03,
                        "min_date": "2026-10-16",
                        "latest": 1334.03,
                        "latest_date": "2026-10-16",
                        "first": 1416.07,
                        "first_date": "2025-10-16",
                        "change": -82.04,
                        "change_pct": -5.79,
                        "std": 51.88,
                    },
                    "trend": "하락 (최근 20개 평균 1,353.11원, 직전 20개 평균 대비 -0.94%)",
                }
            ]
        }
    )

    dataset: DatasetInfo
    period: str
    start_date: str | None
    end_date: str | None
    count: int
    metrics: SummaryMetrics | None
    trend: str
    trend_detail: TrendInfo | None
    monthly: list[MonthlyStat]
    recent: list[DataPoint]
    generated_at: str


class DailyMove(BaseModel):
    date: str
    value: float
    change: float
    change_pct: float


class PriceRun(BaseModel):
    """구간 변동: 하락이면 start=고점, end=그 뒤 저점 / 상승이면 start=저점, end=그 뒤 고점."""

    pct: float
    start_date: str
    start_value: float
    end_date: str
    end_value: float


class StatisticsResponse(BaseModel):
    count: int
    period: str
    moving_averages: dict[str, float | None]
    latest_vs_ma20_pct: float | None
    volatility: dict[str, float | None]
    max_drawdown: PriceRun | None = Field(None, description="고점 대비 최대 하락률(%)")
    max_rally: PriceRun | None = Field(None, description="저점 대비 최대 상승률(%)")
    quartiles: dict[str, float | None]
    top_rises: list[DailyMove]
    top_falls: list[DailyMove]
    up_days: int
    down_days: int
    flat_days: int
    monthly: list[MonthlyStat]
    generated_at: str
