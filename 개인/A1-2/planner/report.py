"""리포트 조립.

역할 나누기
- LLM   : 문장(추천 이유 요약, 날씨 요약, 행사 목록, 1일 일정)을 쓴다.
- 프로그램: 사실 데이터(맛집 표, 오류 요약)와 안내 문구를 직접 넣는다.
  LLM 초안의 {{RESTAURANTS_n}} 자리를 실제 검색 결과 표로 바꾸므로, 없는 식당이 리포트에 들어가지 않는다.

LLM 호출이 실패하거나 틀(필수 섹션, 자리 표시)을 지키지 않으면 기본 템플릿으로 리포트를 만든다.
어떤 경우에도 리포트 파일은 반드시 생성된다.
"""
from __future__ import annotations

import re
from datetime import date

from .errors import FORMAT_ERROR, STEP_REPORT, ApiError, ErrorCollector, hint_for
from .llm import build_report_prompt, placeholder, write_report
from .schema import REQUIRED_KEYS

EM_DASH = "\u2014"
PER_CITY_SECTIONS = ("추천 이유", "날씨", "행사", "맛집", "일정")
TIME_SLOTS = ("오전", "오후", "저녁")
# 목록·제목·표·인용·코드·자리 표시로 시작하는 줄 (이런 줄은 목록 보정 대상이 아님)
_NOT_PLAIN = re.compile(r"^([-*+]\s|\d+[.)]\s|#|>|\||```|<|\{\{RESTAURANTS_)")
# "**오전**: ..."처럼 시간대를 굵게 쓴 줄
_TIME_SLOT_LINE = re.compile(r"^\*\*(오전|오후|저녁)[^*\n]*\*\*")
_WRAPPING_FENCE = re.compile(r"^```(?:markdown|md)?[ \t]*\n(.*?)\n```$", re.S)


# ---------------------------------------------------------------------------
# 재료 준비
# ---------------------------------------------------------------------------
def city_blocks(recommendation: dict, restaurants: list[dict], searches: list[dict]) -> list[dict]:
    """지역별로 (1차 추천, 검색 정보, 맛집 목록)을 묶는다."""
    cities = recommendation.get("recommended_cities") or [
        {key: recommendation[key] for key in REQUIRED_KEYS}
    ]
    blocks = []
    for i, rec in enumerate(cities, start=1):
        city = rec["recommended_city"]
        search = next((s for s in searches if s.get("city") == city), None) or {
            "city": city, "query": "", "status": "error", "error_type": "UNKNOWN",
        }
        items = [r for r in restaurants if r.get("city") == city]
        blocks.append({"index": i, "rec": rec, "search": search, "items": items})
    return blocks


def _cell(value) -> str:
    """표 칸에 넣을 글자 정리(줄바꿈, | 기호 제거)."""
    return " ".join(str(value or "-").replace("|", "/").split()) or "-"


def _safe_url(url: str) -> str:
    return str(url).replace(" ", "%20").replace(")", "%29").replace("(", "%28")


def restaurants_markdown(search: dict, items: list[dict], provider_label: str) -> str:
    """맛집 섹션 본문. 0건이나 실패면 '데이터 없음'."""
    if items:
        lines = [
            f"검색어: `{search.get('query', '')}` | 출처: {provider_label} | {len(items)}곳",
            "",
            "| # | 이름 | 분류 | 주소 | 지도 |",
            "|---|---|---|---|---|",
        ]
        for n, item in enumerate(items, start=1):
            link = f"[열기]({_safe_url(item['url'])})" if item.get("url") else "-"
            lines.append(
                f"| {n} | {_cell(item.get('name'))} | {_cell(item.get('category'))} "
                f"| {_cell(item.get('address'))} | {link} |"
            )
        return "\n".join(lines)
    if search.get("status") == "empty":
        return f"- 데이터 없음 (장소 검색 결과 0건, 검색어: {search.get('query') or '-'})"
    return f"- 데이터 없음 (장소 검색 실패: {search.get('error_type') or 'UNKNOWN'}, 아래 오류 요약 참고)"


def errors_markdown(errors: list[dict]) -> str:
    lines = ["## 오류 요약(errors)", ""]
    if not errors:
        lines.append("- 없음 (모든 단계 정상 처리)")
        return "\n".join(lines)
    lines += ["| # | 단계 | 유형 | 내용 |", "|---|---|---|---|"]
    for n, err in enumerate(errors, start=1):
        lines.append(f"| {n} | {_cell(err.get('step'))} | {_cell(err.get('type'))} | {_cell(err.get('message'))} |")
    return "\n".join(lines)


def notice_block(meta: dict, source: str) -> str:
    cache = "사용(1차 추천, 맛집 검색 API 호출 생략)" if meta["cache"]["used"] else "미사용"
    lines = [
        f"> 생성: {meta['last_run_at']} | LLM: {meta['llm']['provider']}({meta['llm']['model']}) "
        f"| 장소 검색: {meta['place']['label']} | 캐시: {cache}",
        "> 날씨와 행사는 LLM의 일반 지식에 기반한 참고 정보입니다. 방문 전 공식 채널에서 일정과 기상을 확인하세요.",
    ]
    if source == "template":
        lines.append("> 참고: LLM 리포트 생성이 실패해 프로그램 기본 템플릿으로 작성했습니다(오류 요약 참고).")
    return "\n>\n".join(lines)


# ---------------------------------------------------------------------------
# 검사와 마무리
# ---------------------------------------------------------------------------
def validate_llm_report(md: str, n_cities: int) -> list[str]:
    """LLM 초안이 필수 섹션과 자리 표시를 모두 갖췄는지 확인한다."""
    problems: list[str] = []
    headings = [line.strip() for line in md.splitlines() if line.lstrip().startswith("#")]

    def count(word: str) -> int:
        return sum(1 for h in headings if word in h)

    if count("추천 지역") < 1:
        problems.append("'추천 지역' 섹션 없음")
    for word in PER_CITY_SECTIONS:
        if count(word) < n_cities:
            problems.append(f"'{word}' 섹션 부족")
    for i in range(1, n_cities + 1):
        if placeholder(i) not in md:
            problems.append(f"맛집 자리 표시(RESTAURANTS_{i}) 없음")
    for slot in TIME_SLOTS:
        if md.count(slot) < n_cities:
            problems.append(f"1일 일정의 '{slot}' 부족")
    return problems


def _strip_wrapping_fence(md: str) -> str:
    match = _WRAPPING_FENCE.match(md.strip())
    return match.group(1) if match else md


def _drop_error_section(md: str) -> str:
    """LLM이 규칙을 어기고 오류 요약 섹션을 썼다면 지운다(프로그램이 정확한 목록을 붙이므로)."""
    out: list[str] = []
    skipping = False
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") and "오류 요약" in stripped:
            skipping = True
            continue
        if skipping and stripped.startswith("## "):
            skipping = False
        if not skipping:
            out.append(line)
    return "\n".join(out)


def _normalize_lists(md: str) -> str:
    """LLM이 목록 기호 없이 한 줄씩 쓴 부분을 Markdown 글머리표 목록으로 바꾼다.

    Markdown(GitHub 포함)은 빈 줄 없이 이어진 줄을 한 문단으로 합쳐 보여 준다. 그래서
    '제주/강릉/경주'나 '**오전**: .../**오후**: ...'를 한 줄씩 쓰면 화면에서는 한 줄로 붙는다.
    (2026-09-29 실제 gpt-4o-mini 복수 지역 리포트에서 발생)
    규칙: 일반 글 줄이 2줄 이상 이어지거나, 시간대를 굵게 쓴 줄이면 앞에 "- "를 붙인다.
    """
    lines = md.split("\n")
    out: list[str] = []
    in_fence = False

    def plain(text: str) -> bool:
        stripped = text.strip()
        return bool(stripped) and not _NOT_PLAIN.match(stripped)

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        if in_fence or stripped.startswith("```") or not plain(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        j = i
        while j < len(lines) and plain(lines[j]):
            j += 1
        block = lines[i:j]
        if len(block) >= 2 or _TIME_SLOT_LINE.match(stripped):
            out.extend(f"- {line.strip()}" for line in block)
        else:
            out.extend(block)
        i = j
    return "\n".join(out)


def sanitize(md: str) -> str:
    md = re.sub(rf"\s*{EM_DASH}\s*", ", ", md)          # em dash는 쉼표로 바꾼다
    md = re.sub(r"[ \t]+\n", "\n", md)                   # 줄 끝 공백 제거
    md = re.sub(r"\n{3,}", "\n\n", md)                   # 빈 줄 3개 이상은 2개로
    return md.strip() + "\n"


def finalize(draft: str, blocks: list[dict], meta: dict, errors: list[dict], source: str,
             provider_label: str) -> str:
    """초안 + (제목, 안내 문구, 실제 맛집 표, 오류 요약) = 최종 리포트."""
    title = f"# {meta['travel_date']} 국내 여행 추천 리포트"
    lines = _drop_error_section(draft).strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]  # 제목은 항상 같은 형식으로 통일
    body = _normalize_lists("\n".join(lines).strip())  # 표를 넣기 전에 LLM 글만 목록 보정
    for block in blocks:
        mark = placeholder(block["index"])
        table = restaurants_markdown(block["search"], block["items"], provider_label)
        body = body.replace(mark, table, 1).replace(mark, "")
    md = "\n\n".join([title, notice_block(meta, source), body, errors_markdown(errors)])
    return sanitize(md)


# ---------------------------------------------------------------------------
# 기본 템플릿 (LLM 실패 시)
# ---------------------------------------------------------------------------
def _itinerary(block: dict, bold: bool) -> list[str]:
    rec, items = block["rec"], block["items"]
    city = rec["recommended_city"]
    lunch = f"점심은 '{items[1]['name']}'에서 먹습니다." if len(items) >= 2 else "점심은 현지 식당에서 먹습니다."
    if rec.get("events"):
        event = re.sub(r"\s*\(일정 변동 가능\)\s*$", "", rec["events"][0])
        afternoon = f"'{event}' 관련 장소를 방문합니다(방문 전 일정 확인)."
    else:
        afternoon = f"{city}의 주요 관광지를 여유 있게 둘러봅니다."
    dinner = f"저녁은 '{items[0]['name']}'에서 먹습니다." if items else "저녁은 현지 식당에서 먹습니다."
    slots = [("오전", f"{city} 도착 후 중심가와 대표 명소를 둘러봅니다. {lunch}"),
             ("오후", afternoon),
             ("저녁", dinner)]
    if bold:
        return [f"- **{name}**: {text}" for name, text in slots]
    out: list[str] = []
    for name, text in slots:
        out += [f"### {name}", text]
    return out


def template_report(blocks: list[dict]) -> str:
    lines: list[str] = []
    if len(blocks) == 1:
        block = blocks[0]
        rec = block["rec"]
        lines += ["## 추천 지역", f"- {rec['recommended_city']}", "",
                  "## 추천 이유", rec["reason"], "",
                  "## 날씨 요약", rec["weather"], "",
                  "## 행사/축제", *[f"- {e}" for e in rec["events"]], "",
                  "## 맛집 추천", placeholder(1), "",
                  "## 1일 일정 제안", *_itinerary(block, bold=False)]
        return "\n".join(lines)
    lines += ["## 추천 지역", *[f"{b['index']}. {b['rec']['recommended_city']}" for b in blocks]]
    for block in blocks:
        rec = block["rec"]
        lines += ["", f"## {block['index']}. {rec['recommended_city']}",
                  "### 추천 이유", rec["reason"],
                  "### 날씨 요약", rec["weather"],
                  "### 행사/축제", *[f"- {e}" for e in rec["events"]],
                  "### 맛집 추천", placeholder(block["index"]),
                  "### 1일 일정 제안", *_itinerary(block, bold=True)]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# [3/3] 전체
# ---------------------------------------------------------------------------
def build_report(llm, travel_date: date, recommendation: dict, restaurants: list[dict],
                 searches: list[dict], errors: ErrorCollector, meta: dict, log=print) -> tuple[str, str]:
    """반환: (최종 Markdown, 작성 방식 'llm' 또는 'template')"""
    blocks = city_blocks(recommendation, restaurants, searches)
    provider_label = meta["place"]["label"]
    prompt_blocks = [
        {
            "index": b["index"],
            **b["rec"],
            "restaurants": [
                {"name": it.get("name", ""), "category": it.get("category", ""), "address": it.get("address", "")}
                for it in b["items"]
            ],
        }
        for b in blocks
    ]
    source = "llm"
    try:
        draft = write_report(llm, build_report_prompt(travel_date.isoformat(), prompt_blocks))
        draft = _strip_wrapping_fence(draft)
        problems = validate_llm_report(draft, len(blocks))
        if problems:
            errors.add(STEP_REPORT, FORMAT_ERROR,
                       f"LLM 리포트가 틀을 지키지 않음({'; '.join(problems)}) -> 기본 템플릿으로 작성")
            log("  - LLM 리포트가 정해진 틀을 지키지 않아 기본 템플릿으로 작성합니다")
            draft, source = template_report(blocks), "template"
    except ApiError as exc:
        errors.add(STEP_REPORT, exc.err_type, exc.message)
        log(f"  - 오류: {hint_for(exc, meta['llm']['provider'])}")
        log("  - 기본 템플릿으로 리포트를 작성하고 계속 진행합니다")
        draft, source = template_report(blocks), "template"
    return finalize(draft, blocks, meta, errors.to_list(), source, provider_label), source
