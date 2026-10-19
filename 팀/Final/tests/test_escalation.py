"""두 번째 판정(escalation)과 대체 모델(fallback) 검사 (API 키, 인터넷 없이 몇 초).

1. 첫 판정이 '일부 확인'이면 escalation_model로 한 번 더 판정하고, 두 판정을 결과에 남기는지
2. 두 번째 판정이 근거 번호 없이 '근거 확인'을 내면 첫 판정을 그대로 두는지
3. escalation_model을 비우면 두 번째 판정을 하지 않는지
4. 설정한 모델 호출이 실패하면 fallback_model로 넘어가고, 실제로 답한 모델을 기록하는지
실행: python tests/test_escalation.py  (마지막 줄 "두 번째 판정 검사 통과")
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from aipromise.judge import judge_one  # noqa: E402
from aipromise.llm import LLM  # noqa: E402
from aipromise.textutil import normalize  # noqa: E402

SENT = "AI 서버용 고용량 메모리 공급을 확대하였습니다."


class Corpus:
    def __init__(self):
        self.by_id = {"s1": {"text": SENT, "report": "2025 사업보고서", "section": "II. 사업의 내용", "page": 3,
                             "url": "https://dart.fss.or.kr/x", "report_key": "y2025", "section_key": "II"}}


class Retriever:
    def search(self, query):
        return ["s1"]


class ScriptedLLM:
    """작업 이름별로 정해 둔 답을 돌려주는 가짜 모델."""
    def __init__(self, answers, escalation_model="model-big"):
        self.cfg = {"llm": {"escalation_model": escalation_model, "escalate_verdicts": ["partial"]}}
        self.answers = answers
        self.calls = []
        self.last_model = None
        self.used_models = {}

    def json(self, task, system, user, model_key, retries=2):
        self.calls.append((task, model_key))
        self.last_model = {"judge_model": "model-main", "escalation_model": "model-big"}[model_key]
        return self.answers[task]


def run(llm):
    p = {"id": "x-p1", "type": "specific", "title": "고용량 메모리 공급 확대", "sentence": "고용량 메모리 공급을 확대할 계획입니다.",
         "source": {"report": "2024 사업보고서", "section": "II. 사업의 내용"}}
    norm = {("y2025", "II"): normalize("앞 문장. " + SENT + " 뒤 문장.")}
    return judge_one(p, Corpus(), Retriever(), norm, llm, 3, ["2025 사업보고서"])


def main():
    problems = []
    partial = {"verdict": "partial", "evidence_ids": ["s1"], "reason": "관련 활동은 확인되지만 범위가 다릅니다.", "new_query": ""}

    # 1) 일부 확인 → 두 번째 판정 근거 확인 (근거 번호 있음) → 채택
    llm = ScriptedLLM({"judge": partial, "judge_escalation": {"verdict": "evidence_found", "evidence_ids": ["s1"],
                                                              "reason": "약속한 공급 확대가 후속 공시에 적혀 있습니다.", "new_query": ""}})
    r = run(llm)
    esc = r.get("escalation") or {}
    if [c[0] for c in llm.calls] != ["judge", "judge_escalation"]:
        problems.append(f"호출 순서가 다릅니다: {llm.calls}")
    if not (r["verdict"] == "evidence_found" and esc.get("first_verdict") == "partial" and esc.get("second_verdict") == "evidence_found"
            and esc.get("adopted") is True and esc.get("model") == "model-big" and r.get("judge_model_used") == "model-main"):
        problems.append(f"두 번째 판정 채택이 다릅니다: verdict={r['verdict']} escalation={esc} used={r.get('judge_model_used')}")
    if not (r["evidence"] and r["evidence"][0]["citation_verified"] is True):
        problems.append("두 번째 판정의 근거가 인용 검사를 통과하지 못했습니다")

    # 2) 두 번째 판정이 근거 번호 없이 근거 확인 → 첫 판정 유지
    llm = ScriptedLLM({"judge": partial, "judge_escalation": {"verdict": "evidence_found", "evidence_ids": [], "reason": "x", "new_query": ""}})
    r = run(llm)
    if not (r["verdict"] == "partial" and (r.get("escalation") or {}).get("adopted") is False):
        problems.append(f"근거 번호 없는 두 번째 판정을 채택했습니다: {r['verdict']} {r.get('escalation')}")

    # 3) escalation_model 비움 → 두 번째 판정 없음
    llm = ScriptedLLM({"judge": partial}, escalation_model="")
    r = run(llm)
    if len(llm.calls) != 1 or "escalation" in r:
        problems.append(f"escalation_model이 비었는데 두 번째 판정을 했습니다: {llm.calls}")

    # 4) 대체 모델: 첫 모델 호출이 실패하면 fallback_model로 넘어감
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {"llm": {"judge_model": "model-new", "fallback_model": "model-old", "temperature": None}}
        real = LLM(cfg, os.path.join(tmp, "log.jsonl"), mock=True)

        class Boom:
            def invoke(self, msgs):
                raise RuntimeError("model_not_found")

        class Ok:
            def invoke(self, msgs):
                class R:
                    content = json.dumps({"verdict": "partial"})
                return R()

        real.mock = False  # 가짜 클라이언트로 실제 호출 경로를 탑니다
        real._clients = {"model-new": Boom(), "model-old": Ok()}
        data = real.json("judge", "s", "u", "judge_model")
        logs = [json.loads(x) for x in open(os.path.join(tmp, "log.jsonl"), encoding="utf-8")]
        if data != {"verdict": "partial"} or real.last_model != "model-old":
            problems.append(f"대체 모델로 넘어가지 않았습니다: {data} {real.last_model}")
        if not (logs and logs[0].get("error") and logs[0]["model"] == "model-new" and logs[-1]["model"] == "model-old"):
            problems.append(f"실패한 호출과 대체 모델 호출이 기록되지 않았습니다: {[(l['model'], bool(l.get('error'))) for l in logs]}")
        if real.used_models.get("judge") != {"model-old"}:
            problems.append(f"실제로 답한 모델 기록이 다릅니다: {real.used_models}")

    if problems:
        print("두 번째 판정 검사 실패:")
        for x in problems:
            print(" -", x)
        sys.exit(1)
    print("두 번째 판정 검사 통과")


if __name__ == "__main__":
    main()
