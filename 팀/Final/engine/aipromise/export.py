"""결과 파일 만들기: 화면이 읽는 sample_data.json과 같은 모양으로 저장합니다.

화면에 필요 없는 작업 기록(검색 기록, 문장 번호, 표시)은 빼고,
검색 기록은 data/results/search_log.json에 따로 남깁니다 (보고서·발표의 예시 1건용).
"""
import datetime
import json
import os
import shutil

from .checker import check

SCREEN_PROMISE_KEYS = ("id", "type", "title", "sentence", "source", "verdict", "reason", "evidence", "search_attempts")


def _screen_promise(j):
    p = {k: j.get(k) for k in SCREEN_PROMISE_KEYS}
    p["evidence"] = [{"sentence": e["sentence"], "source": e["source"], "citation_verified": e["citation_verified"]}
                     for e in j.get("evidence", [])]
    return p


def run_export(cfg, company_keys, copy_to=None):
    from .config import company_cfg, work_dir
    with open(cfg["paths"]["labels_file"], encoding="utf-8") as f:
        labels = json.load(f)
    companies, logs, skipped = [], {}, []
    for key in company_keys:
        c = company_cfg(cfg, key)
        work = work_dir(cfg, key)
        jp, cp = os.path.join(work, "judged.json"), os.path.join(work, "card.json")
        if not os.path.exists(jp):
            skipped.append(f"{c['name']}: judged.json 없음 (judge 단계 먼저)")
            continue
        with open(jp, encoding="utf-8") as f:
            judged = json.load(f)["promises"]
        card = {"issues": [], "talking_points": [], "questions": []}
        if os.path.exists(cp):
            with open(cp, encoding="utf-8") as f:
                card = json.load(f)
        else:
            skipped.append(f"{c['name']}: card.json 없음 (면접 카드는 빈 채로 내보냄)")
        companies.append({
            "id": key, "name": c["name"],
            "reports": {
                "promise": [{"title": r["title"], "url": r.get("url", "")} for r in c["promise_reports"]],
                "evidence": [{"title": r["title"], "url": r.get("url", "")} for r in c["evidence_reports"]],
            },
            "promises": [_screen_promise(j) for j in judged],
            "interview_card": card,
        })
        if c.get("check_note"):  # 선택: 기업별 검증 안내 (예: 시연용 기업)
            companies[-1]["check_note"] = c["check_note"]
        logs[key] = [{"id": j["id"], "title": j["title"], "verdict": j["verdict"], "search_log": j.get("search_log", []),
                      "flags": j.get("flags", [])} for j in judged]

    data = {
        "meta": {"is_sample": False, "notice": "", "schema_version": "0.1",
                 "updated": datetime.date.today().isoformat(),
                 "engine": {k: cfg["llm"][k] for k in ("extract_model", "judge_model", "card_model", "embed_model")}},
        "labels": labels,
        "companies": companies,
    }
    out = cfg["paths"]["results_file"]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with open(os.path.join(os.path.dirname(out), "search_log.json"), "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=1)

    print(f"\n[결과 파일] {out}")
    for s in skipped:
        print("  ※", s)
    problems = check(data)
    if problems:
        print("화면 점검에서 문제 발견:")
        for p in problems:
            print("  -", p)
    else:
        print("화면 점검 통과: 항목 이름, 판정 값, 인용 표시, 면접 카드 연결이 모두 맞습니다.")
    blocking = [p for p in problems if not p.startswith("(주의)")]
    if copy_to and blocking:
        print(f"화면 점검 문제 {len(blocking)}개가 있어 화면 데이터 자리에 복사하지 않았습니다: {copy_to}")
    elif copy_to:
        os.makedirs(os.path.dirname(copy_to), exist_ok=True)
        shutil.copyfile(out, copy_to)
        print(f"화면 데이터 자리에 복사함: {copy_to}")
    return data, problems
