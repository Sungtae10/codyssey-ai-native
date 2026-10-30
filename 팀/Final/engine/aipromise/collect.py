"""1단계: 수집. DART에서 받은 PDF를 읽어 '읽는 장'만 문장 단위로 저장합니다.

읽는 장 3곳
- I. 회사의 개요 > 5. 정관에 관한 사항   (키: I5)
- II. 사업의 내용                         (키: II)
- IV. 이사의 경영진단 및 분석의견          (키: IV)

장의 시작과 끝은 제목 줄로 찾습니다. 못 찾으면 config.yaml의 section_pages로 쪽을 직접 적습니다.
"""
import json
import os
import re

from .textutil import clean_page_text, normalize, keyword_regex, DEFAULT_KEYWORDS

_H = {
    "I": r"(?:I|Ⅰ)\s*\.\s*회\s*사\s*의\s*개\s*요",
    "II": r"(?:II|Ⅱ)\s*\.\s*사\s*업\s*의\s*내\s*용",
    "III": r"(?:III|Ⅲ)\s*\.\s*재\s*무\s*에\s*관\s*한\s*사\s*항",
    "IV": r"(?:IV|Ⅳ)\s*\.\s*이\s*사\s*의\s*경\s*영\s*진\s*단\s*및\s*분\s*석\s*의\s*견",
    "V": r"(?:V|Ⅴ)\s*\.\s*회\s*계\s*감\s*사\s*인\s*의\s*감\s*사\s*의\s*견",
    "VI": r"(?:VI|Ⅵ)\s*\.\s*이\s*사\s*회\s*등\s*회\s*사\s*의\s*기\s*관",
}
_I5 = r"5\s*\.\s*정\s*관\s*에\s*관\s*한\s*사\s*항"

SECTIONS = {
    "I5": {"name": "I. 회사의 개요 > 5. 정관에 관한 사항", "start": _I5, "end": [_H["II"]]},
    "II": {"name": "II. 사업의 내용", "start": _H["II"], "end": [_H["III"], _H["IV"]]},
    "IV": {"name": "IV. 이사의 경영진단 및 분석의견", "start": _H["IV"], "end": [_H["V"], _H["VI"]]},
}


def read_pages(path: str):
    """PDF(또는 시험용 .txt, 쪽 구분은 \\f)를 쪽 글 목록으로 읽기."""
    if path.lower().endswith(".txt"):
        with open(path, encoding="utf-8") as f:
            raw = f.read().split("\f")
        return [clean_page_text(p) for p in raw]
    from pypdf import PdfReader  # 실제 PDF를 읽을 때만 필요
    reader = PdfReader(path)
    return [clean_page_text(p.extract_text() or "") for p in reader.pages]


def _is_toc(page: str) -> bool:
    """목차 쪽: 큰 제목이 3개 이상 모인 짧은 쪽. (DART 화면에서 복사한 .txt처럼 한 쪽에 본문이 다 든 경우는 제외)"""
    if len(page) > 4000:
        return False
    hits = sum(1 for pat in _H.values() if re.search(pat, page))
    return hits >= 3


def _find(pages, pattern, start_page=0, start_pos=0, anchored=True):
    rx = re.compile((r"(?m)^\s*" if anchored else "") + pattern)
    for i in range(start_page, len(pages)):
        if _is_toc(pages[i]):
            continue
        m = rx.search(pages[i], start_pos if i == start_page else 0)
        if m:
            return i, m.start()
    return None


def _heading_lines(pages, pattern, start_page=0, start_pos=0, slack=12):
    """제목 줄 후보: 줄 맨 앞이 장 제목이고 뒤에 붙은 글이 짧은(slack자 이하) 줄만. (DART 자동 수집 글용)
    정정 보고서 앞의 '정정 사항' 표처럼 장 제목 뒤에 다른 칸 글이 이어지는 줄은 빼려는 것입니다."""
    rx = re.compile(r"(?m)^[ \t]*(?:" + pattern + r")(.*)$")
    out = []
    for i in range(start_page, len(pages)):
        if _is_toc(pages[i]):
            continue
        for m in rx.finditer(pages[i], start_pos if i == start_page else 0):
            if len(m.group(1).strip()) <= slack:
                out.append((i, m.start()))
    return out


def span_chars(pages, start, end):
    """(쪽, 글자 위치) 시작과 끝 사이 글자 수 (끝이 없으면 문서 끝까지)."""
    (sp, spos) = start
    ep, epos = end if end else (len(pages) - 1, None)
    total = 0
    for i in range(sp, min(ep, len(pages) - 1) + 1):
        a = spos if i == sp else 0
        b = epos if (i == ep and epos is not None) else len(pages[i])
        total += max(0, b - a)
    return total


# 이보다 짧으면 본문 장이 아니라 표 칸 등으로 봅니다 (II장은 길고, 정관 장과 반기보고서의 IV장은 짧을 수 있음)
_DART_MIN_CHARS = {"I5": 150, "II": 2000, "IV": 150}


def _locate_dart(pages, spec, min_chars=2000):
    """DART 자동 수집 글: 제목 줄 후보 가운데 장 길이가 min_chars 이상인 첫 후보, 없으면 가장 긴 후보.
    (10/19 고침) 카카오 2026 반기보고서([기재정정])는 맨 앞 정정 사항 표의 'II. 사업의 내용' 칸이 먼저 잡혀
    II장이 91자만 남았습니다. 본문 장 제목(XML의 TITLE)은 한 줄에 제목만 있으므로 이 규칙으로 본문을 고릅니다."""
    best = None
    for st in _heading_lines(pages, spec["start"]):
        en = None
        for pat in spec["end"]:
            cands = _heading_lines(pages, pat, st[0], st[1] + 1)
            cand = cands[0] if cands else None
            if cand and (en is None or cand < en):
                en = cand
        size = span_chars(pages, st, en)
        if size >= min_chars:
            return st, en
        if best is None or size > best[2]:
            best = (st, en, size)
    return (best[0], best[1]) if best else None


def locate_sections(pages, wanted, overrides=None, dart=False):
    """장마다 (시작 쪽, 시작 글자 위치, 끝 쪽, 끝 글자 위치)를 찾습니다. 쪽 번호는 0부터.
    dart=True(OpenDART 자동 수집 글)면 제목 줄 규칙(_locate_dart)을 먼저 쓰고, 못 찾으면 원래 방법으로 찾습니다."""
    overrides = overrides or {}
    found = {}
    for key in wanted:
        spec = SECTIONS[key]
        if key in overrides:  # 사람이 적은 쪽 번호(1부터, 양끝 포함)
            s, e = overrides[key]
            found[key] = {"start": (s - 1, 0), "end": (e - 1, None), "how": "config"}
            continue
        if dart:
            got = _locate_dart(pages, spec, _DART_MIN_CHARS.get(key, 150))
            if got:
                found[key] = {"start": got[0], "end": got[1], "how": "auto"}
                continue
        st = _find(pages, spec["start"]) or _find(pages, spec["start"], anchored=False)
        if not st:
            found[key] = None
            continue
        en = None
        for pat in spec["end"]:
            cand = _find(pages, pat, st[0], st[1] + 1) or _find(pages, pat, st[0], st[1] + 1, anchored=False)
            if cand and (en is None or cand < en):
                en = cand
        found[key] = {"start": st, "end": en, "how": "auto"}
    return found


_END = re.compile(r"(다\.|요\.|음\.|함\.|임\.|됨\.|[.?!])$")
# 제목 줄: "1. 사업의 개요", "(1) 산업의 특성", "가. 사업목적 현황", "II. 사업의 내용", "① ..." 처럼 번호로 시작하는 짧은 줄
_HEADING = re.compile(r"^(?:(?:\d{1,2}|[IVX]{1,4}|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|[가-하])\s*[.)]|\(\d{1,2}\)|\([가-하]\)|[①-⑳])\s*\S")


def _is_heading(line):
    return len(line) <= 45 and not _END.search(line) and bool(_HEADING.match(line))


# PDF는 단어 중간에서 줄이 바뀌기도 합니다. 이어 붙일 때 띄어쓰기를 넣지 않을 경우:
# 숫자끼리("202" + "5년"), 숫자 뒤 단위("2025" + "년"), 단어를 시작하지 않는 어미·조사("계획입" + "니다")
_GLUE_NEXT = re.compile(r"^(?:을|를|는|으|했|였|됩|됐|겠|습니다|니다|에서|에게|께서|부터|까지|[다요음함임됨](?:[.,]|$)|[),.%])")
_UNIT = re.compile(r"^(?:\d|년|월|일|억|만|천|조|원|개|곳|명|건|%)")


# 한 글자로도 단어가 되는 말 (이 글자로 줄이 끝나면 띄어 씀)
_ONE_SYL_WORDS = set("및등수중약총각그이더또전후내외간별당본동시한두세네몇첫새온제곳개년월일원")


def _glue(prev, nxt):
    if not prev:
        return True
    if prev[-1].isdigit() and _UNIT.match(nxt):
        return True
    if prev[-1] in "(" or _GLUE_NEXT.match(nxt):
        return True
    last = prev.rsplit(" ", 1)[-1]
    # 줄 끝이 한 글자 조각이면(예: "적" + "용하였습니다") 단어 중간에서 줄이 바뀐 것으로 봅니다.
    if len(last) == 1 and "가" <= last <= "힣" and last not in _ONE_SYL_WORDS and "가" <= nxt[:1] <= "힣":
        return True
    return False


# 문장 나누기 (10/19 보강). 공시 글은 번호 목록과 줄표 목록이 한 줄로 붙어 있는 일이 많아, 아래 자리에서도 나눕니다.
# 1) 문장 끝 + 띄어쓰기  2) "~니다.(5) 기존 사업" 처럼 띄어쓰기 없이 번호가 붙은 곳
# 3) "~양산 시작됨- 이전 세대" 처럼 '됨/함/음/임' 뒤 줄표 목록  4) "~대응 예정 (*) GDDR" 처럼 각주 표시 앞
# (예: 카카오 2024 정관 장의 "...담당합니다.(5) ...(7) 향후 추진계획- AI 캠퍼스..."가 한 문장으로 붙어 화면에 그대로 보였음)
_SPLIT = re.compile(
    r"(?<=[.?!])\s+(?=\S)"
    r"|(?<=[다요음함임됨]\.)(?=\(\d{1,2}\)|[①-⑳])"
    r"|(?<=[됨함음임])\s*-\s+(?=\S)"
    r"|\s+(?=\(\*{1,4}\)\s)"
)


def section_sentences(page_slices, min_len=12, max_len=500):
    """[(쪽 번호, 글)] → [(쪽 번호, 문장)]. 쪽을 넘어가는 문장도 이어 붙입니다.
    제목 줄과, 문장 밖의 짧은 조각(표 칸 등)은 문장에 섞이지 않게 뺍니다."""
    blocks = []  # (text, [(offset, page)])
    buf, marks = "", []
    for page_no, text in page_slices:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if _is_heading(line):
                if buf:
                    blocks.append((buf, marks))
                    buf, marks = "", []
                continue
            if not buf and len(line) < 15 and not _END.search(line):
                continue
            if buf and not _glue(buf, line):
                buf += " "
            marks.append((len(buf), page_no))
            buf += line
            if _END.search(buf):
                blocks.append((buf, marks))
                buf, marks = "", []
    if buf:
        blocks.append((buf, marks))

    out = []
    for text, mk in blocks:
        pos = 0
        for part in _SPLIT.split(text):
            start = text.find(part, pos)
            pos = start + len(part)
            page = mk[0][1]
            for off, pg in mk:
                if off <= start:
                    page = pg
            part = part.strip()
            if min_len <= len(part) <= max_len:
                out.append((page, part))
            elif len(part) > max_len:
                for q in re.split(r"(?<=[,;])\s+", part):
                    q = q.strip()
                    if min_len <= len(q) <= max_len:
                        out.append((page, q))
    return out


def report_path(cfg, report):
    """읽을 파일: OpenDART에서 자동으로 받은 글(report['text'], data/dart)이 있으면 그것, 없으면 PDF(data/pdf)."""
    if report.get("text"):
        from .dart import dart_dir
        return os.path.join(dart_dir(cfg), report["text"]), report["text"]
    return os.path.join(cfg["paths"]["pdf_dir"], report["pdf"]), report["pdf"]


def collect_report(cfg, company, report, role):
    pdf_path, source_file = report_path(cfg, report)
    if not os.path.exists(pdf_path):
        raise SystemExit(f"파일이 없습니다: {pdf_path}\n→ DART에서 받은 PDF를 이 이름으로 data/pdf 폴더에 넣거나, "
                         "python fetch_dart.py --companies <기업>으로 자동으로 받아 주세요.")
    pages = read_pages(pdf_path)
    # DART 자동 수집 글은 쪽이 PDF 쪽과 다르므로 쪽 번호를 남기지 않습니다 (화면에 'p.' 표시 안 함)
    no_pages = bool(report.get("no_pages"))
    overrides = (cfg.get("section_pages") or {}).get(company["key"], {}).get(report["key"], {})
    loc = locate_sections(pages, cfg["sections"], overrides, dart=no_pages)
    kw = keyword_regex(cfg.get("keywords") or DEFAULT_KEYWORDS)

    result = {
        "company": company["key"], "report_key": report["key"], "title": report["title"],
        "url": report.get("url", ""), "role": role, "source_file": source_file,
        "source": "dart" if no_pages else "pdf", "num_pages": None if no_pages else len(pages), "sections": {},
    }
    for key in cfg["sections"]:
        spec = SECTIONS[key]
        info = loc.get(key)
        if not info:
            result["sections"][key] = {"name": spec["name"], "found": False, "sentences": [], "norm_text": ""}
            continue
        (sp, spos), end = info["start"], info["end"]
        ep, epos = (end if end else (len(pages) - 1, None))
        slices = []
        for i in range(sp, min(ep, len(pages) - 1) + 1):
            text = pages[i]
            a = 0
            if i == sp:
                a = spos
                if info["how"] == "auto":  # 장 제목 줄은 건너뛰기
                    nl = text.find("\n", spos)
                    a = nl + 1 if nl != -1 else len(text)
            b = epos if (i == ep and epos is not None) else len(text)
            slices.append((i + 1, text[a:b]))
        sents = section_sentences(slices)
        result["sections"][key] = {
            "name": spec["name"], "found": True, "how": info["how"],
            "start_page": None if no_pages else sp + 1, "end_page": None if no_pages else ep + 1,
            "end_found": end is not None,
            "sentences": [
                {"id": f"{report['key']}-{key}-{n:04d}", "text": s, "page": None if no_pages else pg,
                 "has_keyword": bool(kw.search(s))}
                for n, (pg, s) in enumerate(sents, 1)
            ],
            "norm_text": normalize("".join(t for _, t in slices)),
        }
    return result


def run_collect(cfg, company, roles=("promise", "evidence")):
    """roles=("promise",)이면 약속을 찾는 보고서만 읽습니다 (scan: 후보 기업 미리 보기, PDF 1개면 됨)."""
    from .config import work_dir
    out_dir = work_dir(cfg, company["key"])
    reports = [(r, "promise") for r in company["promise_reports"] if "promise" in roles] + \
              [(r, "evidence") for r in company["evidence_reports"] if "evidence" in roles]
    summary = []
    for report, role in reports:
        res = collect_report(cfg, company, report, role)
        with open(os.path.join(out_dir, f"collected_{report['key']}.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False)
        for key, sec in res["sections"].items():
            summary.append((report["title"], sec["name"], sec.get("start_page"), sec.get("end_page"),
                            len(sec["sentences"]), sum(s["has_keyword"] for s in sec["sentences"]),
                            sec["found"], sec.get("end_found", False)))
    print(f"\n[1단계 수집] {company['name']}")
    print("보고서 | 장 | 시작 쪽 | 끝 쪽 | 문장 수 | 검색어 든 문장 | 확인")
    for t, n, s, e, ns, nk, ok, eok in summary:
        flag = "OK" if ok and eok else ("끝 제목 못 찾음, 문서 끝까지 읽음 → 끝 쪽 확인 필요" if ok else
                                        "장을 못 찾음 (보고서에 원래 없는 장이면 그대로 두고, 있는데 못 찾았으면 config.yaml section_pages에 쪽 번호를 적기)")
        print(f"{t} | {n} | {'-' if s is None else s} | {'-' if e is None else e} | {ns} | {nk} | {flag}")
    print("→ 시작 쪽과 끝 쪽이 PDF 목차와 맞는지 꼭 한 번 확인해 주세요.")
    return summary
