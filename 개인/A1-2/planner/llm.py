"""LLM 호출(OpenAI 또는 Gemini)과 프롬프트.

- recommend()    : [1/3] 여행 날짜 -> 1차 추천 JSON (JSON 강제 + 검증 + 실패 시 재요청 1회)
- write_report() : [3/3] 1차 추천 + 맛집 목록 -> Markdown 리포트 초안

LLM을 바꾸고 싶으면 BaseLLM을 상속한 클래스에 complete() 하나만 만들고 LLM_CLASSES에 등록한다.
"""
from __future__ import annotations

import json
from datetime import date

from .errors import PARSE_ERROR, STEP_RECOMMEND, ApiError, ErrorCollector
from .http_client import post_json
from .schema import extract_json, validate_recommendation

WEEKDAYS = "월화수목금토일"
SEASONS = {12: "겨울", 1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄",
           6: "여름", 7: "여름", 8: "여름", 9: "가을", 10: "가을", 11: "가을"}


# ---------------------------------------------------------------------------
# LLM 클라이언트
# ---------------------------------------------------------------------------
class BaseLLM:
    provider = "base"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 90):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, system: str, user: str, *, json_mode: bool) -> str:
        """system(역할/규칙) + user(요청)를 보내고 모델이 쓴 텍스트를 돌려준다."""
        raise NotImplementedError


class OpenAILLM(BaseLLM):
    """OpenAI Chat Completions API: POST {base}/chat/completions, 키는 Authorization 헤더."""

    provider = "openai"

    def complete(self, system: str, user: str, *, json_mode: bool) -> str:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}  # 문법상 올바른 JSON만 나오게 강제
        data = post_json(
            f"{self.base_url}/chat/completions",
            body=body,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )
        try:
            choice = data["choices"][0]
            content = choice["message"].get("content")
        except (KeyError, IndexError, TypeError, AttributeError):
            raise ApiError(PARSE_ERROR, "OpenAI 응답에 choices[0].message.content가 없음") from None
        if not isinstance(content, str) or not content.strip():
            reason = choice.get("finish_reason") if isinstance(choice, dict) else None
            raise ApiError(PARSE_ERROR, f"OpenAI 응답 본문이 비어 있음(finish_reason={reason})")
        return content


class GeminiLLM(BaseLLM):
    """Gemini API: POST {base}/models/{model}:generateContent, 키는 URL이 아니라 x-goog-api-key 헤더."""

    provider = "gemini"

    def complete(self, system: str, user: str, *, json_mode: bool) -> str:
        body: dict = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
        }
        if json_mode:
            body["generationConfig"] = {"responseMimeType": "application/json"}
        data = post_json(
            f"{self.base_url}/models/{self.model}:generateContent",
            body=body,
            headers={"x-goog-api-key": self.api_key},
            timeout=self.timeout,
        )
        candidates = data.get("candidates") or []
        if not candidates or not isinstance(candidates[0], dict):
            blocked = (data.get("promptFeedback") or {}).get("blockReason")
            extra = f"(blockReason={blocked})" if blocked else ""
            raise ApiError(PARSE_ERROR, f"Gemini 응답에 candidates가 없음{extra}")
        first = candidates[0]
        parts = (first.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))
        if not text.strip():
            raise ApiError(PARSE_ERROR, f"Gemini 응답 텍스트가 비어 있음(finishReason={first.get('finishReason')})")
        return text


LLM_CLASSES = {"openai": OpenAILLM, "gemini": GeminiLLM}


def create_llm(settings) -> BaseLLM:
    """설정에 맞는 LLM 클라이언트를 만든다. (파이프라인은 어떤 LLM 인지 몰라도 된다)"""
    cls = LLM_CLASSES[settings.llm_provider]
    return cls(settings.llm_api_key, settings.llm_model, settings.llm_base_url)


# ---------------------------------------------------------------------------
# [1/3] 1차 추천 프롬프트
# ---------------------------------------------------------------------------
RECOMMEND_SYSTEM = (
    "너는 한국 국내 여행 큐레이터다. 사용자가 준 여행 날짜의 계절, 그 시기의 일반적인 날씨 경향, "
    "그 무렵 자주 열리는 지역 행사를 바탕으로 국내 여행지를 추천한다.\n"
    "출력 규칙: JSON 객체 하나만 출력한다. 코드블록 표시(```), 설명 문장, 주석은 쓰지 않는다. "
    "키 이름과 값의 타입을 정확히 지킨다. 값은 한국어로 쓰고 영어 단어를 섞지 않는다."
)

SINGLE_SCHEMA = ('{"recommended_city": "제주", "weather": "그 시기 일반적인 날씨 요약", '
                 '"events": ["행사/축제 후보 1", "행사/축제 후보 2"], "reason": "추천 근거 2~4문장"}')

CITY_RULES = (
    "- recommended_city: 시·군 단위 지명 하나만 쓴다(예: 제주, 강릉, 경주, 여수, 전주). "
    "'특별자치도, 광역시, 시, 군' 같은 행정 접미사, 괄호, 두 지역을 묶은 이름(예: 속초·양양)은 쓰지 않는다. "
    "이 값은 그대로 지도 검색어로 쓰인다.\n"
    "- weather: 그 시기의 일반적인 날씨 경향을 1~2문장으로 쓴다(실시간 예보가 아님).\n"
    "- events: 그 시기에 그 지역에서 열리는 편인 행사·축제 후보 1~3개를 문자열 배열로 쓴다. "
    "올해 개최 여부나 날짜가 확실하지 않으면 이름 뒤에 '(일정 변동 가능)'을 붙인다.\n"
    "- reason: 추천 근거를 2~4문장으로 쓴다."
)


def describe_date(d: date) -> str:
    """2026-10-10 -> '2026-10-10 (토요일, 10월 초순, 가을)'"""
    part = "초순" if d.day <= 10 else ("중순" if d.day <= 20 else "하순")
    return f"{d.isoformat()} ({WEEKDAYS[d.weekday()]}요일, {d.month}월 {part}, {SEASONS[d.month]})"


def build_recommend_prompt(travel_date: date, n_cities: int = 1) -> str:
    head = f"여행 날짜: {describe_date(travel_date)}\n\n"
    if n_cities <= 1:
        return (
            head
            + "이 날짜에 여행하기 좋은 한국 국내 지역 1곳을 추천해 줘.\n\n"
            + f"출력 형식(JSON):\n{SINGLE_SCHEMA}\n\n"
            + f"작성 규칙:\n{CITY_RULES}"
        )
    return (
        head
        + f"이 날짜에 여행하기 좋은 한국 국내 지역 {n_cities}곳을 서로 다른 지역으로, 추천 순서대로 골라 줘.\n\n"
        + f'출력 형식(JSON):\n{{"recommended_cities": [{SINGLE_SCHEMA}, ...]}}\n'
        + f"recommended_cities 배열에는 정확히 {n_cities}개의 객체를 넣고, 각 객체는 아래 규칙을 모두 지킨다.\n\n"
        + f"작성 규칙:\n{CITY_RULES}"
    )


def build_repair_prompt(bad_output: str, problems: list[str], n_cities: int = 1) -> str:
    """재요청 프롬프트: 처음 규칙 대신 '필수 키만 다시 JSON으로' 한 가지만 강하게 요구한다."""
    if n_cities <= 1:
        schema = SINGLE_SCHEMA
    else:
        schema = f'{{"recommended_cities": [{SINGLE_SCHEMA}, ...]}} (객체 정확히 {n_cities}개)'
    snippet = (bad_output or "").strip()[:1500]
    return (
        "직전 응답을 프로그램이 JSON으로 읽지 못했거나 필수 키 검사를 통과하지 못했다.\n"
        f"발견된 문제: {'; '.join(problems)[:500]}\n\n"
        f"직전 응답(앞부분):\n<<<\n{snippet}\n>>>\n\n"
        "내용은 살리되, 아래 필수 키만 가진 JSON 객체 하나로 다시 출력하라. "
        "JSON 이외의 글자(인사말, 설명, 코드블록 표시)는 한 글자도 쓰지 않는다.\n"
        f"필수 형식: {schema}\n"
        "타입: recommended_city=문자열(지명 하나), weather=문자열, events=문자열 배열(1~3개), reason=문자열"
    )


def parse_recommendation(raw_text: str, n_cities: int) -> tuple[bool, list[str], dict | None]:
    try:
        obj = extract_json(raw_text)
    except ValueError as exc:
        return False, [f"JSON 파싱 실패({exc})"], None
    return validate_recommendation(obj, n_cities)


def recommend(llm: BaseLLM, travel_date: date, n_cities: int, errors: ErrorCollector, log=print) -> dict:
    """[1/3] 1차 추천. JSON 검증에 실패하면 '필수 키만 다시' 프롬프트로 딱 1번만 재요청한다.

    API 오류(인증, 한도, 네트워크)는 ApiError로 그대로 올려 보낸다(다음 단계로 갈 수 없음).
    """
    raw = llm.complete(RECOMMEND_SYSTEM, build_recommend_prompt(travel_date, n_cities), json_mode=True)
    ok, problems, data = parse_recommendation(raw, n_cities)
    if ok:
        return data

    record = errors.add(
        STEP_RECOMMEND,
        PARSE_ERROR,
        f"1차 응답 검증 실패({'; '.join(problems)}) -> 필수 키만 다시 요청(재시도 1회)",
    )
    log("  - 1차 응답을 JSON으로 읽지 못함 -> 필수 키만 다시 요청합니다(재시도 1회)")
    raw2 = llm.complete(RECOMMEND_SYSTEM, build_repair_prompt(raw, problems, n_cities), json_mode=True)
    ok, problems2, data = parse_recommendation(raw2, n_cities)
    if ok:
        record["message"] = (record["message"] + " -> 재시도 성공")[:300]
        log("  - 재시도 성공")
        return data
    raise ApiError(PARSE_ERROR, f"재시도 후에도 JSON 검증 실패({'; '.join(problems2)})"[:300])


# ---------------------------------------------------------------------------
# [3/3] 리포트 프롬프트
# ---------------------------------------------------------------------------
REPORT_SYSTEM = (
    "너는 여행 리포트 편집자다. 프로그램이 준 [데이터]만 사용해 한국어 Markdown 리포트를 쓴다. "
    "데이터에 없는 식당, 행사, 수치를 지어내지 않는다. 문장은 '~합니다'체로 짧고 구체적으로 쓴다. "
    "em dash 기호는 쓰지 않는다. 전체를 코드블록(```)으로 감싸지 않는다."
)


def placeholder(index: int) -> str:
    """리포트 안에서 프로그램이 실제 맛집 표로 바꿔 넣을 자리 표시."""
    return "{{RESTAURANTS_" + str(index) + "}}"


def build_report_prompt(date_text: str, blocks: list[dict]) -> str:
    """blocks: 지역별 {index, recommended_city, weather, events, reason, restaurants[{name, category, address}]}"""
    n = len(blocks)
    data = json.dumps(blocks, ensure_ascii=False, indent=2)
    title = f"# {date_text} 국내 여행 추천 리포트"
    if n == 1:
        frame = "\n".join([
            title, "",
            "## 추천 지역", "(지역 이름과 한 줄 소개)", "",
            "## 추천 이유", "(reason을 2~3문장으로 요약)", "",
            "## 날씨 요약", "(weather를 바탕으로 1~2문장, 옷차림이나 준비물 팁 1개)", "",
            "## 행사/축제", "(events를 글머리표(-)로 옮김, 새 행사를 추가하지 않음)", "",
            "## 맛집 추천", placeholder(1), "",
            "## 1일 일정 제안", "### 오전", "### 오후", "### 저녁",
        ])
    else:
        lines = [title, "", "## 추천 지역", f"(지역 {n}곳을 추천 순서대로 '1. 지역 이름: 한 줄 소개' 형식의 번호 목록으로 쓴다)"]
        for block in blocks:
            i = block["index"]
            lines += [
                "",
                f"## {i}. {block['recommended_city']}",
                "### 추천 이유", "### 날씨 요약", "### 행사/축제",
                "### 맛집 추천", placeholder(i),
                "### 1일 일정 제안", "('- **오전**: ...', '- **오후**: ...', '- **저녁**: ...' 세 줄의 글머리표 목록으로 쓴다)",
            ]
        frame = "\n".join(lines)
    marks = ", ".join(placeholder(b["index"]) for b in blocks)
    return (
        "아래 [데이터]로 국내 여행 리포트를 Markdown으로 작성해 줘.\n\n"
        f"[데이터]\n{data}\n[데이터 끝]\n\n"
        "[출력 틀] 제목, 섹션 이름, 순서를 글자 그대로 지킨다. 괄호 안 설명은 지시문이므로 지우고 내용으로 채운다.\n"
        f"{frame}\n\n"
        "[규칙]\n"
        f"1. {marks} 줄은 글자 그대로 한 번씩만 둔다. 그 자리는 프로그램이 실제 검색 결과 표로 채우므로 식당 목록을 직접 쓰지 않는다.\n"
        "2. 일정에 식당을 넣을 때는 해당 지역 restaurants에 있는 이름만 쓴다. restaurants가 비어 있으면 식당 이름 없이 '현지 식당'처럼 쓴다.\n"
        "3. '오류 요약' 섹션은 쓰지 않는다(프로그램이 붙인다).\n"
        "4. 행사는 일정이 바뀔 수 있다는 점을 과장 없이 반영한다.\n"
    )


def write_report(llm: BaseLLM, prompt: str) -> str:
    """[3/3] 리포트 초안(Markdown). JSON 강제 없이 자유 텍스트로 받는다."""
    return llm.complete(REPORT_SYSTEM, prompt, json_mode=False)
