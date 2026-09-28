#!/usr/bin/env python3
"""국내 여행 추천 프로그램 (코디세이 A1-2)

사용법
  python travel_planner.py -date "YYYY-MM-DD"
  python travel_planner.py --date "2026-10-10" --cities 3      (보너스: 복수 지역)
  python travel_planner.py --date "2026-10-10" --no-cache      (캐시 무시하고 API 다시 호출)

흐름
  [1/3] LLM 1차 추천(JSON) -> [2/3] 지도 API 맛집 검색 -> [3/3] LLM 최종 리포트(Markdown)
  결과: results/{날짜}_raw.json, results/{날짜}_travel_plan.md

종료 코드
  0 정상 | 1 실행 실패(1차 추천 불가 등) | 2 입력 오류(날짜 형식 등) | 3 설정 오류(API 키 미설정)
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime

EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_CONFIG = 0, 1, 2, 3
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
WEEKDAYS = "월화수목금토일"


def valid_date(value: str) -> date:
    """argparse 용 날짜 검사. 틀리면 ArgumentTypeError -> 사용법 출력 후 종료 코드 2."""
    text = value.strip()
    if not DATE_PATTERN.fullmatch(text):
        raise argparse.ArgumentTypeError(
            f"날짜 형식이 올바르지 않습니다: '{value}' (YYYY-MM-DD 형식으로 입력, 예: 2026-10-10)"
        )
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"존재하지 않는 날짜입니다: '{value}'") from None


def restaurant_count(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"숫자를 입력하세요: '{value}'") from None
    if not 1 <= number <= 15:
        raise argparse.ArgumentTypeError("맛집 수는 1~15 사이로 입력하세요")
    return number


def search_keyword(value: str) -> str:
    text = " ".join(value.split())
    if not text or len(text) > 20:
        raise argparse.ArgumentTypeError("검색 키워드는 1~20자로 입력하세요 (예: 맛집, 해산물, 카페)")
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="travel_planner.py",
        description="LLM API와 지도 API를 엮어 국내 여행 리포트를 만드는 CLI 프로그램",
        epilog='예시: python travel_planner.py -date "2026-10-10"',
    )
    parser.add_argument(
        "-date", "--date", dest="date", required=True, type=valid_date, metavar="YYYY-MM-DD",
        help="여행 날짜 (필수), 예: 2026-10-10",
    )
    parser.add_argument(
        "--cities", type=int, choices=[1, 2, 3], default=1, metavar="N",
        help="추천 지역 수 1~3 (기본 1). 2~3은 보너스 기능(복수 지역 추천)",
    )
    parser.add_argument(
        "--count", type=restaurant_count, default=5, metavar="N",
        help="지역당 맛집 수 1~15 (기본 5, Naver는 최대 5)",
    )
    parser.add_argument(
        "--keyword", type=search_keyword, default="맛집", metavar="단어",
        help="장소 검색 키워드 (기본: 맛집). 검색어는 '{지역} {키워드}'로 만들어진다",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="같은 조건의 결과 파일이 있어도 API를 다시 호출한다 (보너스 기능: 캐싱 끄기)",
    )
    parser.add_argument("--results-dir", default="results", metavar="폴더", help="결과 저장 폴더 (기본: results)")
    parser.add_argument("--llm", choices=["openai", "gemini"], help="LLM 제공자 (기본: .env의 LLM_PROVIDER)")
    parser.add_argument("--place", choices=["kakao", "naver"], help="장소 검색 제공자 (기본: .env의 PLACE_PROVIDER)")
    parser.add_argument("--env-file", metavar="경로", help="읽을 .env 파일 경로 (기본: 프로그램 폴더의 .env)")
    return parser


def _configure_console() -> None:
    """Windows 콘솔 등에서 출력할 수 없는 글자가 있어도 멈추지 않게 한다."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    if sys.version_info < (3, 10):
        print(f"Python 3.10 이상이 필요합니다(현재 {sys.version.split()[0]}).", file=sys.stderr)
        return EXIT_FAIL

    args = build_parser().parse_args(argv)  # 날짜 형식이 틀리면 여기서 사용법 출력 후 종료(코드 2)

    try:
        from planner.config import ConfigError, load_env, load_settings
        from planner.errors import hint_for
        from planner.pipeline import FatalRunError, run
    except ImportError as exc:
        print(f"[설치 오류] 모듈을 불러오지 못했습니다({exc.name}).", file=sys.stderr)
        print("  - 프로젝트 폴더에서 실행했는지 확인하고, 패키지를 설치하세요: python -m pip install -r requirements.txt",
              file=sys.stderr)
        return EXIT_FAIL

    # 1) 설정 읽기: 키가 없으면 즉시 종료 + 설정 방법 안내
    env_note = load_env(args.env_file)
    try:
        settings = load_settings(llm_provider=args.llm, place_provider=args.place)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG

    travel_date: date = args.date
    print(f"여행 날짜: {travel_date.isoformat()}({WEEKDAYS[travel_date.weekday()]}) | {settings.describe()} | {env_note}")
    if travel_date < date.today():
        print("  (참고: 지난 날짜입니다. 그 시기의 일반적인 계절 정보로 추천합니다)")
    custom_urls = settings.custom_base_urls()
    if custom_urls:
        print(f"  (참고: 기본 API 주소 대신 {', '.join(custom_urls)}로 요청합니다. "
              "연습용 설정이 남은 창이라면 PowerShell 창을 새로 열고 실행하세요)")

    # 2) 3단계 실행
    try:
        run(
            travel_date,
            settings,
            n_cities=args.cities,
            count=args.count,
            keyword=args.keyword,
            use_cache=not args.no_cache,
            results_dir=args.results_dir,
        )
    except FatalRunError as exc:
        print("", file=sys.stderr)
        print("[중단] 1차 추천(LLM) 단계가 실패해 다음 단계로 진행할 수 없습니다.", file=sys.stderr)
        print(f"  - 원인: {exc.error.err_type}: {exc.error.message}", file=sys.stderr)
        print(f"  - 조치: {hint_for(exc.error, exc.provider)}", file=sys.stderr)
        print(f"  - 오류 기록: {exc.raw_path.as_posix()}", file=sys.stderr)
        return EXIT_FAIL
    except KeyboardInterrupt:
        print("\n사용자가 중단했습니다(Ctrl+C).", file=sys.stderr)
        return 130
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
