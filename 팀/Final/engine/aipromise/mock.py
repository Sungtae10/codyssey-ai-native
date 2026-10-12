"""--mock 실행용 가짜 모델. 인터넷과 API 키 없이 1~7단계가 끝까지 도는지 점검할 때만 씁니다.
판정 품질과는 관계없습니다."""
import json
import re

from .textutil import tokenize, keyword_regex, DEFAULT_KEYWORDS

PLAN = re.compile(r"계획|예정|추진할|확대할|나갈|겠습니다|목표로")
SPECIFIC = re.compile(r"\d|공장|라인|센터|서비스|제품|플랫폼|조직|시스템")
DONE = re.compile(r"하였|했습니다|완료|적용|출시|신설|도입하였|구축하였")
NOT_PURSUED = re.compile(r"추진하지\s*않")
KW = keyword_regex(DEFAULT_KEYWORDS)


def _sim(a, b):
    ta, tb = set(tokenize(a)), set(tokenize(b))
    return len(ta & tb) / (len(ta | tb) or 1)


def _cands(user):
    rows = []
    for line in user.splitlines():
        parts = [x.strip() for x in line.split(" | ")]
        if len(parts) >= 5 and re.match(r"^\S+-\S+-\d{4}$", parts[0]):
            rows.append((parts[0], parts[-1]))
    return rows


class FakeLLM:
    def respond(self, task, system, user):
        if task == "extract":
            out = []
            for line in user.split("[후보 문장]")[-1].splitlines():
                m = re.match(r"^(\S+-\S+-\d{4}): (.*)$", line.strip())
                if m and PLAN.search(m.group(2)) and KW.search(m.group(2)):
                    t = m.group(2)
                    out.append({"id": m.group(1), "type": "specific" if SPECIFIC.search(t) else "directional",
                                "title": t[:22]})
            return json.dumps({"promises": out}, ensure_ascii=False)
        if task in ("judge", "related"):
            m = re.search(r"(?:약속 문장|방향성 약속): (.*)", user)
            promise = m.group(1) if m else ""
            scored = sorted(((_sim(promise, t), sid, t) for sid, t in _cands(user)), reverse=True)
            if task == "related":
                ids = [sid for s, sid, t in scored[:2] if s >= 0.12 and DONE.search(t)]
                return json.dumps({"related_ids": ids[:1]})
            for s, sid, t in scored[:5]:
                if NOT_PURSUED.search(t) and s >= 0.1:
                    return json.dumps({"verdict": "company_reported_not_pursued", "evidence_ids": [sid],
                                       "reason": "회사가 후속 공시에 이 일을 추진하지 않고 있다고 적었습니다.", "new_query": ""},
                                      ensure_ascii=False)
            if scored and scored[0][0] >= 0.18 and DONE.search(scored[0][2]):
                v = "evidence_found" if scored[0][0] >= 0.28 else "partial"
                return json.dumps({"verdict": v, "evidence_ids": [scored[0][1]],
                                   "reason": "약속과 같은 대상이 후속 공시에 적혀 있습니다. 근거 문장을 함께 확인해 주세요.",
                                   "new_query": ""}, ensure_ascii=False)
            t = re.search(r"약속 제목: (.*)", user)
            return json.dumps({"verdict": "not_verifiable", "evidence_ids": [], "reason": "",
                               "new_query": (t.group(1) if t else "") + " 운영"}, ensure_ascii=False)
        if task == "card":
            return json.dumps({"issues": [], "talking_points": [], "questions": []})
        return "{}"
