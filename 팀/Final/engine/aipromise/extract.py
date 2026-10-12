"""2단계(약속 추출)와 3단계(분류).

- 검색어(AI, 인공지능 등)가 든 문장과 그 앞뒤 문장을 후보로 AI에게 보여 줍니다.
  앞뒤 문장은 뜻을 이해하는 데만 쓰고, 검색어가 없는 문장은 약속으로 고르지 않습니다. (판정기준 v2, 2장)
- AI는 후보의 '번호'만 고르고 구체적/방향성으로 나눕니다. 문장은 원문 그대로 씁니다.
- 결과로 promises.json과, 사람이 정답을 매길 'eval/gold/<기업>_정답매길목록.csv'를 만듭니다.
"""
import csv
import json
import os

from .prompts import EXTRACT_SYSTEM, EXTRACT_USER
from .textutil import normalize

BATCH = 40


def _load(work, key):
    with open(os.path.join(work, f"collected_{key}.json"), encoding="utf-8") as f:
        return json.load(f)


def run_extract(cfg, company, llm, work):
    promises = []
    dropped = []
    for rep_cfg in company["promise_reports"]:
        rep = _load(work, rep_cfg["key"])
        for skey, sec in rep["sections"].items():
            sents = sec["sentences"]
            if not sents:
                continue
            idx = {s["id"]: i for i, s in enumerate(sents)}
            cand_ids = []
            for i, s in enumerate(sents):
                if s["has_keyword"]:
                    for j in (i - 1, i, i + 1):
                        if 0 <= j < len(sents) and sents[j]["id"] not in cand_ids:
                            cand_ids.append(sents[j]["id"])
            cand_ids.sort(key=lambda x: idx[x])
            for b in range(0, len(cand_ids), BATCH):
                batch = cand_ids[b:b + BATCH]
                text = "\n".join(f"{sid}: {sents[idx[sid]]['text']}" for sid in batch)
                data = llm.json("extract", EXTRACT_SYSTEM,
                                EXTRACT_USER.format(company=company["name"], report=rep["title"],
                                                    section=sec["name"], candidates=text),
                                "extract_model")
                for item in data.get("promises", []) or []:
                    sid = str(item.get("id", "")).strip()
                    if sid not in batch:
                        dropped.append({"id": sid, "why": "후보에 없는 번호"})
                        continue
                    s = sents[idx[sid]]
                    if not s.get("has_keyword"):
                        dropped.append({"id": sid, "why": "문장 안에 AI 관련 말 없음 (판정기준 v2)"})
                        continue
                    ptype = item.get("type") if item.get("type") in ("specific", "directional") else "directional"
                    # 인용 검사: 약속 문장이 읽은 장의 원문에 그대로 있는지
                    if normalize(s["text"]) not in sec["norm_text"]:
                        dropped.append({"id": sid, "why": "원문 대조 실패"})
                        continue
                    title = (item.get("title") or "").strip() or s["text"][:25]
                    if any(p["sentence_id"] == sid for p in promises):
                        continue
                    promises.append({
                        "type": ptype, "title": title[:40], "sentence": s["text"], "sentence_id": sid,
                        "source": {"report": rep["title"], "section": sec["name"], "url": rep.get("url", ""),
                                   "page": s["page"]},
                    })
    # 번호 붙이기 (예: samsung-p1, samsung-d1)
    np_, nd = 0, 0
    for p in promises:
        if p["type"] == "specific":
            np_ += 1
            p["id"], n = f"{company['key']}-p{np_}", np_
        else:
            nd += 1
            p["id"], n = f"{company['key']}-d{nd}", nd
        p["_order"] = (0 if p["type"] == "specific" else 1, n)
    promises.sort(key=lambda p: p["_order"])
    for p in promises:
        p.pop("_order", None)

    with open(os.path.join(work, "promises.json"), "w", encoding="utf-8") as f:
        json.dump({"promises": promises, "dropped": dropped}, f, ensure_ascii=False, indent=1)
    gold_path = write_gold_template(cfg, company, promises)

    print(f"\n[2~3단계 약속 추출·분류] {company['name']}")
    print(f"구체적 약속 {np_}개, 방향성 약속 {nd}개 (버린 항목 {len(dropped)}개)")
    for p in promises:
        kind = "구체적" if p["type"] == "specific" else "방향성"
        print(f"  {p['id']} [{kind}] {p['title']}  (p.{p['source']['page']})")
    print(f"→ 정답 매길 목록: {gold_path}")
    return promises


def write_gold_template(cfg, company, promises):
    gold_dir = os.path.join(cfg["paths"]["eval_dir"], "gold")
    os.makedirs(gold_dir, exist_ok=True)
    path = os.path.join(gold_dir, f"{company['key']}_정답매길목록.csv")
    cols = ["번호", "promise_id", "약속 문장", "약속 위치", "분류", "근거 문장", "근거 위치", "판정", "걸린 시간(분)", "메모"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for n, p in enumerate(promises, 1):
            loc = f"{p['source']['report']}, {p['source']['section']}, p.{p['source']['page']}"
            kind = "구체적" if p["type"] == "specific" else "방향성"
            w.writerow([n, p["id"], p["sentence"], loc, kind, "", "", "", "", ""])
    return path
