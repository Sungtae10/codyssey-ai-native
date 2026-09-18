"""raw -> clean 정제 규칙: 필수필드 검증, 텍스트 정규화, 날짜 통일, 결측 처리.

담당: 팀원 B
"""
import logging
import re
from datetime import datetime

log = logging.getLogger(__name__)

REQUIRED = ["url", "title", "body", "category"]
MIN_BODY_LEN = 100
DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z",
    "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y.%m.%d",
]


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)          # HTML 태그 제거
    s = re.sub(r"\s+", " ", s)               # 연속 공백 제거
    return s.strip()


def normalize_date(s: str, fallback: str) -> str:
    """여러 형식을 시도해 YYYY-MM-DD 로 통일. 실패 시 fallback(수집일) 사용."""
    if s:
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return fallback[:10]


def clean_article(raw: dict) -> dict | None:
    """정제된 dict 를 반환. 필수 조건 미달이면 None."""
    for k in REQUIRED:
        if not raw.get(k):
            log.warning("필수 필드 누락(%s) id=%s", k, raw.get("id"))
            return None
    body = normalize_text(raw["body"])
    if len(body) < MIN_BODY_LEN:
        log.warning("본문 길이 부족(%d자) id=%s", len(body), raw.get("id"))
        return None
    return {
        "id": raw["id"],
        "url": raw["url"],
        "title": normalize_text(raw["title"]),
        "body": body,
        "source": raw.get("source"),
        "method": raw.get("method"),
        "category": normalize_text(raw["category"]),
        "published_at": normalize_date(raw.get("published_raw", ""), raw["collected_at"]),
        "collected_at": raw["collected_at"],
    }
