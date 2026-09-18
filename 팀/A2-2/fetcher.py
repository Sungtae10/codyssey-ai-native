"""뉴스 수집: RSS(feedparser) + 크롤링(requests + BeautifulSoup).

담당: 팀원 B
아래 함수 시그니처와 반환 dict 키는 바꾸지 않는다.
반환 dict 키: url, title, body, source, method, category, published_raw, collected_at
"""
import logging
import time
from datetime import datetime

import feedparser
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


def fetch_body(url: str, selectors: dict | None, timeout: int = 10, ua: str = "") -> str:
    """기사 URL 에서 본문 텍스트를 추출한다. 실패 시 빈 문자열."""
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent": ua}, allow_redirects=True)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            node = soup.select_one(selectors.get("body_selector", "article")) if selectors else None
            paras = (node or soup).find_all("p")
            return " ".join(p.get_text(" ", strip=True) for p in paras)
        except requests.RequestException as e:
            log.warning("본문 수집 실패(%d/3) %s: %s", attempt + 1, url, e)
            time.sleep(1)
    return ""


def fetch_rss(url: str, category: str, limit: int, source_name: str,
              full_body: bool = False, delay: float = 1.0, ua: str = "",
              timeout: int = 10) -> list:
    """RSS 피드에서 기사 목록을 가져온다."""
    feed = feedparser.parse(url)
    out = []
    for e in feed.entries[:limit]:
        body = BeautifulSoup(e.get("summary", ""), "lxml").get_text(" ", strip=True)
        if full_body:
            body = fetch_body(e.link, None, timeout=timeout, ua=ua) or body
            time.sleep(delay)
        out.append({
            "url": e.link,
            "title": e.get("title", ""),
            "body": body,
            "source": source_name,
            "method": "rss",
            "category": category,
            "published_raw": e.get("published", ""),
            "collected_at": datetime.now().isoformat(timespec="seconds"),
        })
    return out


def fetch_crawl(section_url: str, category: str, limit: int, selectors: dict,
                delay: float = 1.0, ua: str = "", timeout: int = 10,
                source_name: str = "crawl") -> list:
    """섹션 페이지에서 기사 링크를 뽑고 각 기사 본문을 수집한다.

    TODO(팀원 B): 대상 언론사에 맞게 link_selector / 링크 필터 규칙을 완성한다.
    """
    log.warning("fetch_crawl 은 아직 구현되지 않았습니다 (팀원 B).")
    return []
