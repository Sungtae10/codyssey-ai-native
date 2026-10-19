"""engine/config.yaml 모양 검사 (API 키, PDF 없이).

10/19에 config.yaml의 companies 블록이 통째로 지워진 채 main에 올라갔는데 CI가 통과했습니다.
그런 일이 다시 생기면 여기서 바로 실패하게 합니다.
실행: python tests/test_config.py  (마지막 줄 "설정 검사 통과")
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from aipromise.config import company_cfg, load_config  # noqa: E402

CORE = ["samsung", "skhynix"]
DEMO = ["kakao", "shinhanbank", "naver"]   # 10/19 결정. 시연용 기업을 바꾸면 여기도 같이 바꿉니다
REPORT_KEYS = ["y2024", "y2025", "h2026"]


def main():
    cfg = load_config()
    problems = []

    r = cfg.get("retrieval") or {}
    for key in ["top_windows", "max_candidates", "max_attempts"]:
        if type(r.get(key)) is not int or r.get(key) < 1:   # true/false는 숫자로 치지 않음
            problems.append(f"retrieval.{key} 값이 1 이상의 숫자가 아닙니다: {r.get(key)!r}")
    for key in r:
        if isinstance(r[key], dict):
            problems.append(f"retrieval 안에 기업처럼 보이는 '{key}'가 들어 있습니다 (들여쓰기 확인)")

    companies = cfg.get("companies") or {}
    candidates = cfg.get("candidates") or {}
    for key in CORE:
        if key not in companies:
            problems.append(f"companies에서 핵심 기업이 빠졌습니다: {key}")

    for key in DEMO:
        if key not in candidates:
            problems.append(f"candidates에서 시연용 기업이 빠졌습니다: {key}")
    for key in set(companies) & set(candidates):
        problems.append(f"'{key}'가 companies와 candidates에 둘 다 있습니다 (companies 쪽만 쓰임)")

    for key in list(companies) + list(candidates):
        try:
            c = company_cfg(cfg, key)
        except BaseException as e:  # SystemExit 포함
            problems.append(f"'{key}' 설정을 읽지 못했습니다: {e}")
            continue
        if not str(c.get("name") or "").strip():
            problems.append(f"'{key}'에 name(화면에 보일 기업 이름)이 없습니다")
        reports = (c.get("promise_reports") or []) + (c.get("evidence_reports") or [])
        if [x.get("key") for x in reports] != REPORT_KEYS:
            problems.append(f"'{key}' 보고서 key가 {REPORT_KEYS}가 아닙니다")
        for x in reports:
            if not str(x.get("pdf", "")).endswith(".pdf"):
                problems.append(f"'{key}' {x.get('key')}의 pdf 파일 이름이 이상합니다: {x.get('pdf')!r}")

    if problems:
        print("설정 검사 실패:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print(f"핵심 기업: {list(companies)} / 시연용 후보: {list(candidates)}")
    print("설정 검사 통과")


if __name__ == "__main__":
    main()
