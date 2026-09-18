"""raw -> clean 정제: 필수필드 검증, 텍스트 정규화, 날짜 통일, 결측 처리.

담당: 팀원 B (박수민).
"""
import html
import logging
import re
from datetime import datetime
import email.utils


def normalize_text(s: str) -> str:
    """HTML 엔티티 및 태그를 제거하고 공백을 정규화합니다."""
    if not s:
        return ""
    # HTML 엔티티 변환 (&quot;, &amp; 등)
    text = html.unescape(str(s))
    # HTML 태그 제거
    text = re.sub(r"<[^>]+>", " ", text)
    # 연속 공백 및 줄바꿈 정리
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_date(s: str) -> str:
    """다양한 형식의 날짜 문자열을 YYYY-MM-DD로 변환합니다."""
    if not s:
        return ""
    s_clean = str(s).strip()

    # 1. RFC 2822 (RSS 표준: Wed, 16 Sep 2026 00:11:37 GMT 등)
    try:
        dt = email.utils.parsedate_to_datetime(s_clean)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # 2. ISO 8601
    try:
        dt = datetime.fromisoformat(s_clean.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # 3. 일반적인 날짜 포맷 시도
    date_formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y.%m.%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    )
    for fmt in date_formats:
        try:
            return datetime.strptime(s_clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 4. 정규식을 통한 연-월-일 추출 (한국어 포함)
    m = re.search(r"(\d{4})[-./년]\s*(\d{1,2})[-./월]\s*(\d{1,2})", s_clean)
    if m:
        try:
            year = int(m.group(1))
            month = int(m.group(2))
            day = int(m.group(3))
            return f"{year:04d}-{month:02d}-{day:02d}"
        except Exception:
            pass

    return ""


def clean_article(raw: dict) -> dict | None:
    """raw 기사 딕셔너리를 검증 및 정제하여 clean 기사 딕셔너리로 반환합니다.

    필수 필드 누락이거나 본문이 100자 미만인 경우 None을 반환합니다.
    """
    required_fields = ("url", "title", "body", "category")
    for field in required_fields:
        val = raw.get(field)
        if not val or not str(val).strip():
            logging.warning("필수 필드(%s) 누락으로 기사 제외: url=%s", field, raw.get("url"))
            return None

    # 텍스트 정제
    title = normalize_text(raw.get("title", ""))
    body = normalize_text(raw.get("body", ""))

    if not title:
        logging.warning("정제 후 제목 공백으로 제외: url=%s", raw.get("url"))
        return None

    # 본문 100자 미만 제외 (계획서 요구사항)
    if len(body) < 100:
        logging.warning("본문 길이 부족(%d자 < 100자)으로 제외: url=%s", len(body), raw.get("url"))
        return None

    # 날짜 정규화 (실패 시 collected_at 날짜 사용)
    published_at = normalize_date(raw.get("published_raw", ""))
    if not published_at:
        collected = raw.get("collected_at", "")
        if collected and len(collected) >= 10:
            published_at = collected[:10]
        else:
            published_at = datetime.now().strftime("%Y-%m-%d")

    collected_at = raw.get("collected_at") or datetime.now().isoformat()

    return {
        "id": raw.get("id"),
        "url": raw["url"],
        "title": title,
        "body": body,
        "source": raw.get("source", ""),
        "method": raw.get("method", ""),
        "category": raw.get("category", ""),
        "published_at": published_at,
        "collected_at": collected_at,
        "status": "clean",
        "cleaned_at": datetime.now().isoformat()
    }
