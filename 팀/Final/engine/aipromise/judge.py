"""4단계(근거 검색), 5단계(판정), 6단계(인용 검사).

Agent처럼 움직이는 부분: 근거를 못 찾으면 AI가 새 검색어를 정해 최대 2번 더 찾습니다(총 3번).
인용 검사: AI가 고른 근거 문장이 읽은 장의 원문에 그대로 있는지 코드로 확인합니다.
근거가 필요한 판정인데 통과한 근거가 없으면 '공시에서 확인 불가'로 낮추고 기록을 남깁니다.
10/19 두 번째 판정: 설정(llm.escalate_verdicts, 기본 '일부 확인')에 해당하는 판정은 llm.escalation_model로
같은 후보를 한 번 더 판정합니다. 두 판정과 실제로 답한 모델을 결과(escalation, judge_model_used)에 남깁니다.
"""
import json
import os

from .prompts import JUDGE_SYSTEM, JUDGE_USER, RELATED_SYSTEM, RELATED_USER, VERDICT_KO
from .retrieve import Corpus, HybridRetriever
from .textutil import normalize, find_forbidden

VERDICTS = ("evidence_found", "partial", "not_verifiable", "company_reported_not_pursued")
NEED_EVIDENCE = ("evidence_found", "partial", "company_reported_not_pursued")

SAFE_REASON = {
    "evidence_found": "약속한 대상이 후속 공시에 실행한 것으로 적혀 있습니다. 근거 문장을 함께 확인해 주세요.",
    "partial": "관련 활동은 후속 공시에서 확인됩니다. 다만 범위, 시점, 수치가 약속과 다르거나 분명하지 않습니다.",
    "company_reported_not_pursued": "회사가 후속 공시에 이 일을 추진하지 않고 있다고 직접 적었습니다.",
}


def _load(work, key):
    with open(os.path.join(work, f"collected_{key}.json"), encoding="utf-8") as f:
        return json.load(f)


def _cand_text(corpus, ids):
    rows = []
    for sid in ids:
        s = corpus.by_id[sid]
        page = f"p.{s['page']}" if s.get("page") else "-"   # DART 자동 수집 글은 쪽 번호가 없습니다
        rows.append(f"{sid} | {s['report']} | {s['section']} | {page} | {s['text']}")
    return "\n".join(rows)


def _verify(corpus, norm_by_sec, ids):
    out = []
    for sid in ids:
        s = corpus.by_id[sid]
        ok = normalize(s["text"]) in norm_by_sec[(s["report_key"], s["section_key"])]
        out.append({
            "sentence": s["text"],
            "source": {"report": s["report"], "section": s["section"], "url": s["url"], "page": s["page"]},
            "citation_verified": ok, "sentence_id": sid,
        })
    return out


def _not_found_reason(evid_titles, attempts):
    r = f"읽은 공시 범위({', '.join(evid_titles)})에서 관련 내용을 찾지 못했습니다."
    if attempts > 1:
        r += f" 검색어를 바꿔 {attempts - 1}번 다시 찾았지만 결과가 같았습니다."
    return r


def judge_one(p, corpus, retriever, norm_by_sec, llm, max_attempts, evid_titles):
    queries = [f"{p['title']} {p['sentence']}"]
    log, data, ev_ids, verdict = [], {}, [], "not_verifiable"
    for attempt in range(1, max_attempts + 1):
        cand = retriever.search(queries[-1])
        data = llm.json("judge", JUDGE_SYSTEM, JUDGE_USER.format(
            sentence=p["sentence"], title=p["title"], report=p["source"]["report"],
            section=p["source"]["section"], queries=" / ".join(queries), candidates=_cand_text(corpus, cand)),
            "judge_model")
        verdict = data.get("verdict") if data.get("verdict") in VERDICTS else "not_verifiable"
        ev_ids = [x for x in (data.get("evidence_ids") or []) if x in cand][:3]
        log.append({"attempt": attempt, "query": queries[-1], "candidates": cand[:12],
                    "verdict": verdict, "evidence_ids": ev_ids})
        if verdict != "not_verifiable" or attempt == max_attempts:
            break
        nq = (data.get("new_query") or "").strip()
        if not nq or nq in queries:
            nq = p["title"] if p["title"] not in queries else ""
        if not nq:
            break
        queries.append(nq)
    judge_model_used = llm.last_model

    # 두 번째 판정: 경계가 애매한 판정만 상위 모델로 다시 봅니다 (비용을 아끼려고 전부 하지 않음)
    escalation = None
    llm_cfg = llm.cfg.get("llm", {})
    if llm_cfg.get("escalation_model") and verdict in (llm_cfg.get("escalate_verdicts") or []):
        data2 = llm.json("judge_escalation", JUDGE_SYSTEM, JUDGE_USER.format(
            sentence=p["sentence"], title=p["title"], report=p["source"]["report"],
            section=p["source"]["section"], queries=" / ".join(queries), candidates=_cand_text(corpus, cand)),
            "escalation_model")
        v2 = data2.get("verdict") if data2.get("verdict") in VERDICTS else None
        ids2 = [x for x in (data2.get("evidence_ids") or []) if x in cand][:3]
        # 근거가 필요한 판정인데 근거 번호를 안 줬으면 첫 판정을 그대로 둡니다 (인용 검사에서 억지로 낮아지지 않게)
        adopted = bool(v2) and (v2 == "not_verifiable" or bool(ids2))
        escalation = {"model": llm.last_model, "first_verdict": verdict, "second_verdict": v2, "adopted": adopted}
        if adopted:
            verdict, data, ev_ids = v2, data2, ids2

    attempts = len(log)
    flags = []
    evidence = _verify(corpus, norm_by_sec, ev_ids)
    verified = [e for e in evidence if e["citation_verified"]]
    if len(verified) < len(evidence):
        flags.append("인용 검사 실패 근거 제외")
    if verdict in NEED_EVIDENCE and not verified:
        flags.append("근거 없음으로 확인 불가로 낮춤")
        verdict = "not_verifiable"

    if verdict == "not_verifiable":
        evidence, reason = [], _not_found_reason(evid_titles, attempts)
    else:
        evidence = verified
        reason = (data.get("reason") or "").strip()
        bad = find_forbidden(reason)
        if bad or not reason:
            flags.append(f"판정 이유 교체({', '.join(bad) or '비어 있음'})")
            reason = SAFE_REASON[verdict]
    out = {**p, "verdict": verdict, "reason": reason, "evidence": evidence,
           "search_attempts": attempts, "search_log": log, "flags": flags, "judge_model_used": judge_model_used}
    if escalation:
        out["escalation"] = escalation
    return out


def related_one(p, corpus, retriever, norm_by_sec, llm):
    cand = retriever.search(f"{p['title']} {p['sentence']}")
    data = llm.json("related", RELATED_SYSTEM, RELATED_USER.format(
        sentence=p["sentence"], candidates=_cand_text(corpus, cand)), "judge_model")
    ids = [x for x in (data.get("related_ids") or []) if x in cand][:2]
    evidence = [e for e in _verify(corpus, norm_by_sec, ids) if e["citation_verified"]]
    return {**p, "verdict": None, "reason": None, "evidence": evidence, "search_attempts": 1,
            "search_log": [{"attempt": 1, "query": f"{p['title']} {p['sentence']}", "candidates": cand[:12],
                            "related_ids": ids}], "flags": []}


def run_judge(cfg, company, llm, work, mock=False, limit=None):
    with open(os.path.join(work, "promises.json"), encoding="utf-8") as f:
        promises = json.load(f)["promises"]
    if limit:
        promises = [p for p in promises if p["type"] == "specific"][:limit]
        print(f"(시험 실행: 구체적 약속 {len(promises)}건만 판정합니다. 방향성 약속은 건너뜁니다. 전체 판정은 --limit 없이 다시 실행하세요)")
    reps = [_load(work, r["key"]) for r in company["evidence_reports"]]
    corpus = Corpus(reps)
    norm_by_sec = {(r["report_key"], k): s["norm_text"] for r in reps for k, s in r["sections"].items()}
    retriever = HybridRetriever(cfg, company["key"], corpus, work, mock=mock)
    evid_titles = [r["title"] for r in reps]
    max_attempts = cfg["retrieval"].get("max_attempts", 3)

    judged = []
    for p in promises:
        if p["type"] == "specific":
            judged.append(judge_one(p, corpus, retriever, norm_by_sec, llm, max_attempts, evid_titles))
        else:
            judged.append(related_one(p, corpus, retriever, norm_by_sec, llm))
    used = {k: sorted(v) for k, v in llm.used_models.items()}
    with open(os.path.join(work, "judged.json"), "w", encoding="utf-8") as f:
        json.dump({"retrieval_mode": retriever.mode, "models_used": used, "promises": judged}, f, ensure_ascii=False, indent=1)

    spec = [j for j in judged if j["type"] == "specific"]
    counts = {v: sum(1 for j in spec if j["verdict"] == v) for v in VERDICTS}
    print(f"\n[4~6단계 근거 검색·판정·인용 검사] {company['name']} (검색: {retriever.mode})")
    print("구체적 약속 " + str(len(spec)) + "개 중 " + ", ".join(f"{VERDICT_KO[v]} {counts[v]}" for v in VERDICTS))
    for j in judged:
        tag = VERDICT_KO.get(j["verdict"], "방향성") if j["verdict"] else "방향성"
        extra = f"  ※ {'; '.join(j['flags'])}" if j["flags"] else ""
        esc = j.get("escalation")
        if esc:
            v1, v2 = VERDICT_KO.get(esc["first_verdict"], esc["first_verdict"]), VERDICT_KO.get(esc["second_verdict"], esc["second_verdict"])
            extra += f"  ※ 두 번째 판정({esc['model']}): {v1} → {v2}{'' if esc['adopted'] else ' (근거 번호가 없어 첫 판정 유지)'}"
        print(f"  {j['id']} [{tag}] 검색 {j['search_attempts']}번, 근거 {len(j['evidence'])}개{extra}")
    print("실제로 답한 모델: " + ", ".join(f"{k} {'/'.join(v)}" for k, v in used.items()))
    return judged
