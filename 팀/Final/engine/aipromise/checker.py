"""결과 파일이 화면 규칙(안내서 2장, 4장)에 맞는지 점검합니다. 배포 전에 꼭 돌립니다."""
from .textutil import find_forbidden

VERDICTS = ("evidence_found", "partial", "not_verifiable", "company_reported_not_pursued")
NEED_EVIDENCE = ("evidence_found", "partial", "company_reported_not_pursued")
LABEL_KEYS = ("service_name", "service_subtitle", "tagline", "disclaimers", "verdicts", "promise_types",
              "not_verifiable_message", "no_related_activity_message", "citation_verified_label",
              "interview_card_notice")


def check(data, expect_real=True):
    errs = []
    meta = data.get("meta", {})
    if not isinstance(meta.get("is_sample"), bool):
        errs.append("meta.is_sample이 true/false가 아닙니다")
    elif expect_real and meta.get("is_sample"):
        errs.append("(주의) meta.is_sample이 true입니다. 실제 결과면 false여야 '예시 데이터' 띠가 사라집니다")
    labels = data.get("labels", {})
    for k in LABEL_KEYS:
        if k not in labels:
            errs.append(f"labels.{k}가 없습니다")
    if len(labels.get("disclaimers", [])) != 2:
        errs.append("labels.disclaimers는 안내 문구 2개여야 합니다")
    comps = data.get("companies") or []
    if not comps:
        errs.append("companies가 비어 있습니다")
    seen = set()
    for c in comps:
        cname = c.get("name", c.get("id"))
        for k in ("id", "name", "reports", "promises", "interview_card"):
            if k not in c:
                errs.append(f"{cname}: {k}가 없습니다")
        if "check_note" in c and (not isinstance(c["check_note"], str) or find_forbidden(c["check_note"])):
            errs.append(f"{cname}: check_note는 단정 표현 없는 글자여야 합니다")
        specs = {}
        for p in c.get("promises", []):
            pid = p.get("id")
            if pid in seen:
                errs.append(f"{pid}: 약속 번호가 겹칩니다")
            seen.add(pid)
            for k in ("type", "title", "sentence", "source", "evidence"):
                if k not in p:
                    errs.append(f"{pid}: {k}가 없습니다")
            src = p.get("source") or {}
            for k in ("report", "section", "url"):
                if k not in src:
                    errs.append(f"{pid}: source.{k}가 없습니다")
            if p.get("type") == "specific":
                specs[pid] = p
                v = p.get("verdict")
                if v not in VERDICTS:
                    errs.append(f"{pid}: 판정 값 '{v}'이 4가지 중 하나가 아닙니다")
                if not p.get("reason"):
                    errs.append(f"{pid}: 판정 이유가 비어 있습니다")
                if v in NEED_EVIDENCE and not p.get("evidence"):
                    errs.append(f"{pid}: '{v}'인데 근거 문장이 없습니다")
                if v == "not_verifiable" and p.get("evidence"):
                    errs.append(f"{pid}: '확인 불가'인데 근거 문장이 들어 있습니다")
            elif p.get("type") == "directional":
                if p.get("verdict") is not None or p.get("reason") is not None:
                    errs.append(f"{pid}: 방향성 약속은 판정과 이유가 null이어야 합니다")
            else:
                errs.append(f"{pid}: type은 specific 또는 directional이어야 합니다")
            for e in p.get("evidence", []):
                if e.get("citation_verified") is not True:
                    errs.append(f"{pid}: 인용 검사를 통과하지 못한 근거가 들어 있습니다")
            bad = find_forbidden(p.get("reason") or "")
            if bad:
                errs.append(f"{pid}: 판정 이유에 단정 표현 {bad}")
        card = c.get("interview_card", {})
        for key, n in (("issues", 3), ("talking_points", 3), ("questions", 2)):
            items = card.get(key, [])
            if len(items) < n:
                errs.append(f"(주의) {cname}: 면접 카드 {key}가 {len(items)}개입니다 (기본 {n}개)")
            for it in items:
                if it.get("promise_id") not in specs:
                    errs.append(f"{cname}: 면접 카드 {key}의 promise_id '{it.get('promise_id')}'가 구체적 약속에 없습니다")
                if find_forbidden(it.get("text", "")):
                    errs.append(f"{cname}: 면접 카드 {key}에 단정 표현이 있습니다")
                if key == "talking_points":
                    j = specs.get(it.get("promise_id"))
                    if not it.get("evidence_url"):
                        errs.append(f"{cname}: 답변 소재에 근거 링크가 없습니다")
                    if j and j.get("verdict") not in ("evidence_found", "partial"):
                        errs.append(f"{cname}: 답변 소재가 근거 확인/일부 확인이 아닌 약속을 씁니다")
    return errs
