"""7단계: 면접 카드 (핵심 이슈 3개, 답변 소재 3개, 역질문 2개).

AI가 쓴 카드를 코드로 다시 점검합니다.
- 답변 소재는 '근거 확인'과 '일부 확인' 약속만, 근거 링크는 데이터에서 붙입니다.
- 단정 표현이 있거나 개수가 모자라면 규칙 방식으로 채웁니다. (--rule-card로 규칙 방식만 쓸 수도 있습니다)
"""
import json
import os

from .prompts import CARD_SYSTEM, CARD_USER, VERDICT_KO
from .textutil import find_forbidden

PRIORITY = ["evidence_found", "partial", "company_reported_not_pursued", "not_verifiable"]


def _spec(judged):
    return [j for j in judged if j["type"] == "specific"]


def rule_card(judged):
    spec = _spec(judged)
    by = {v: [j for j in spec if j["verdict"] == v] for v in PRIORITY}
    issues = []
    for v in PRIORITY:
        for j in by[v]:
            if len(issues) >= 3:
                break
            tail = {
                "evidence_found": "후속 공시에서 실행이 확인됨",
                "partial": "후속 공시에서 일부만 확인됨",
                "company_reported_not_pursued": "회사가 추진하지 않는다고 공시함",
                "not_verifiable": "후속 공시에서 실행 내용을 찾기 어려움",
            }[v]
            issues.append({"text": f"{j['title']}: {tail} ({VERDICT_KO[v]})", "promise_id": j["id"]})
    talking = []
    for j in by["evidence_found"] + by["partial"]:
        if len(talking) >= 3:
            break
        ev = j["evidence"][0]
        snippet = ev["sentence"] if len(ev["sentence"]) <= 70 else ev["sentence"][:70] + "…"
        talking.append({
            "text": f"공시에서 '{j['title']}' 관련 내용을 확인했습니다. 근거: \"{snippet}\"",
            "promise_id": j["id"], "evidence_url": ev["source"]["url"],
        })
    questions = []
    for j in by["not_verifiable"] + by["partial"]:
        if len(questions) >= 2:
            break
        if j["verdict"] == "not_verifiable":
            text = f"'{j['title']}' 계획은 공시에서 후속 내용을 확인하기 어려웠습니다. 현재 추진 방향이 궁금합니다."
        else:
            text = f"'{j['title']}' 관련해서는 일부 진행만 확인했습니다. 이후 확대 계획이 궁금합니다."
        questions.append({"text": text, "promise_id": j["id"]})
    return {"issues": issues, "talking_points": talking, "questions": questions}


def _clean(card, judged):
    spec = {j["id"]: j for j in _spec(judged)}
    out = {"issues": [], "talking_points": [], "questions": []}
    for item in card.get("issues") or []:
        pid, text = item.get("promise_id"), (item.get("text") or "").strip()
        if pid in spec and text and not find_forbidden(text):
            out["issues"].append({"text": text, "promise_id": pid})
    for item in card.get("talking_points") or []:
        pid, text = item.get("promise_id"), (item.get("text") or "").strip()
        j = spec.get(pid)
        if j and j["verdict"] in ("evidence_found", "partial") and j["evidence"] and text and not find_forbidden(text):
            out["talking_points"].append({"text": text, "promise_id": pid, "evidence_url": j["evidence"][0]["source"]["url"]})
    for item in card.get("questions") or []:
        pid, text = item.get("promise_id"), (item.get("text") or "").strip()
        if pid in spec and text and not find_forbidden(text):
            out["questions"].append({"text": text, "promise_id": pid})
    return out


def _fill(card, rule, limits):
    for key, n in limits.items():
        have = {x["promise_id"] for x in card[key]}
        for x in rule[key]:
            if len(card[key]) >= n:
                break
            if x["promise_id"] not in have:
                card[key].append(x)
                have.add(x["promise_id"])
        card[key] = card[key][:n]
    return card


def run_card(cfg, company, llm, work, rule_only=False):
    with open(os.path.join(work, "judged.json"), encoding="utf-8") as f:
        judged = json.load(f)["promises"]
    rule = rule_card(judged)
    limits = {"issues": 3, "talking_points": 3, "questions": 2}
    how = "규칙 방식"
    if rule_only:
        card = rule
    else:
        items = []
        for j in _spec(judged):
            ev = " / ".join(e["sentence"] for e in j["evidence"]) or "(근거 없음)"
            items.append(f"- {j['id']} | {j['title']} | 판정: {j['verdict']} | 이유: {j['reason']} | 근거: {ev}")
        try:
            raw = llm.json("card", CARD_SYSTEM, CARD_USER.format(company=company["name"], items="\n".join(items)),
                           "card_model")
            card = _fill(_clean(raw, judged), rule, limits)
            how = "AI 작성 + 코드 점검"
        except Exception as e:  # 모델 오류가 나도 카드는 만들어지게
            print(f"  (면접 카드 AI 작성 실패, 규칙 방식으로 대신함: {e})")
            card = rule
    with open(os.path.join(work, "card.json"), "w", encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False, indent=1)
    print(f"\n[7단계 면접 카드] {company['name']} ({how})")
    print(f"핵심 이슈 {len(card['issues'])}개, 답변 소재 {len(card['talking_points'])}개, 역질문 {len(card['questions'])}개")
    return card
