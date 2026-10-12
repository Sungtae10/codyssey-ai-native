"""AI 판정 평가: 사람이 만든 합의 정답과 AI 판정을 비교해 결과표를 만듭니다.

한 번 실행하면 결과표가 다시 나옵니다 (재현 가능).

  python eval/evaluate.py                       # 기본: samsung, skhynix / samsung은 '개발에 쓴 기업'
  python eval/evaluate.py --companies skhynix   # 한 기업만

필요한 파일 (eval/gold 폴더)
  <기업>_김성태.csv, <기업>_서원.csv   두 사람이 같은 약속 목록에 따로 매긴 판정 (일치도 계산용)
  <기업>_합의.csv                     판정이 다른 건을 합의해 정한 최종 정답
  <기업>_사람약속목록.csv (선택)       사람이 직접 찾은 약속 문장 ('약속 문장' 칸) → 약속을 찾은 비율
                                      없으면 promise_id 칸이 빈 <기업>_서원.csv(서원님이 직접 찾은 목록)를 대신 씁니다.
AI 판정은 data/work/<기업>/judged.json에서 읽습니다.

정답과 AI 약속 맞추기
  - promise_id가 있으면 번호로 맞춥니다. (엔진의 '정답매길목록.csv'를 복사해 판정한 경우)
  - promise_id가 없으면 '약속 문장'으로 맞춥니다. (서원님이 직접 찾은 목록에 판정한 경우)
    띄어쓰기를 무시하고, 한쪽이 다른 쪽을 포함하거나 비슷한 정도가 0.6 이상이면 같은 약속으로 봅니다.
  - 사람은 구체적으로 봤는데 AI가 방향성으로 둔 약속은 AI 판정이 없어 판정 비교에서 빼고,
    errors_<기업>.csv에 원인 '분류가 다름'으로 적습니다. AI가 찾지 못한 약속도 판정 비교에서 빠집니다.

약속을 찾은 비율 (판정기준 v2, 2장)
  - 사람 약속 목록 중 문장 안에 AI 관련 말(엔진과 같은 검색어)이 없는 문장은 약속이 아니므로 비율 계산에서 빼고,
    뺀 개수를 결과표에 따로 적습니다. (예: 연습 5번 문장)

CSV 읽기 (read_table)
  - 엑셀의 'CSV UTF-8', 구글 시트에서 받은 CSV, 엑셀의 그냥 'CSV'(cp949)를 모두 읽습니다.
  - 맨 위에 안내 줄이 있어도 됩니다. 칸 이름 줄은 '번호', 'promise_id', '약속 문장', '판정' 중 하나가 든 첫 줄입니다.
  - 칸 이름은 띄어쓰기와 괄호 설명을 무시하고 맞춥니다. (예: '약속 문장 (원문 그대로)'도 '약속 문장'으로 읽음)
  - 번호 칸이 '예'로 시작하는 형식 예시 줄은 뺍니다. (공유 폴더의 연습5건 시트 형식)

만드는 파일 (eval/results 폴더)
  results.md, results.json, confusion_<기업>.csv, errors_<기업>.csv(틀린 건 목록, 원인 칸을 채워 분석)
"""
import argparse
import csv
import difflib
import io
import json
import math
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "engine"))
from aipromise.textutil import DEFAULT_KEYWORDS, keyword_regex  # noqa: E402  엔진과 같은 검색어 규칙

LABELS = ["evidence_found", "partial", "not_verifiable", "company_reported_not_pursued"]
KO = {"evidence_found": "근거 확인", "partial": "일부 확인", "not_verifiable": "확인 불가",
      "company_reported_not_pursued": "미추진 공시"}
MAP = {"근거 확인": "evidence_found", "일부 확인": "partial", "공시에서 확인 불가": "not_verifiable",
       "확인 불가": "not_verifiable", "회사가 미추진으로 공시": "company_reported_not_pursued",
       "미추진 공시": "company_reported_not_pursued"}
MAP.update({k: k for k in LABELS})
NEED_EVIDENCE = ("evidence_found", "partial", "company_reported_not_pursued")


def norm(t):
    t = unicodedata.normalize("NFKC", t or "")
    return re.sub(r"\s+", "", t)


# 칸 이름 맞추기: 띄어쓰기, 괄호 설명, 영문 대소문자를 무시한 이름 → 코드가 쓰는 이름
COLS = {"번호": "번호", "promise_id": "promise_id", "약속문장": "약속 문장", "약속위치": "약속 위치",
        "분류": "분류", "근거문장": "근거 문장", "근거위치": "근거 위치", "판정": "판정",
        "걸린시간": "걸린 시간(분)", "메모": "메모"}
HEADER_KEYS = ("번호", "promise_id", "약속문장", "판정")


def _col_key(name):
    t = unicodedata.normalize("NFKC", name or "")
    t = re.sub(r"\([^)]*\)", "", t)
    return re.sub(r"\s+", "", t).lower()


def read_table(path):
    """CSV를 읽어 줄마다 {칸 이름: 값} 목록으로 돌려줍니다. 읽는 규칙은 맨 위 설명을 봐 주세요."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp949")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    start = next((i for i, r in enumerate(rows) if any(_col_key(c) in HEADER_KEYS for c in r)), None)
    if start is None:
        print(f"(주의) 칸 이름 줄을 찾지 못했습니다: {path}")
        return []
    names = [COLS.get(_col_key(c), c.strip()) for c in rows[start]]
    out = []
    for r in rows[start + 1:]:
        if not any(c.strip() for c in r):
            continue
        row = dict(zip(names, [c.strip() for c in r] + [""] * (len(names) - len(r))))
        if row.get("번호", "").startswith("예"):
            continue
        out.append(row)
    return out


def read_gold_rows(path):
    """판정이 매겨진 구체적 약속 줄 목록: [{pid, sentence, label}] (판정 칸이 빈 줄과 방향성은 뺌)"""
    if not os.path.exists(path):
        return None
    out = []
    for row in read_table(path):
        lab = MAP.get(row.get("판정", ""))
        pid, sent = row.get("promise_id", ""), row.get("약속 문장", "")
        if lab and row.get("분류", "") != "방향성" and (pid or sent):
            out.append({"pid": pid, "sentence": sent, "label": lab})
    return out


def gold_key(r):
    """번호가 있으면 번호, 없으면 정규화한 약속 문장 (두 사람이 같은 목록에 판정했을 때 서로 맞춰짐)"""
    return r["pid"] or "s:" + norm(r["sentence"])


def read_gold(path):
    """약속 → 판정 코드"""
    rows = read_gold_rows(path)
    if rows is None:
        return None
    return {gold_key(r): r["label"] for r in rows}


def match_promise(sentence, ai_norm):
    """사람 약속 문장과 같은 AI 약속을 찾습니다. ai_norm: [(약속, 정규화한 문장)]. 못 찾으면 None."""
    hn = norm(sentence)
    if not hn:
        return None
    best, best_r = None, 0.0
    for p, x in ai_norm:
        if not x:
            continue
        if hn in x or x in hn:
            return p
        r = difflib.SequenceMatcher(None, hn, x).ratio()
        if r >= 0.6 and r > best_r:
            best, best_r = p, r
    return best


def wilson(k, n, z=1.959964):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def macro_f1(pairs):
    labels = sorted({g for g, _ in pairs} | {a for _, a in pairs}, key=LABELS.index)
    f1s = {}
    for lab in labels:
        tp = sum(1 for g, a in pairs if g == lab and a == lab)
        fp = sum(1 for g, a in pairs if g != lab and a == lab)
        fn = sum(1 for g, a in pairs if g == lab and a != lab)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s[lab] = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return (sum(f1s.values()) / len(f1s) if f1s else 0.0), f1s


def kappa(a, b):
    common = sorted(set(a) & set(b))
    n = len(common)
    if n == 0:
        return None, 0, None
    agree = sum(1 for k in common if a[k] == b[k]) / n
    pe = 0.0
    for lab in LABELS:
        pa = sum(1 for k in common if a[k] == lab) / n
        pb = sum(1 for k in common if b[k] == lab) / n
        pe += pa * pb
    k = (agree - pe) / (1 - pe) if pe < 1 else 1.0
    return agree, n, k


def extraction_recall(human_path, ai_promises):
    if not os.path.exists(human_path):
        return None
    rows = [r["약속 문장"] for r in read_table(human_path) if r.get("약속 문장")]
    # 판정기준 v2: 문장 안에 AI 관련 말이 없으면 약속이 아니므로 비율에서 뺍니다.
    kw = keyword_regex(DEFAULT_KEYWORDS)
    human = [h for h in rows if kw.search(unicodedata.normalize("NFKC", h))]
    excluded = [h for h in rows if h not in human]
    ai_norm = [(p, norm(p["sentence"])) for p in ai_promises]
    found, missed = 0, []
    for h in human:
        ok = match_promise(h, ai_norm) is not None
        found += ok
        if not ok:
            missed.append(h)
    return {"human": len(human), "found": found, "rate": found / len(human) if human else None, "missed": missed,
            "excluded_no_ai_word": len(excluded), "excluded": excluded}


def evaluate(company, dev_companies, gold_dir, work_root, out_dir):
    with open(os.path.join(work_root, company, "judged.json"), encoding="utf-8") as f:
        judged = json.load(f)["promises"]
    spec = {j["id"]: j for j in judged if j["type"] == "specific"}
    gold_rows = read_gold_rows(os.path.join(gold_dir, f"{company}_합의.csv")) or []
    ai_norm = [(j, norm(j["sentence"])) for j in judged]
    pairs, errors = [], []
    by_sentence = {"rows": 0, "matched": 0, "ai_directional": 0, "unmatched": 0}
    for r in gold_rows:
        g = r["label"]
        if r["pid"]:
            j = spec.get(r["pid"])
            if j is None:
                continue
        else:
            by_sentence["rows"] += 1
            j = match_promise(r["sentence"], ai_norm)
            if j is None:
                by_sentence["unmatched"] += 1
                continue
            by_sentence["matched"] += 1
            if j["type"] != "specific":
                by_sentence["ai_directional"] += 1
                errors.append({"promise_id": j["id"], "제목": j["title"], "정답": KO[g], "AI": "방향성(판정 없음)",
                               "AI 이유": "", "원인": "분류가 다름"})
                continue
        a = j["verdict"]
        pairs.append((g, a))
        if g != a:
            errors.append({"promise_id": j["id"], "제목": j["title"], "정답": KO[g], "AI": KO.get(a, a),
                           "AI 이유": j["reason"], "원인": ""})
    n = len(pairs)
    correct = sum(1 for g, a in pairs if g == a)
    lo, hi = wilson(correct, n)
    mf1, f1s = macro_f1(pairs) if pairs else (0.0, {})
    conf = {g: {a: sum(1 for x, y in pairs if x == g and y == a) for a in LABELS} for g in LABELS}
    critical = conf["not_verifiable"]["evidence_found"]

    ra = read_gold(os.path.join(gold_dir, f"{company}_김성태.csv"))
    rb = read_gold(os.path.join(gold_dir, f"{company}_서원.csv"))
    agree = kappa(ra, rb) if ra and rb else (None, 0, None)

    specs = list(spec.values())
    with_cite = sum(1 for j in specs if (j["verdict"] in NEED_EVIDENCE and any(e["citation_verified"] for e in j["evidence"]))
                    or (j["verdict"] == "not_verifiable" and j.get("sentence")))
    quotes = [e for j in specs for e in j["evidence"]]
    verified = sum(1 for e in quotes if e["citation_verified"])
    unsupported = sum(1 for j in specs if j["verdict"] in ("evidence_found", "partial") and
                      not any(e["citation_verified"] for e in j["evidence"]))
    rec_path = os.path.join(gold_dir, f"{company}_사람약속목록.csv")
    if not os.path.exists(rec_path):
        # 서원님이 직접 찾은 목록에 판정한 파일(promise_id 없음)이면 그 목록으로 약속을 찾은 비율을 잽니다.
        alt = os.path.join(gold_dir, f"{company}_서원.csv")
        if os.path.exists(alt) and not any(r.get("promise_id") for r in read_table(alt)):
            rec_path = alt
    rec = extraction_recall(rec_path, judged)
    if rec:
        rec["source"] = os.path.basename(rec_path)

    res = {
        "company": company, "dev_set": company in dev_companies, "n": n, "correct": correct,
        "accuracy": correct / n if n else None, "accuracy_ci95": [lo, hi], "macro_f1": mf1,
        "f1_by_label": f1s, "support": {lab: sum(1 for g, _ in pairs if g == lab) for lab in LABELS},
        "confusion": conf, "critical_errors": critical,
        "human_agreement": {"percent": agree[0], "n": agree[1], "kappa": agree[2]},
        "citation_inclusion": with_cite / len(specs) if specs else None,
        "citation_verified": verified / len(quotes) if quotes else None,
        "unsupported_execution_claims": unsupported,
        "extraction": rec, "downgraded": sum(1 for j in specs if any("낮춤" in f for f in j.get("flags", []))),
        "gold_by_sentence": by_sentence if by_sentence["rows"] else None,
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"confusion_{company}.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["정답 \\ AI"] + [KO[a] for a in LABELS])
        for g in LABELS:
            w.writerow([KO[g]] + [conf[g][a] for a in LABELS])
    with open(os.path.join(out_dir, f"errors_{company}.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["promise_id", "제목", "정답", "AI", "AI 이유", "원인"])
        w.writeheader()
        w.writerows(errors)
    return res


def pct(x):
    return "-" if x is None else f"{x * 100:.1f}%"


def to_md(results):
    lines = ["# AI 판정 평가 결과 (시범 평가)", ""]
    lines.append("| 기업 | 구분 | 건수 | 정확도 | 95% 신뢰구간 | macro-F1 | 치명 오류 | 사람 일치율 | kappa | 인용 포함 | 인용 원문 일치 | 근거 없는 실행 판정 | 약속을 찾은 비율 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in results:
        ex = r["extraction"]
        exs = "-" if not ex else f"{ex['found']}/{ex['human']} ({pct(ex['rate'])})"
        ha = r["human_agreement"]
        kap = "-" if ha["kappa"] is None else f"{ha['kappa']:.2f}"
        lines.append(f"| {r['company']} | {'개발에 쓴 기업' if r['dev_set'] else '평가용'} | {r['n']} | {pct(r['accuracy'])} | "
                     f"{pct(r['accuracy_ci95'][0])}~{pct(r['accuracy_ci95'][1])} | {r['macro_f1']:.2f} | {r['critical_errors']} | "
                     f"{pct(ha['percent'])} (n={ha['n']}) | {kap} | {pct(r['citation_inclusion'])} | {pct(r['citation_verified'])} | "
                     f"{r['unsupported_execution_claims']} | {exs} |")
    lines.append("")
    notes = []
    for r in results:
        ex = r["extraction"]
        if ex and ex.get("excluded_no_ai_word"):
            notes.append(f"- {r['company']}: 사람 약속 목록 중 문장 안에 AI 관련 말이 없는 {ex['excluded_no_ai_word']}개는 "
                         "약속이 아니라서 '약속을 찾은 비율'에서 뺐습니다. (판정기준 v2, 2장)")
        bs = r.get("gold_by_sentence")
        if bs:
            notes.append(f"- {r['company']}: 정답 {bs['rows']}건을 약속 문장으로 AI 약속과 맞췄습니다. 맞춘 {bs['matched']}건 중 "
                         f"AI가 방향성으로 둔 {bs['ai_directional']}건은 판정 비교에서 빼고 errors 파일에 '분류가 다름'으로 적었습니다. "
                         f"AI 약속과 맞지 않은 {bs['unmatched']}건도 판정 비교에서 뺐습니다.")
    if notes:
        lines.extend(notes + [""])
    for r in results:
        lines.append(f"## {r['company']} 혼동표 (행: 정답, 열: AI)")
        lines.append("| 정답 \\ AI | " + " | ".join(KO[a] for a in LABELS) + " |")
        lines.append("| --- | " + " | ".join("---" for _ in LABELS) + " |")
        for g in LABELS:
            lines.append(f"| {KO[g]} | " + " | ".join(str(r["confusion"][g][a]) for a in LABELS) + " |")
        small = [KO[lab] for lab, c in r["support"].items() if 0 < c < 5]
        if small:
            lines.append(f"\n건수가 5건 미만인 판정: {', '.join(small)} (해석에 주의)")
        lines.append("")
    lines.append("- 건수가 적어 '시범 평가'로 표기합니다. 신뢰구간은 Wilson 방법으로 계산했습니다.")
    lines.append("- '개발에 쓴 기업'은 엔진을 만들며 결과를 본 기업이라 평가용 결과와 따로 봅니다.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", nargs="+", default=["samsung", "skhynix"])
    ap.add_argument("--dev", nargs="*", default=["samsung"])
    ap.add_argument("--gold-dir", default=os.path.join(HERE, "gold"))
    ap.add_argument("--work-root", default=os.path.join(ROOT, "data", "work"))
    ap.add_argument("--out-dir", default=os.path.join(HERE, "results"))
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    results = []
    for c in a.companies:
        if not os.path.exists(os.path.join(a.work_root, c, "judged.json")):
            print(f"건너뜀: {c} (judged.json 없음)")
            continue
        results.append(evaluate(c, a.dev, a.gold_dir, a.work_root, a.out_dir))
    md = to_md(results)
    with open(os.path.join(a.out_dir, "results.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(md)


if __name__ == "__main__":
    main()
