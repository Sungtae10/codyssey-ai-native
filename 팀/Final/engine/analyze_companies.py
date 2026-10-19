"""여러 기업을 한 번에: OpenDART 자동 수집 → 1~7단계 → 결과 파일 → 화면 데이터 미리 보기 (10/19 추가)

사용 예 (engine 폴더에서):
  python analyze_companies.py kakao naver shinhanbank          # 시연용 3곳: 수집부터 면접 카드, 결과 파일까지
  python analyze_companies.py skhynix                          # 핵심 기업: 엔진만 돌리고 사람 정답과 비교 (화면에는 안 넣음)
  python analyze_companies.py kakao --skip-fetch               # 이미 받은 글(data/dart)이나 PDF(data/pdf)로
  python analyze_companies.py kakao --skip-fetch --mock        # 가짜 모델로 코드 점검 (인터넷, 키 없이)
  python analyze_companies.py kakao naver shinhanbank --write-screen   # 점검을 통과하면 app/data/results.json에 씀

기업 구분
  - config.yaml의 candidates(시연용): 결과 파일(data/results/ai_promise_data.json)에 넣고, 화면 데이터에 합칠 수 있습니다.
    화면에는 기업별로 "AI 엔진 결과(사람 검토 전)"로 표시됩니다 (data_mode: engine).
  - config.yaml의 companies(핵심, 사람이 공시 원문을 대조한 기업): 화면 데이터에 넣지 않고,
    eval/evaluate.py로 사람 정답과 AI 판정을 비교합니다.
한 기업이 실패해도 다음 기업을 계속하고, 끝에 기업별 표(수집, 약속, 판정, 인용 검사, 시간, 실제로 답한 모델)를 찍습니다.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import traceback

ENGINE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ENGINE)
sys.path.insert(0, ENGINE)

from aipromise.config import company_cfg, load_config, work_dir  # noqa: E402

VERDICT_KO = {"evidence_found": "근거 확인", "partial": "일부 확인", "not_verifiable": "확인 불가",
              "company_reported_not_pursued": "미추진 공시"}


def run_one(cfg, key, mock=False):
    """1~7단계를 돌리고 요약을 돌려줍니다."""
    from aipromise.card import run_card
    from aipromise.collect import run_collect
    from aipromise.extract import run_extract
    from aipromise.judge import run_judge
    from aipromise.llm import LLM

    c = company_cfg(cfg, key)
    work = work_dir(cfg, key)
    llm = LLM(cfg, os.path.join(work, "llm_log.jsonl"), mock=mock)
    collected = run_collect(cfg, c)
    run_extract(cfg, c, llm, work)
    run_judge(cfg, c, llm, work, mock=mock)
    run_card(cfg, c, llm, work)

    with open(os.path.join(work, "judged.json"), encoding="utf-8") as f:
        judged = json.load(f)
    ps = judged.get("promises", [])
    spec = [p for p in ps if p.get("type") == "specific"]
    counts = {v: sum(1 for p in spec if p.get("verdict") == v) for v in VERDICT_KO}
    ev = [e for p in ps for e in p.get("evidence", [])]
    sec_missing = [f"{t} {n}" for t, n, s, e, ns, nk, ok, eok in collected if not ok]
    return {
        "name": c["name"], "specific": len(spec), "directional": len(ps) - len(spec), "counts": counts,
        "evidence": len(ev), "verified": sum(1 for e in ev if e.get("citation_verified") is True),
        "models": judged.get("models_used") or {}, "sections_missing": sec_missing,
        "source": "DART 자동 수집" if any(r.get("text") for r in c["promise_reports"] + c["evidence_reports"]) else "PDF",
    }


def main():
    ap = argparse.ArgumentParser(description="여러 기업 자동 분석 (OpenDART 수집 → 엔진 → 결과 파일)")
    ap.add_argument("companies", nargs="+", help="config.yaml의 기업 이름 (예: kakao naver shinhanbank skhynix)")
    ap.add_argument("--skip-fetch", action="store_true", help="OpenDART 수집을 건너뛰고 이미 받은 글이나 PDF로")
    ap.add_argument("--mock", action="store_true", help="가짜 모델로 코드 점검 (인터넷, 키 없이)")
    ap.add_argument("--write-screen", action="store_true", help="점검을 통과하면 app/data/results.json에 씀")
    ap.add_argument("--config")
    a = ap.parse_args()
    cfg = load_config(a.config)
    core = set(cfg["companies"])

    fetch_failed = []
    if not a.skip_fetch:
        from fetch_dart import fetch
        from aipromise.dart import DartError
        try:
            _, fetch_failed = fetch(cfg, a.companies)
        except DartError as e:
            print(f"OpenDART 수집 멈춤: {e}")
            sys.exit(1)

    results, failed = {}, {}
    for key in a.companies:
        t0 = time.time()
        print(f"\n========== {key} ==========")
        try:
            r = run_one(cfg, key, mock=a.mock)
            r["seconds"] = round(time.time() - t0)
            results[key] = r
        except SystemExit as e:  # 엔진 안의 안내형 멈춤 (파일 없음, 키 없음)
            failed[key] = str(e)
            print(f"[{key}] 멈춤: {e}")
        except Exception as e:
            failed[key] = f"{type(e).__name__}: {e}"
            traceback.print_exc()

    print("\n[기업별 결과]")
    print("기업 | 원문 | 구체적 | 방향성 | 근거 확인 | 일부 확인 | 확인 불가 | 미추진 공시 | 근거 문장(인용 검사 통과) | 시간(초) | 실제로 답한 모델")
    for key, r in results.items():
        c = r["counts"]
        models = ", ".join(f"{k}={v}" for k, v in sorted(r["models"].items())) or "-"
        print(f"{r['name']} | {r['source']} | {r['specific']} | {r['directional']} | {c['evidence_found']} | {c['partial']} | "
              f"{c['not_verifiable']} | {c['company_reported_not_pursued']} | {r['evidence']}({r['verified']}) | {r['seconds']} | {models}")
        if r["sections_missing"]:
            print(f"   (주의) 못 찾은 장: {'; '.join(r['sections_missing'])}")
    for key, why in failed.items():
        print(f"{key} | 실패: {why[:300]}")
    if fetch_failed:
        print(f"(주의) OpenDART에서 보고서를 다 받지 못한 기업: {fetch_failed}")

    screen_keys = [k for k in results if k not in core]
    eval_keys = [k for k in results if k in core]

    if screen_keys:
        from aipromise.export import run_export
        engine_data, problems = run_export(cfg, screen_keys)
        from merge_screen import DEFAULT_SCREEN, merge
        from aipromise.checker import check
        with open(DEFAULT_SCREEN, encoding="utf-8") as f:
            screen = json.load(f)
        out, merge_problems = merge(screen, engine_data, screen_keys)
        errs = merge_problems + check(out, expect_real=False)
        blocking = [e for e in errs if not e.startswith("(주의)")]
        print("\n[화면 데이터 미리 보기] (사람 대조 기업은 그대로 둡니다)")
        for c in out["companies"]:
            mode = "AI 엔진" if c.get("data_mode") == "engine" else ("사람 대조" if c.get("promises") else "준비 중")
            print(f"  {c['id']}: {c['name']} [{mode}] 약속 {len(c.get('promises', []))}개")
        for e in errs:
            print(("  문제: " if e in blocking else "  ") + e)
        if a.write_screen and not blocking:
            with open(DEFAULT_SCREEN, "w", encoding="utf-8") as f:
                f.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
            print(f"화면 데이터에 썼습니다: {DEFAULT_SCREEN}")
        elif a.write_screen:
            print(f"막는 문제 {len(blocking)}개가 있어 화면 데이터에 쓰지 않았습니다.")
        else:
            print("화면 데이터에는 쓰지 않았습니다 (검토 뒤 merge_screen.py --write 또는 --write-screen).")

    for key in eval_keys:
        print(f"\n[사람 정답과 비교] {key}")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "eval", "evaluate.py"), "--companies", key], cwd=ROOT)
        if r.returncode != 0:
            print(f"(주의) {key} 평가가 끝나지 않았습니다 (정답 파일 확인)")

    sys.exit(1 if failed or not results else 0)


if __name__ == "__main__":
    main()
