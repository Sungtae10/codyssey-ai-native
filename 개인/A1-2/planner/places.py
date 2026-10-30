"""지도/장소 검색 (Kakao Local 또는 Naver 지역 검색).

흐름: normalize_city()로 지명 보정 -> "{지명} {키워드}" 검색어 -> GET 호출
      -> 응답 필드 통일(name, address, category, url, lat, lng) -> 주소로 지역 검증 -> N곳 선택

장소 API를 바꾸고 싶으면 BasePlaceClient를 상속한 클래스에
_request()(요청 보내기)와 _normalize_item()(필드 이름 맞추기) 두 개만 만들고 PLACE_CLASSES에 등록한다.
"""
from __future__ import annotations

import html
import re
from urllib.parse import quote

from .errors import PARSE_ERROR, ApiError
from .http_client import get_json

KAKAO_FOOD_CATEGORY = "FD6"  # 카카오 카테고리 그룹 코드: 음식점
KAKAO_CAFE_CATEGORY = "CE7"  # 카카오 카테고리 그룹 코드: 카페 (--keyword 카페일 때)


def kakao_category(query: str) -> str:
    """검색어에 '카페' 또는 '커피'가 있으면 카페(CE7), 아니면 음식점(FD6)으로 좁힌다."""
    return KAKAO_CAFE_CATEGORY if ("카페" in query or "커피" in query) else KAKAO_FOOD_CATEGORY

# 광역 지명 -> 카카오/네이버 주소에 쓰이는 짧은 지명
REGION_ALIASES = {
    "서울특별시": "서울", "서울시": "서울",
    "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주",
    "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
    "제주특별자치도": "제주", "제주도": "제주",
    "강원특별자치도": "강원", "강원도": "강원",
    "경기도": "경기",
    "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남",
}
BROAD_NAMES = set(REGION_ALIASES) | set(REGION_ALIASES.values())
_ADMIN_SUFFIXES = ("구", "군", "시")                     # 좁은 행정 단위
_MULTI_REGION = re.compile(r"[,/·ㆍ&+]|\s및\s|\s와\s|\s과\s")
_BRACKETS = re.compile(r"\(.*?\)|\[.*?\]")
_TAGS = re.compile(r"<[^>]+>")


def normalize_city(name: str) -> str:
    """LLM이 준 지명을 검색하기 좋은 짧은 지명으로 바꾼다.

    규칙
      1) 괄호 안 설명 제거                 '경주(보문단지)'   -> '경주'
      2) 여러 지역이면 첫 번째만           '속초·양양'        -> '속초'
      3) 여러 단어면 가장 좁은 지역 선택    '제주도 서귀포시'  -> '서귀포'
                                           '강원 강릉'        -> '강릉'
                                           '전주 한옥마을'    -> '전주'
      4) 광역 지명은 짧은 이름으로         '제주특별자치도'   -> '제주', '강원도' -> '강원'
      5) 시/군/구 접미사 제거(2글자 이상 남을 때) '강릉시' -> '강릉', '해운대구' -> '해운대'
    """
    text = _BRACKETS.sub(" ", str(name or ""))
    text = _MULTI_REGION.split(text)[0]
    tokens = text.split()
    if not tokens:
        return ""

    def level(token: str) -> int:
        if token in BROAD_NAMES:
            return 1  # 도, 광역시처럼 넓은 지역
        if token.endswith(_ADMIN_SUFFIXES) and len(token) >= 3:
            return 3  # 서귀포시, 해운대구처럼 좁은 행정 단위
        return 2      # 강릉, 전주처럼 접미사 없는 지명

    best = max(tokens, key=level)  # 같은 등급이면 앞쪽 단어(max는 먼저 나온 것을 고름)
    if best in REGION_ALIASES:
        return REGION_ALIASES[best]
    for suffix in _ADMIN_SUFFIXES:
        if best.endswith(suffix) and len(best) - len(suffix) >= 2:
            return best[: -len(suffix)]
    return best


def in_region(item: dict, search_city: str) -> bool:
    """검색 결과 주소에 지명이 들어 있는지 확인한다(엉뚱한 지역 결과 거르기)."""
    if not search_city:
        return True
    address = f"{item.get('address', '')} {item.get('address_jibun', '')}"
    return search_city in address


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class BasePlaceClient:
    provider = "base"
    label = "장소 검색"
    max_size = 15  # 한 번에 받을 수 있는 최대 개수

    def __init__(self, keys: dict, base_url: str, timeout: float = 15):
        self.keys = keys
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(self, city: str, keyword: str, count: int) -> dict:
        """맛집 검색. API 오류는 ApiError로 올려 보낸다(파이프라인이 '데이터 없음' 처리)."""
        search_city = normalize_city(city) or city
        query = f"{search_city} {keyword}".strip()
        size = min(self.max_size, max(count * 2, count))  # 지역 검증으로 걸러질 몫까지 넉넉히
        docs, meta = self._request(query, size)
        items = [self._normalize_item(d) for d in docs if isinstance(d, dict)]
        items = [it for it in items if it.get("name")]
        matched = [it for it in items if in_region(it, search_city)]
        chosen = (matched or items)[:count]
        for it in chosen:
            it["city"] = city
            it.pop("address_jibun", None)
        return {
            "city": city,
            "search_city": search_city,
            "query": query,
            "provider": self.provider,
            "total_count": meta.get("total_count"),
            "selected_region": meta.get("selected_region"),
            "region_matched": len(matched),
            "result_count": len(chosen),
            "items": chosen,
        }

    def _request(self, query: str, size: int) -> tuple[list, dict]:
        raise NotImplementedError

    def _normalize_item(self, raw: dict) -> dict:
        raise NotImplementedError


class KakaoPlaceClient(BasePlaceClient):
    """Kakao Local 키워드 검색: GET /v2/local/search/keyword.json, 헤더 Authorization: KakaoAK {키}"""

    provider = "kakao"
    label = "Kakao Local"
    max_size = 15

    def _request(self, query: str, size: int) -> tuple[list, dict]:
        data = get_json(
            f"{self.base_url}/v2/local/search/keyword.json",
            params={
                "query": query,
                "category_group_code": kakao_category(query),
                "size": size,
                "sort": "accuracy",
            },
            headers={"Authorization": f"KakaoAK {self.keys['rest_api_key']}"},
            timeout=self.timeout,
        )
        docs = data.get("documents")
        if not isinstance(docs, list):
            raise ApiError(PARSE_ERROR, "Kakao 응답에 documents 목록이 없음")
        meta = data.get("meta") or {}
        same_name = meta.get("same_name") or {}
        return docs, {
            "total_count": meta.get("total_count"),
            "selected_region": same_name.get("selected_region") if isinstance(same_name, dict) else None,
        }

    def _normalize_item(self, raw: dict) -> dict:
        category = str(raw.get("category_name") or "")
        if category.startswith("음식점 > "):
            category = category[len("음식점 > "):]
        return {
            "name": str(raw.get("place_name") or "").strip(),
            "address": str(raw.get("road_address_name") or raw.get("address_name") or "").strip(),
            "address_jibun": str(raw.get("address_name") or ""),
            "category": category,
            "url": str(raw.get("place_url") or ""),
            "lat": _to_float(raw.get("y")),
            "lng": _to_float(raw.get("x")),
            "phone": str(raw.get("phone") or ""),
        }


class NaverPlaceClient(BasePlaceClient):
    """Naver 지역 검색: GET /v1/search/local.json, 헤더 X-Naver-Client-Id / X-Naver-Client-Secret"""

    provider = "naver"
    label = "Naver 지역 검색"
    max_size = 5  # 네이버 지역 검색은 한 번에 최대 5건

    def _request(self, query: str, size: int) -> tuple[list, dict]:
        data = get_json(
            f"{self.base_url}/v1/search/local.json",
            params={"query": query, "display": min(size, self.max_size), "start": 1, "sort": "comment"},
            headers={
                "X-Naver-Client-Id": self.keys["client_id"],
                "X-Naver-Client-Secret": self.keys["client_secret"],
            },
            timeout=self.timeout,
        )
        items = data.get("items")
        if not isinstance(items, list):
            raise ApiError(PARSE_ERROR, "Naver 응답에 items 목록이 없음")
        return items, {"total_count": data.get("total")}

    @staticmethod
    def _coord(value) -> float | None:
        """네이버 mapx/mapy는 WGS84 경위도 x 10^7 정수. (예전 KATEC 좌표면 변환하지 않고 None)"""
        try:
            number = int(str(value).strip())
        except (TypeError, ValueError):
            return None
        return number / 10_000_000 if abs(number) > 100_000_000 else None

    def _normalize_item(self, raw: dict) -> dict:
        name = html.unescape(_TAGS.sub("", str(raw.get("title") or ""))).strip()
        link = str(raw.get("link") or "").strip()
        return {
            "name": name,
            "address": str(raw.get("roadAddress") or raw.get("address") or "").strip(),
            "address_jibun": str(raw.get("address") or ""),
            "category": str(raw.get("category") or ""),
            "url": link or (f"https://map.naver.com/p/search/{quote(name)}" if name else ""),
            "lat": self._coord(raw.get("mapy")),
            "lng": self._coord(raw.get("mapx")),
            "phone": str(raw.get("telephone") or ""),
        }


PLACE_CLASSES = {"kakao": KakaoPlaceClient, "naver": NaverPlaceClient}


def create_place_client(settings) -> BasePlaceClient:
    cls = PLACE_CLASSES[settings.place_provider]
    return cls(settings.place_keys, settings.place_base_url)
