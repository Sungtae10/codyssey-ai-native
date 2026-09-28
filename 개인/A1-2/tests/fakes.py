"""테스트용 가짜 API 응답 모음.

실제 키와 인터넷 없이, 각 제공자의 응답 모양(JSON 구조)을 흉내 낸다.
단위 테스트(requests.request 가짜로 바꾸기)와 E2E 가짜 서버가 함께 쓴다.
"""
from __future__ import annotations

import json
import re

CITY_ADDRESS = {
    "제주": "제주특별자치도 제주시",
    "서귀포": "제주특별자치도 서귀포시",
    "강릉": "강원특별자치도 강릉시",
    "경주": "경북 경주시",
    "여수": "전남 여수시",
    "전주": "전북특별자치도 전주시",
    "부산": "부산 해운대구",
}
FOOD = ["흑돼지구이", "해물칼국수", "초당순두부", "한정식", "물회", "비빔밥", "갈치조림", "국밥"]


def recommendation(city: str = "제주") -> dict:
    return {
        "recommended_city": city,
        "weather": f"{city}의 이 시기는 선선하고 맑은 날이 많아 야외 활동에 좋습니다.",
        "events": [f"{city} 가을 축제(일정 변동 가능)", f"{city} 야시장 행사(일정 변동 가능)"],
        "reason": f"이 시기 {city}의 날씨가 안정적입니다. 걷기 좋은 명소가 많습니다. 성수기보다 붐비지 않습니다.",
    }


def multi_recommendation(cities=("제주", "강릉", "경주")) -> dict:
    return {"recommended_cities": [recommendation(c) for c in cities]}


# ---------------------------------------------------------------- LLM 응답 모양
def openai_chat(content: str) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    }


def gemini_generate(text: str) -> dict:
    return {
        "candidates": [{"content": {"parts": [{"text": text}], "role": "model"}, "finishReason": "STOP", "index": 0}],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20, "totalTokenCount": 30},
    }


def report_markdown(date_text: str, cities: list[str], with_placeholders: bool = True) -> str:
    """LLM이 규칙대로 쓴 리포트 초안을 흉내 낸다."""
    n = len(cities)
    lines = [f"# {date_text} 국내 여행 추천 리포트", "", "## 추천 지역"]
    if n == 1:
        city = cities[0]
        lines += [f"{city}: 이 시기에 걷기 좋은 도시입니다.", "",
                  "## 추천 이유", "날씨가 안정적이고 볼거리가 많습니다.", "",
                  "## 날씨 요약", "선선합니다. 얇은 겉옷을 챙기세요.", "",
                  "## 행사/축제", f"- {city} 가을 축제(일정 변동 가능)", "",
                  "## 맛집 추천", "{{RESTAURANTS_1}}" if with_placeholders else "- 식당 A", "",
                  "## 1일 일정 제안", "### 오전", "시내 산책을 합니다.", "### 오후", "축제장을 둘러봅니다.",
                  "### 저녁", "현지 식당에서 저녁을 먹습니다."]
        return "\n".join(lines)
    # 복수 지역: 2026-09-29 실제 gpt-4o-mini 응답처럼 목록 기호 없이 한 줄씩 쓴 모양
    # (지역 이름만 한 줄씩, "**오전**: ..." 줄 앞에 "- " 없음). 프로그램이 목록으로 보정해야 한다.
    lines += list(cities)
    for i, city in enumerate(cities, start=1):
        lines += ["", f"## {i}. {city}", "### 추천 이유", "날씨가 좋습니다.", "### 날씨 요약", "선선합니다.",
                  "### 행사/축제", f"- {city} 가을 축제(일정 변동 가능)", "### 맛집 추천",
                  "{{RESTAURANTS_" + str(i) + "}}" if with_placeholders else "- 식당 A",
                  "### 1일 일정 제안", "**오전**: 산책", "**오후**: 관광", "**저녁**: 식사"]
    return "\n".join(lines)


# ---------------------------------------------------------------- 장소 응답 모양
def _city_of(query: str) -> str:
    return (query or "").split()[0] if query else "제주"


def kakao_keyword(query: str, size: int = 15, count: int | None = None, foreign: int = 0) -> dict:
    """카카오 키워드 검색 응답. foreign 개수만큼 다른 지역(서울) 결과를 앞에 섞는다."""
    city = _city_of(query)
    area = CITY_ADDRESS.get(city, f"{city}시")
    total = size if count is None else count
    docs = []
    for i in range(foreign):
        docs.append({
            "id": f"9{i}", "place_name": f"{city}식당 서울점{i + 1}", "category_name": "음식점 > 한식",
            "category_group_code": "FD6", "category_group_name": "음식점", "phone": "02-000-0000",
            "address_name": f"서울 마포구 동교동 {i + 1}", "road_address_name": f"서울 마포구 양화로 {i + 1}",
            "x": "126.92", "y": "37.55", "place_url": f"http://place.map.kakao.com/9{i}", "distance": "",
        })
    for i in range(total):
        food = FOOD[i % len(FOOD)]
        docs.append({
            "id": str(1000 + i), "place_name": f"{city} {food} {i + 1}호점",
            "category_name": f"음식점 > 한식 > {food}", "category_group_code": "FD6", "category_group_name": "음식점",
            "phone": "064-000-0000", "address_name": f"{area} 테스트동 {i + 1}",
            "road_address_name": f"{area} 테스트로 {i + 1}",
            "x": f"{126.5 + i / 1000:.6f}", "y": f"{33.5 + i / 1000:.6f}",
            "place_url": f"http://place.map.kakao.com/{1000 + i}", "distance": "",
        })
    docs = docs[:size]
    return {
        "meta": {"total_count": len(docs), "pageable_count": len(docs), "is_end": True,
                 "same_name": {"region": [city], "keyword": "맛집", "selected_region": area.split()[0]}},
        "documents": docs,
    }


def naver_local(query: str, display: int = 5) -> dict:
    city = _city_of(query)
    area = CITY_ADDRESS.get(city, f"{city}시")
    items = []
    for i in range(display):
        food = FOOD[i % len(FOOD)]
        items.append({
            "title": f"<b>{city}</b> {food} &amp; 식당 {i + 1}",
            "link": "" if i % 2 else f"https://example.com/shop{i + 1}",
            "category": f"한식>{food}", "description": "", "telephone": "",
            "address": f"{area} 테스트동 {i + 1}", "roadAddress": f"{area} 테스트로 {i + 1}",
            "mapx": str(1265300000 + i * 1000), "mapy": str(335000000 + i * 1000),
        })
    return {"lastBuildDate": "Tue, 29 Sep 2026 10:00:00 +0900", "total": len(items), "start": 1,
            "display": len(items), "items": items}


def cities_from_report_prompt(prompt: str) -> tuple[str, list[str]]:
    """리포트 프롬프트의 [데이터] 부분에서 날짜와 지역 이름을 꺼낸다(가짜 LLM이 틀에 맞게 답하려고)."""
    date_match = re.search(r"# (\d{4}-\d{2}-\d{2}) 국내 여행 추천 리포트", prompt)
    data_match = re.search(r"\[데이터\]\n(.*?)\n\[데이터 끝\]", prompt, re.S)
    blocks = json.loads(data_match.group(1)) if data_match else []
    return (date_match.group(1) if date_match else "2026-10-10"), [b["recommended_city"] for b in blocks]
