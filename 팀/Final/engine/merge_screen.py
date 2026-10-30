"""엔진 결과 기업을 화면 데이터에 합치기 (사람이 원문을 검토한 기업은 그대로 둠)

사용 예 (engine 폴더에서):
  python merge_screen.py --engine ../data/results/ai_promise_data.json --companies kakao shinhanbank naver          # 미리 보기만
  python merge_screen.py --engine ../data/results/ai_promise_data.json --companies kakao shinhanbank naver --write  # 화면 데이터에 씀

하는 일
1. 엔진 결과 파일에서 고른 기업만 가져와 화면 데이터(app/data/results.json)의 같은 id 자리에 넣습니다(없으면 뒤에 붙임).
   가져온 기업에는 data_mode: "engine"을 붙여, 화면이 기업별로 "AI 엔진 결과(사람 검토 전)"라고 표시합니다.
2. 화면 데이터에 사람이 원문을 검토한 기업과 엔진 결과 기업이 섞이면, 맨 위 안내 띠(meta.notice)와 안내 문구 두 번째 줄을
   기업 이름으로 나눠 사실대로 고칩니다.
3. 화면 규칙 점검(checker)을 돌려, 막는 문제가 있으면 쓰지 않습니다. 약속이 없는 기업은 넣지 않습니다.
"""
import argparse
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aipromise.checker import check  # noqa: E402

DEFAULT_SCREEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "data", "results.json")


def names(companies):
    return ", ".join(c["name"] for c in companies)


def merge(screen, engine, ids):
    out = copy.deepcopy(screen)
    by_id = {c["id"]: c for c in engine.get("companies", [])}
    problems = []
    for cid in ids:
        c = by_id.get(cid)
        if c is None:
            problems.append(f"엔진 결과 파일에 '{cid}'가 없습니다")
            continue
        if not c.get("promises"):
            problems.append(f"'{cid}'에 약속이 없어 넣지 않습니다 (엔진 실행 결과 확인)")
            continue
        c = copy.deepcopy(c)
        c["data_mode"] = "engine"
        pos = [i for i, x in enumerate(out["companies"]) if x["id"] == cid]
        if pos:
            out["companies"][pos[0]] = c
        else:
            out["companies"].append(c)

    ready = [c for c in out["companies"] if c.get("promises")]
    human = [c for c in ready if c.get("data_mode") != "engine" and out.get("meta", {}).get("data_mode") == "human_reviewed_demo"]
    eng = [c for c in ready if c.get("data_mode") == "engine"]
    if human and eng:
        out["meta"]["notice"] = (f"{names(human)}는 사람이 원문을 읽고 판정했고(사람 원문 검토 완료), {names(eng)}는 AI 엔진 결과(사람 검토 전)입니다. "
                                 "엔진 정확도 평가는 따로 구분합니다.")
        d = out.get("labels", {}).get("disclaimers", [])
        if len(d) == 2:
            d[1] = f"{names(human)}는 사람이 공시 원문을 읽고 판정했고, {names(eng)}는 AI가 생성한 분석입니다."
    return out, problems


def main():
    ap = argparse.ArgumentParser(description="엔진 결과 기업을 화면 데이터에 합치기")
    ap.add_argument("--engine", required=True, help="run.py export로 만든 파일 (예: ../data/results/ai_promise_data.json)")
    ap.add_argument("--screen", default=DEFAULT_SCREEN, help="화면 데이터 (기본: ../app/data/results.json)")
    ap.add_argument("--companies", nargs="+", required=True)
    ap.add_argument("--write", action="store_true", help="문제가 없으면 화면 데이터에 씀 (없으면 미리 보기만)")
    a = ap.parse_args()

    with open(a.screen, encoding="utf-8") as f:
        screen = json.load(f)
    with open(a.engine, encoding="utf-8") as f:
        engine = json.load(f)
    out, problems = merge(screen, engine, a.companies)
    errs = problems + check(out, expect_real=False)
    blocking = [e for e in errs if not e.startswith("(주의)")]
    for c in out["companies"]:
        mode = "AI 엔진" if c.get("data_mode") == "engine" else ("사람 검토" if c.get("promises") else "준비 중")
        print(f"  {c['id']}: {c['name']} [{mode}] 약속 {len(c.get('promises', []))}개")
    for e in errs:
        print(("  문제: " if e in blocking else "  ") + e)
    if blocking:
        print(f"막는 문제 {len(blocking)}개가 있어 쓰지 않았습니다.")
        sys.exit(1)
    if a.write:
        with open(a.screen, "w", encoding="utf-8") as f:
            f.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
        print(f"화면 데이터에 썼습니다: {a.screen}")
    else:
        print("미리 보기만 했습니다. 쓰려면 --write를 붙이세요.")


if __name__ == "__main__":
    main()
