"""엔진 결과 기업을 화면 데이터에 합치는 도구(engine/merge_screen.py) 검사 (몇 초, API 없이)
실행: python tests/test_merge_screen.py   (마지막 줄 "화면 합치기 검사 통과")
"""
import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from merge_screen import merge  # noqa: E402
from aipromise.checker import check  # noqa: E402


def main():
    problems = []
    screen = json.load(open(os.path.join(ROOT, "app", "data", "results.json"), encoding="utf-8"))
    before = copy.deepcopy(screen)
    sam = [c for c in screen["companies"] if c["id"] == "samsung"][0]
    fake = json.loads(json.dumps(sam).replace("samsung", "kakao"))
    fake["name"] = "카카오"
    fake.pop("check_note", None)
    engine = {"companies": [fake, {"id": "naver", "name": "NAVER", "reports": sam["reports"], "promises": [], "interview_card": {}}]}

    out, msgs = merge(screen, engine, ["kakao", "naver", "nothere"])
    if screen != before:
        problems.append("원래 화면 데이터를 바꿨습니다 (복사본에만 써야 함)")
    k = [c for c in out["companies"] if c["id"] == "kakao"][0]
    if k.get("data_mode") != "engine" or not k.get("promises"):
        problems.append("카카오에 data_mode: engine과 약속이 들어가야 합니다")
    if [c["id"] for c in out["companies"]] != [c["id"] for c in screen["companies"]]:
        problems.append(f"기업 순서가 바뀌었습니다: {[c['id'] for c in out['companies']]}")
    if not any("naver" in m and "약속이 없어" in m for m in msgs) or not any("nothere" in m for m in msgs):
        problems.append(f"약속 없는 기업, 없는 기업 안내가 없습니다: {msgs}")
    if [c for c in out["companies"] if c["id"] == "naver"][0].get("data_mode"):
        problems.append("약속이 없는 NAVER는 바꾸지 않아야 합니다")
    notice = out["meta"].get("notice", "")
    if "카카오는 AI 엔진 결과" not in notice or "삼성전자" not in notice:
        problems.append(f"안내 띠가 섞인 데이터를 사실대로 말하지 않습니다: {notice}")
    if "카카오는 AI가 생성한 분석" not in out["labels"]["disclaimers"][1]:
        problems.append(f"안내 문구 두 번째 줄이 바뀌지 않았습니다: {out['labels']['disclaimers']}")
    blocking = [e for e in check(out, expect_real=False) if not e.startswith("(주의)")]
    if blocking:
        problems.append(f"합친 결과가 화면 규칙 점검을 통과하지 못했습니다: {blocking}")

    if problems:
        print("화면 합치기 검사 실패:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("화면 합치기 검사 통과")


if __name__ == "__main__":
    main()
