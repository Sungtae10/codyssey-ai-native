"""결과 파일 저장과 캐시 읽기.

- 저장 위치: results/ (없으면 만든다)
- 파일 이름: 입력한 여행 날짜 기준
    지역 1곳  : results/2026-10-10_raw.json, results/2026-10-10_travel_plan.md
    지역 N곳  : results/2026-10-10_3cities_raw.json, results/2026-10-10_3cities_travel_plan.md
- 저장 직전에 등록된 API 키 문자열이 들어 있으면 *** 로 바꾼다(마지막 유출 방지 장치).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .errors import EMPTY_RESULT, STEP_PLACE, STEP_RECOMMEND
from .http_client import mask


@dataclass(frozen=True)
class ResultPaths:
    raw: Path
    report: Path


def result_paths(results_dir: str | Path, travel_date: date, n_cities: int = 1) -> ResultPaths:
    tag = travel_date.isoformat() if n_cities <= 1 else f"{travel_date.isoformat()}_{n_cities}cities"
    base = Path(results_dir)
    return ResultPaths(raw=base / f"{tag}_raw.json", report=base / f"{tag}_travel_plan.md")


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(mask(text) + "\n", encoding="utf-8")


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = mask(text)
    path.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")


def load_cache(path: Path, cache_key: dict) -> tuple[dict | None, str]:
    """같은 조건으로 성공했던 원본 JSON이 있으면 돌려준다.

    반환: (캐시 데이터 또는 None, 쓰지 않은 이유). 파일이 아예 없으면 이유는 빈 문자열.
    실패(인증, 한도, 네트워크 등)가 남아 있는 결과는 캐시로 쓰지 않는다. 0건(EMPTY_RESULT)은 정상 결과로 본다.
    """
    if not path.is_file():
        return None, ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, f"{path.name}을(를) 읽지 못해 캐시로 쓰지 않습니다"
    if not isinstance(data, dict):
        return None, "캐시 파일 형식이 올바르지 않습니다"
    saved_key = (data.get("meta") or {}).get("cache_key")
    if saved_key != cache_key:
        return None, "이전 결과와 실행 조건(지역 수, 맛집 수, 키워드, 제공자)이 달라 캐시로 쓰지 않습니다"
    if not isinstance(data.get("recommendation"), dict) or not isinstance(data.get("restaurants"), list):
        return None, "이전 결과에 1차 추천 또는 맛집 목록이 없어 캐시로 쓰지 않습니다"
    failed = [
        e for e in data.get("errors") or []
        if isinstance(e, dict)
        and e.get("step") in (STEP_RECOMMEND, STEP_PLACE)
        and e.get("type") != EMPTY_RESULT
        and "재시도 성공" not in str(e.get("message", ""))
    ]
    if failed:
        return None, f"이전 결과에 오류({failed[0].get('type')})가 있어 캐시로 쓰지 않습니다"
    return data, ""
