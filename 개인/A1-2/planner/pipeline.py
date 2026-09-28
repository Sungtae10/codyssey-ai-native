"""3단계 실행 흐름.

[1/3] LLM 1차 추천(POST, JSON)      -> recommended_city
[2/3] 지도/장소 API 맛집 검색(GET)   -> 맛집 N곳 (0건, 실패여도 '데이터 없음'으로 계속)
[3/3] LLM 최종 리포트(POST, Markdown) -> 프로그램이 맛집 표와 오류 요약을 채워 저장

보너스
- 복수 지역: n_cities 2~3이면 지역마다 [2/3] 검색을 반복한다.
- 캐싱     : 같은 조건으로 성공한 원본 JSON이 있으면 [1/3], [2/3] 호출을 건너뛰고 리포트만 다시 만든다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from . import __version__
from .config import PLACE_LABELS, Settings
from .errors import (
    EMPTY_RESULT,
    STEP_PLACE,
    STEP_RECOMMEND,
    ApiError,
    ErrorCollector,
    hint_for,
)
from .http_client import register_secrets
from .llm import create_llm, recommend
from .places import create_place_client, normalize_city
from .report import build_report
from .storage import load_cache, result_paths, save_json, save_text


class FatalRunError(Exception):
    """[1/3] 1차 추천이 실패해 더 진행할 수 없음. 오류 기록은 원본 JSON에 저장된 상태."""

    def __init__(self, error: ApiError, raw_path: Path, provider: str):
        super().__init__(str(error))
        self.error = error
        self.raw_path = raw_path
        self.provider = provider


@dataclass
class RunResult:
    raw_path: Path
    report_path: Path
    errors: list
    cache_used: bool
    report_source: str  # "llm" 또는 "template"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run(travel_date: date, settings: Settings, *, n_cities: int = 1, count: int = 5,
        keyword: str = "맛집", use_cache: bool = True, results_dir: str | Path = "results",
        log=print) -> RunResult:
    register_secrets(settings.secrets())  # 이후 모든 오류 메시지/저장 파일에서 키를 *** 로 가린다
    errors = ErrorCollector()
    paths = result_paths(results_dir, travel_date, n_cities)

    if settings.place_provider == "naver" and count > 5:
        log("  (참고: Naver 지역 검색은 한 번에 최대 5곳이라 맛집 수를 5곳으로 맞춥니다)")
        count = 5

    cache_key = {
        "travel_date": travel_date.isoformat(),
        "city_count": n_cities,
        "restaurant_count": count,
        "keyword": keyword,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "place_provider": settings.place_provider,
    }
    meta = {
        "program": "codyssey-a1-2-travel-planner",
        "version": __version__,
        "travel_date": travel_date.isoformat(),
        "mode": "single" if n_cities <= 1 else "multi",
        "generated_at": _now(),
        "last_run_at": _now(),
        "llm": {"provider": settings.llm_provider, "model": settings.llm_model},
        "place": {"provider": settings.place_provider, "label": PLACE_LABELS[settings.place_provider]},
        "cache": {"used": False},
        "cache_key": cache_key,
    }
    llm = create_llm(settings)

    cached, reason = load_cache(paths.raw, cache_key) if use_cache else (None, "")
    if cached:
        log(f"[캐시] {paths.raw.as_posix()} 파일을 재사용합니다. 1차 추천과 맛집 검색 API 호출을 건너뜁니다.")
        log("       (API를 새로 부르려면 --no-cache를 붙여 실행)")
        recommendation = cached["recommendation"]
        restaurants = cached["restaurants"]
        searches = cached.get("place_searches") or []
        errors.extend([e for e in cached.get("errors") or [] if e.get("step") in (STEP_RECOMMEND, STEP_PLACE)])
        meta["generated_at"] = (cached.get("meta") or {}).get("generated_at", meta["generated_at"])
        meta["cache"] = {"used": True, "source": paths.raw.as_posix()}
        log(f'  - recommended_city: "{recommendation["recommended_city"]}" (캐시)')
    else:
        if reason:
            log(f"[캐시] {reason}. API를 새로 호출합니다.")
        recommendation = _step_recommend(llm, travel_date, n_cities, errors, meta, paths, log)
        searches, restaurants = _step_places(settings, recommendation, keyword, count, errors, log)
        # 중간 저장: 리포트 단계에서 문제가 생겨도 1~2단계 결과는 남는다
        save_json(paths.raw, _raw_document(meta, recommendation, restaurants, searches, errors))

    log("[3/3] 최종 리포트 생성 중(LLM)...")
    report_md, source = build_report(llm, travel_date, recommendation, restaurants, searches, errors, meta, log)
    if source == "llm":
        log("  - 리포트 생성 완료")
    save_json(paths.raw, _raw_document(meta, recommendation, restaurants, searches, errors))
    save_text(paths.report, report_md)

    log("")
    log(f"완료! {paths.report.as_posix()} 를 확인하세요.")
    log(f"  - 원본 데이터: {paths.raw.as_posix()}")
    if len(errors):
        log(f"  - 오류 {len(errors)}건 (리포트 맨 아래 '오류 요약(errors)' 참고)")
    else:
        log("  - 오류 0건")
    return RunResult(paths.raw, paths.report, errors.to_list(), meta["cache"]["used"], source)


def _step_recommend(llm, travel_date, n_cities, errors, meta, paths, log) -> dict:
    log("[1/3] 1차 추천 생성 중(LLM)...")
    try:
        recommendation = recommend(llm, travel_date, n_cities, errors, log)
    except ApiError as exc:
        errors.add(STEP_RECOMMEND, exc.err_type, exc.message)
        save_json(paths.raw, _raw_document(meta, None, [], [], errors))
        raise FatalRunError(exc, paths.raw, llm.provider) from None
    log(f'  - recommended_city: "{recommendation["recommended_city"]}"')
    if n_cities > 1:
        names = ", ".join(c["recommended_city"] for c in recommendation["recommended_cities"])
        log(f"  - recommended_cities: {names}")
    return recommendation


def _step_places(settings, recommendation, keyword, count, errors, log) -> tuple[list, list]:
    log("[2/3] 맛집 검색 중(지도/장소 API)...")
    client = create_place_client(settings)
    cities = [c["recommended_city"] for c in recommendation.get("recommended_cities") or [recommendation]]
    multi = len(cities) > 1
    searches: list[dict] = []
    restaurants: list[dict] = []
    for i, city in enumerate(cities, start=1):
        prefix = f"[{i}] {city}: " if multi else ""
        try:
            result = client.search(city, keyword, count)
        except ApiError as exc:
            query = f"{normalize_city(city) or city} {keyword}"
            errors.add(STEP_PLACE, exc.err_type, f"{exc.message} (query={query})")
            log(f"  - {prefix}오류: {hint_for(exc, settings.place_provider)}")
            log("  - 맛집 섹션은 '데이터 없음'으로 처리하고 계속 진행합니다.")
            searches.append({"city": city, "query": query, "provider": settings.place_provider,
                             "status": "error", "error_type": exc.err_type, "result_count": 0})
            continue
        items = result.pop("items")
        if not items:
            errors.add(STEP_PLACE, EMPTY_RESULT, f"0 results for query={result['query']}")
            log(f"  - {prefix}검색 결과 0건(키워드/카테고리를 바꿔 재시도하지 않고 다음 단계로 진행)")
            result["status"] = "empty"
        else:
            result["status"] = "ok"
            log(f"  - {prefix}맛집 {len(items)}곳 검색 완료 (검색어: {result['query']})")
        searches.append(result)
        restaurants.extend(items)
    return searches, restaurants


def _raw_document(meta, recommendation, restaurants, searches, errors) -> dict:
    """원본 JSON 구조. 과제 필수 3가지(recommendation, restaurants, errors)를 최상위에 둔다."""
    return {
        "meta": meta,
        "recommendation": recommendation,   # 1차 추천 JSON(파싱·검증 결과)
        "restaurants": restaurants,         # 맛집 검색 결과(리스트, 0건 가능)
        "place_searches": searches,         # 지역별 검색어, 상태(ok/empty/error), 건수
        "errors": errors.to_list(),         # 오류 요약(빈 리스트 가능)
    }
