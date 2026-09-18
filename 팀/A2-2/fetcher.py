"""뉴스 수집: RSS(feedparser) + 크롤링(requests + BeautifulSoup).

담당: 팀원 B (박수민). 통합: 김성태.
반환 dict 키: url, title, body, source, method, category, published_raw, collected_at
"""
import logging
import time
from datetime import datetime
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 CodysseyNewsBot/1.0"
)


def fetch_body(url: str, selectors: dict = None, timeout: int = 10, ua: str = "") -> str:
    """기사 URL에서 본문 텍스트를 추출합니다.

    실패 시 최대 2회 재시도(총 3회)하며 지연을 둡니다.
    """
    user_agent = ua or DEFAULT_UA
    headers = {"User-Agent": user_agent}

    for attempt in range(3):
        try:
            r = requests.get(
                url,
                timeout=timeout,
                headers=headers,
                allow_redirects=True
            )
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "lxml")

            node = None
            if selectors and selectors.get("body_selector"):
                node = soup.select_one(selectors["body_selector"])

            if not node:
                node = (
                    soup.select_one("article")
                    or soup.select_one("div.article_content")
                    or soup.select_one("div.article-feed")
                    or soup.select_one("div.view_cont")
                    or soup.select_one(".article-body")
                    or soup.select_one("#articleBody")
                    or soup
                )

            paragraphs = [p.get_text(" ", strip=True) for p in node.find_all("p")]
            text = " ".join(paragraphs) if paragraphs else node.get_text(" ", strip=True)
            return text.strip()

        except requests.RequestException as e:
            logging.warning("본문 수집 실패(%d/3) %s: %s", attempt + 1, url, e)
            if attempt < 2:
                time.sleep(1.0)

    return ""


def fetch_rss(
    url: str,
    category: str,
    limit: int = 20,
    source_name: str = "rss",
    full_body: bool = False,
    delay: float = 1.0,
    ua: str = "",
    timeout: int = 10
) -> list[dict]:
    """RSS 피드에서 기사 목록을 수집하여 raw 기사 딕셔너리 리스트로 반환합니다."""
    feed = feedparser.parse(url)
    out = []

    for e in feed.entries[:limit]:
        raw_summary = e.get("summary", "") or e.get("description", "")
        body = BeautifulSoup(raw_summary, "lxml").get_text(" ", strip=True)

        link = e.get("link", "")
        if not link:
            continue

        if full_body:
            crawled_body = fetch_body(link, selectors=None, timeout=timeout, ua=ua)
            if crawled_body:
                body = crawled_body
            time.sleep(delay)

        out.append({
            "url": link,
            "title": e.get("title", "").strip(),
            "body": body,
            "source": source_name,
            "method": "rss",
            "category": category,
            "published_raw": e.get("published", "") or e.get("updated", ""),
            "collected_at": datetime.now().isoformat()
        })

    return out


def fetch_crawl(
    section_url: str,
    category: str,
    limit: int = 20,
    selectors: dict = None,
    delay: float = 1.0,
    ua: str = "",
    source_name: str = "crawl",
    timeout: int = 10
) -> list[dict]:
    """섹션 페이지에서 기사 링크를 탐색한 후 개별 기사 본문을 수집합니다."""
    headers = {"User-Agent": ua} if ua else {}
    out = []

    try:
        r = requests.get(section_url, timeout=timeout, headers=headers)
        r.raise_for_status()
    except requests.RequestException as e:
        logging.warning("섹션 페이지 수집 실패 %s: %s", section_url, e)
        return out

    soup = BeautifulSoup(r.text, "lxml")
    link_selector = selectors.get("link_selector", "a") if selectors else "a"
    link_nodes = soup.select(link_selector)

    visited_urls = set()
    collected = 0

    for node in link_nodes:
        if collected >= limit:
            break

        href = node.get("href")
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        full_url = urljoin(section_url, href)
        if full_url in visited_urls:
            continue

        link_title = node.get_text(" ", strip=True)

        visited_urls.add(full_url)
        time.sleep(delay)

        body = fetch_body(full_url, selectors=selectors, timeout=timeout, ua=ua)
        if not body:
            continue

        # link_title이 비어있거나 너무 짧으면 기사 페이지에서 제목 보강
        title = link_title
        if not title or len(title) < 5:
            user_agent = ua or DEFAULT_UA
            try:
                r_art = requests.get(full_url, timeout=timeout, headers={"User-Agent": user_agent}, allow_redirects=True)
                art_soup = BeautifulSoup(r_art.text, "lxml")
                title_node = (
                    art_soup.select_one("h1")
                    or art_soup.select_one("meta[property='og:title']")
                    or art_soup.title
                )
                if title_node:
                    title = (
                        title_node.get("content", "")
                        if title_node.name == "meta"
                        else title_node.get_text(" ", strip=True)
                    )
            except Exception as e:
                logging.debug("크롤링 기사 제목 추출 실패 %s: %s", full_url, e)

        if not title:
            title = "제목 없음"

        out.append({
            "url": full_url,
            "title": title,
            "body": body,
            "source": source_name,
            "method": "crawl",
            "category": category,
            "published_raw": datetime.now().strftime("%Y-%m-%d"),
            "collected_at": datetime.now().isoformat()
        })
        collected += 1

    return out
