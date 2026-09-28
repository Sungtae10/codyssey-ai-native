"""LLM 출력에서 JSON을 꺼내고, 1차 추천 스키마(필수 키와 타입)를 검사한다.

1차 추천 필수 스키마 (과제 명세)
    recommended_city : string        (예: "제주")
    weather          : string        (해당 시기 일반적 날씨 요약)
    events           : string 배열    (행사/축제 후보 1~3개)
    reason           : string        (추천 근거 2~4문장)

보너스(복수 지역) 모드에서는 {"recommended_cities": [ {위 4개 키}, ... ]}로 받는다.
이때도 결과의 최상위에는 1순위 지역의 4개 키를 그대로 두어 기본 스키마를 항상 만족시킨다.
"""
from __future__ import annotations

import json
import re

REQUIRED_KEYS: dict[str, type] = {
    "recommended_city": str,
    "weather": str,
    "events": list,
    "reason": str,
}
# 위 4개는 validate_city()가 하나씩 따로 검사한다. REQUIRED_KEYS에 키를 더 넣으면(예: "budget": str)
# 그 키는 아래 반복문이 타입만 검사해 결과에 그대로 담는다(프롬프트 설명은 llm.py에 한 줄 추가).
SPEC_KEYS = ("recommended_city", "weather", "events", "reason")
MAX_EVENTS = 3
MAX_CITY_LEN = 20
# 지명 하나에 지역이 여러 개 섞였는지 확인 (예: "속초, 양양", "속초·양양", "속초 및 양양")
_MULTI_REGION = re.compile(r"[,/·ㆍ&+]|\s및\s|\s와\s|\s과\s")
_CODE_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)


def extract_json(text: str) -> dict:
    """텍스트에서 JSON 객체 하나를 찾아 dict로 돌려준다. 못 찾으면 ValueError.

    순서대로 시도한다.
      1) 텍스트 전체를 그대로 json.loads
      2) ```json ... ``` 코드블록 안쪽만 json.loads
      3) 첫 '{'부터 짝이 맞는 '}'까지 잘라서 json.loads (앞뒤 인사말 제거)
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("빈 응답")
    s = text.strip()

    obj = _try_loads(s)
    if obj is not None:
        return obj

    fence = _CODE_FENCE.search(s)
    if fence:
        obj = _try_loads(fence.group(1).strip())
        if obj is not None:
            return obj

    start = s.find("{")
    while start != -1:
        end = _matching_brace(s, start)
        if end == -1:
            break
        obj = _try_loads(s[start:end + 1])
        if obj is not None:
            return obj
        start = s.find("{", start + 1)
    raise ValueError("JSON 객체를 찾지 못함")


def _try_loads(s: str) -> dict | None:
    try:
        obj = json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


def _matching_brace(s: str, start: int) -> int:
    """s[start]의 '{'와 짝이 맞는 '}' 위치. 문자열 안의 괄호는 무시한다."""
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def validate_city(block, label: str = "") -> tuple[dict | None, list[str]]:
    """지역 하나의 4개 필수 키를 검사한다. 통과하면 (정리된 dict, []), 아니면 (None, 문제 목록)."""
    if not isinstance(block, dict):
        return None, [f"{label}JSON 객체가 아님"]
    problems = [f"{label}필수 키 '{key}' 없음" for key in REQUIRED_KEYS if key not in block]
    if problems:
        return None, problems

    out: dict = {}
    city = block["recommended_city"]
    if not isinstance(city, str) or not city.strip():
        problems.append(f"{label}recommended_city는 비어 있지 않은 문자열이어야 함")
    else:
        city = " ".join(city.split())
        if len(city) > MAX_CITY_LEN:
            problems.append(f"{label}recommended_city가 너무 김({len(city)}자)")
        elif _MULTI_REGION.search(city):
            problems.append(f"{label}recommended_city에 지역이 여러 개 들어 있음('{city}')")
        else:
            out["recommended_city"] = city

    weather = block["weather"]
    if not isinstance(weather, str) or not weather.strip():
        problems.append(f"{label}weather는 비어 있지 않은 문자열이어야 함")
    else:
        out["weather"] = " ".join(weather.split())

    events = block["events"]
    if isinstance(events, str):  # 가벼운 보정: 문자열 하나로 오면 배열로 감싼다
        events = [events]
    if not isinstance(events, list):
        problems.append(f"{label}events는 문자열 배열이어야 함")
    else:
        cleaned = [" ".join(e.split()) for e in events if isinstance(e, str) and e.strip()]
        if not cleaned:
            problems.append(f"{label}events가 비어 있음(1~3개 필요)")
        else:
            out["events"] = cleaned[:MAX_EVENTS]  # 가벼운 보정: 3개를 넘으면 앞의 3개만

    reason = block["reason"]
    if not isinstance(reason, str) or not reason.strip():
        problems.append(f"{label}reason은 비어 있지 않은 문자열이어야 함")
    else:
        out["reason"] = " ".join(reason.split())

    for key, expected in REQUIRED_KEYS.items():  # 과제 4개 키 외에 추가한 키
        if key in SPEC_KEYS:
            continue
        value = block[key]
        if expected is str:
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{label}{key}는 비어 있지 않은 문자열이어야 함")
            else:
                out[key] = " ".join(value.split())
        elif not isinstance(value, expected):
            problems.append(f"{label}{key}의 타입이 {expected.__name__}이어야 함")
        else:
            out[key] = value

    return (None, problems) if problems else (out, [])


def validate_recommendation(data, n_cities: int = 1) -> tuple[bool, list[str], dict | None]:
    """1차 추천 전체를 검사한다. 반환: (통과 여부, 문제 목록, 정리된 결과)."""
    if not isinstance(data, dict):
        return False, ["최상위가 JSON 객체가 아님"], None

    if n_cities <= 1:
        block = data
        listed = data.get("recommended_cities")
        if not all(k in data for k in REQUIRED_KEYS) and isinstance(listed, list) and listed:
            block = listed[0]  # 목록 형태로 답했으면 첫 번째 지역만 사용
        city, problems = validate_city(block)
        return (True, [], city) if city else (False, problems, None)

    items = data.get("recommended_cities")
    if not isinstance(items, list):
        return False, ["'recommended_cities' 배열이 없음"], None
    cities: list[dict] = []
    problems: list[str] = []
    seen: set[str] = set()
    for i, block in enumerate(items, start=1):
        city, probs = validate_city(block, label=f"{i}번째 지역: ")
        if probs:
            problems.extend(probs)
            continue
        if city["recommended_city"] in seen:
            problems.append(f"{i}번째 지역 '{city['recommended_city']}'이(가) 중복됨")
            continue
        seen.add(city["recommended_city"])
        cities.append(city)
    if len(cities) < n_cities:
        problems.append(f"서로 다른 지역 {n_cities}곳이 필요한데 유효한 지역은 {len(cities)}곳")
        return False, problems, None

    cities = cities[:n_cities]
    normalized = dict(cities[0])            # 기본 스키마 4개 키 = 1순위 지역
    normalized["recommended_cities"] = cities
    return True, [], normalized
