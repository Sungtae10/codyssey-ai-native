"""글 다듬기, 문장 나누기, 인용 검사에 쓰는 공통 함수.

인용 검사(6단계)와 수집(1단계)이 같은 normalize()를 써야
"인용문이 원문에 그대로 있다"는 판정이 흔들리지 않습니다.
"""
import re
import unicodedata

# 사람이 공시를 읽을 때 쓰는 검색어와 같게 둡니다 (서원님 안내와 동일).
DEFAULT_KEYWORDS = ["AI", "인공지능", "머신러닝", "딥러닝", "생성형", "자동화", "지능형"]

# 화면과 판정 이유에 쓰지 않는 단정 표현 (안내서 2장 규칙 4)
FORBIDDEN_WORDS = ["AI 워싱", "AI워싱", "거짓", "약속을 어김", "약속을 어겼", "실행하지 않음", "실행하지 않았"]

_QUOTE_MAP = {
    "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
    "\u00b7": "\u00b7", "\u30fb": "\u00b7", "\u2022": "\u00b7",
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u00a0": " ",
}


def normalize(text: str) -> str:
    """인용 검사용 정규화: 유니코드 통일, 따옴표·대시 통일, 모든 공백 제거."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    for a, b in _QUOTE_MAP.items():
        t = t.replace(a, b)
    return re.sub(r"\s+", "", t)


def clean_page_text(text: str) -> str:
    """PDF에서 뽑은 쪽 글을 읽기 좋게 다듬기 (줄 단위 공백 정리)."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in t.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def keyword_regex(keywords):
    """'AI'는 영문자와 붙어 있지 않을 때만 잡습니다 (예: MAIN, PAID 제외)."""
    parts = []
    for k in keywords:
        if re.fullmatch(r"[A-Za-z]+", k):
            parts.append(rf"(?<![A-Za-z]){re.escape(k)}(?![A-Za-z])")
        else:
            parts.append(re.escape(k))
    return re.compile("|".join(parts), re.IGNORECASE)


def tokenize(text: str):
    """키워드 검색용 토큰: 한글은 두 글자씩, 영문·숫자는 단어 단위."""
    t = unicodedata.normalize("NFKC", text or "").lower()
    toks = re.findall(r"[a-z]+|\d+", t)
    for chunk in re.findall(r"[가-힣]+", t):
        if len(chunk) == 1:
            toks.append(chunk)
        else:
            toks.extend(chunk[i:i + 2] for i in range(len(chunk) - 1))
    return toks


def find_forbidden(text: str):
    return [w for w in FORBIDDEN_WORDS if w in (text or "")]
