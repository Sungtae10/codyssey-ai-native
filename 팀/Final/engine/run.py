"""AI Promise 엔진 실행

  python run.py doctor  --company samsung    시작 전 점검 (설치, 키, PDF, 실제 API 1번 호출. --no-api: 호출 빼기)
  python run.py collect --company samsung    1단계 수집 (PDF → 읽는 장의 문장)
  python run.py extract --company samsung    2~3단계 약속 추출·분류 (+ 정답 매길 목록 CSV)
  python run.py judge   --company samsung    4~6단계 근거 검색·판정·인용 검사 (--limit 1: 구체적 약속 1건만 시험)
  python run.py card    --company samsung    7단계 면접 카드 (--rule-card: 규칙 방식만)
  python run.py all     --company samsung    1~7단계를 한 번에
  python run.py export  --companies samsung skhynix [--copy-to 화면의_데이터_파일_경로]
  python run.py check   --file ../data/results/ai_promise_data.json   화면 규칙 점검
  python run.py scan    --company kakao      후보 기업 미리 보기: 2024 사업보고서 PDF 1개로 수집 + 약속 추출만 하고
                                             구체적 약속이 기준(--min, 기본 3개) 이상인지 알려 줌

공통 옵션: --mock (가짜 모델로 코드 점검), --config 다른 설정 파일
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aipromise.config import load_config, company_cfg, work_dir  # noqa: E402
from aipromise.llm import LLM  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="AI Promise 엔진")
    ap.add_argument("step", choices=["doctor", "collect", "extract", "judge", "card", "all", "export", "check", "scan"])
    ap.add_argument("--min", type=int, default=3, help="scan: 통과 기준이 되는 구체적 약속 개수 (기본 3)")
    ap.add_argument("--company")
    ap.add_argument("--companies", nargs="+")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--rule-card", action="store_true")
    ap.add_argument("--copy-to")
    ap.add_argument("--file")
    ap.add_argument("--config")
    ap.add_argument("--limit", type=int, help="judge: 구체적 약속을 앞에서부터 이 개수만 판정 (첫 시험 실행용)")
    ap.add_argument("--no-api", action="store_true", help="doctor: 실제 API 호출을 빼고 점검")
    a = ap.parse_args()
    cfg = load_config(a.config)

    if a.step == "doctor":
        from aipromise.doctor import run_doctor
        keys = [a.company] if a.company else (a.companies or list(cfg["companies"]))
        problems = run_doctor(cfg, keys, api=not a.no_api)
        sys.exit(1 if problems else 0)

    if a.step == "check":
        from aipromise.checker import check
        path = a.file or cfg["paths"]["results_file"]
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        problems = check(data, expect_real=not data.get("meta", {}).get("is_sample", False))
        print("문제 없음" if not problems else "\n".join("- " + p for p in problems))
        sys.exit(1 if any(not p.startswith("(주의)") for p in problems) else 0)

    if a.step == "export":
        from aipromise.export import run_export
        keys = a.companies or list(cfg["companies"])
        _, problems = run_export(cfg, keys, copy_to=a.copy_to)
        sys.exit(1 if any(not p.startswith("(주의)") for p in problems) else 0)

    if not a.company:
        ap.error("--company가 필요합니다 (예: --company samsung)")
    company = company_cfg(cfg, a.company)
    work = work_dir(cfg, a.company)
    llm = None
    if a.step in ("extract", "judge", "card", "all", "scan"):
        llm = LLM(cfg, os.path.join(work, "llm_log.jsonl"), mock=a.mock)

    if a.step == "scan":
        from aipromise.collect import run_collect
        from aipromise.extract import run_extract
        run_collect(cfg, company, roles=("promise",))
        promises = run_extract(cfg, company, llm, work)
        n_spec = sum(1 for p in promises if p["type"] == "specific")
        n_dir = len(promises) - n_spec
        ok = n_spec >= a.min
        print(f"\n[미리 보기 결과] {company['name']}: 구체적 약속 {n_spec}개, 방향성 약속 {n_dir}개")
        print(f"→ {'통과' if ok else '미달'} (기준: 구체적 약속 {a.min}개 이상). "
              "통과해도 약속 목록을 판정기준 v2로 한 번 읽어 보고, 근거를 찾는 보고서 PDF를 받은 뒤 all을 돌립니다.")
        sys.exit(0 if ok else 2)

    steps = ["collect", "extract", "judge", "card"] if a.step == "all" else [a.step]
    for s in steps:
        if s == "collect":
            from aipromise.collect import run_collect
            run_collect(cfg, company)
        elif s == "extract":
            from aipromise.extract import run_extract
            run_extract(cfg, company, llm, work)
        elif s == "judge":
            from aipromise.judge import run_judge
            run_judge(cfg, company, llm, work, mock=a.mock, limit=a.limit)
        elif s == "card":
            from aipromise.card import run_card
            run_card(cfg, company, llm, work, rule_only=a.rule_card)


if __name__ == "__main__":
    main()
