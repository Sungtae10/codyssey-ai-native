"""설정 읽기.

원칙: API 키는 코드에 쓰지 않는다. 프로젝트 폴더의 .env 파일 또는 환경변수에서만 읽는다.
필요한 키가 비어 있으면 ConfigError(설정 방법 안내문 포함)를 일으켜 프로그램이 즉시 종료되게 한다.

제공자 선택 순서
1) 실행 옵션 --llm / --place
2) .env의 LLM_PROVIDER / PLACE_PROVIDER
3) 둘 다 없으면 키가 들어 있는 쪽을 자동 선택 (LLM: openai 우선, 장소: kakao 우선)
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"

LLM_PROVIDERS = ("openai", "gemini")
PLACE_PROVIDERS = ("kakao", "naver")

# 기본 모델: 2026-09 공식 문서 확인 기준. 바꾸려면 .env에 OPENAI_MODEL / GEMINI_MODEL을 적는다.
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-3.5-flash-lite",
}
# 기본 주소. 테스트(가짜 서버)나 사내 프록시를 쓸 때만 *_BASE_URL로 바꾼다.
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "kakao": "https://dapi.kakao.com",
    "naver": "https://openapi.naver.com",
}
PLACE_LABELS = {"kakao": "Kakao Local", "naver": "Naver 지역 검색"}

# 예시 값을 그대로 둔 경우도 "비어 있음"으로 본다.
_PLACEHOLDERS = {"your_key", "your-key", "yourkey", "your_api_key", "your-api-key", "changeme", "xxx", "none", "null"}


class ConfigError(Exception):
    """키 누락 등 설정 문제. 메시지에 설정 방법 안내가 들어 있다."""


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_model: str
    llm_api_key: str = field(repr=False)
    llm_base_url: str = ""
    place_provider: str = "kakao"
    place_keys: dict = field(default_factory=dict, repr=False)
    place_base_url: str = ""

    def secrets(self) -> list[str]:
        """화면/파일에 절대 나오면 안 되는 값 목록 (가리기용)."""
        return [self.llm_api_key, *self.place_keys.values()]

    def describe(self) -> str:
        return f"LLM: {self.llm_provider}({self.llm_model}) | 장소 검색: {PLACE_LABELS[self.place_provider]}"

    def custom_base_urls(self) -> list[str]:
        """기본 주소가 아닌 곳(가짜 서버, 프록시)으로 요청하는 항목. 화면 안내용이라 주소의 호스트까지만 보여 준다."""
        notes = []
        for provider, url in ((self.llm_provider, self.llm_base_url), (self.place_provider, self.place_base_url)):
            if url and url != DEFAULT_BASE_URLS[provider]:
                parts = urlsplit(url)
                try:
                    port = f":{parts.port}" if parts.port else ""
                except ValueError:  # 포트 자리에 숫자가 아닌 값
                    port = ""
                notes.append(f"{provider.upper()}_BASE_URL({parts.scheme}://{parts.hostname or '?'}{port})")
        return notes


# ---------------------------------------------------------------------------
# .env 읽기
# ---------------------------------------------------------------------------
def load_env(env_path: str | os.PathLike | None = None) -> str:
    """.env 파일을 읽어 환경변수로 올린다. 이미 설정된 환경변수는 덮어쓰지 않는다.

    반환값은 화면 안내용 한 줄 설명이다.
    """
    path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    if not path.is_file():
        return f".env 없음({path.name}), 환경변수만 사용"
    text = _read_text_any_encoding(path)
    try:
        from dotenv import load_dotenv
    except ImportError:
        _load_env_text_fallback(text)
        return f".env 사용({path.name}, 내장 파서)"
    load_dotenv(stream=io.StringIO(text), override=False)
    return f".env 사용({path.name})"


def _read_text_any_encoding(path: Path) -> str:
    """메모장/PowerShell이 만든 UTF-8(BOM 포함), UTF-16 파일도 읽는다."""
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp949", errors="replace")


def _load_env_text_fallback(text: str) -> None:
    """python-dotenv가 없을 때 쓰는 최소 파서 (KEY=VALUE 줄만 읽는다)."""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# ---------------------------------------------------------------------------
# 설정 만들기
# ---------------------------------------------------------------------------
def _clean(value) -> str:
    value = str(value or "").strip().strip('"').strip("'").strip()
    if value.lower() in _PLACEHOLDERS or "여기에" in value or value.upper().startswith("YOUR_"):
        return ""
    return value


def load_settings(environ=None, *, llm_provider: str | None = None,
                  place_provider: str | None = None) -> Settings:
    """환경변수에서 설정을 만든다. 필요한 키가 없으면 ConfigError."""
    env = os.environ if environ is None else environ

    def get(name: str) -> str:
        return _clean(env.get(name, ""))

    problems: list[str] = []
    missing: list[str] = []

    # 1) 제공자 결정
    llm = (llm_provider or get("LLM_PROVIDER")).lower()
    if not llm:
        has_gemini = bool(get("GEMINI_API_KEY") or get("GOOGLE_API_KEY"))
        llm = "gemini" if (has_gemini and not get("OPENAI_API_KEY")) else "openai"
    if llm not in LLM_PROVIDERS:
        problems.append(f"LLM_PROVIDER 값 '{llm}'은(는) 지원하지 않습니다. openai 또는 gemini로 적으세요.")

    place = (place_provider or get("PLACE_PROVIDER")).lower()
    if not place:
        place = "naver" if (get("NAVER_CLIENT_ID") and not get("KAKAO_REST_API_KEY")) else "kakao"
    if place not in PLACE_PROVIDERS:
        problems.append(f"PLACE_PROVIDER 값 '{place}'은(는) 지원하지 않습니다. kakao 또는 naver로 적으세요.")

    # 2) 키 확인
    llm_key = ""
    if llm == "openai":
        llm_key = get("OPENAI_API_KEY")
        if not llm_key:
            missing.append("OPENAI_API_KEY")
    elif llm == "gemini":
        llm_key = get("GEMINI_API_KEY") or get("GOOGLE_API_KEY")
        if not llm_key:
            missing.append("GEMINI_API_KEY")

    place_keys: dict[str, str] = {}
    if place == "kakao":
        key = get("KAKAO_REST_API_KEY")
        if key:
            place_keys["rest_api_key"] = key
        else:
            missing.append("KAKAO_REST_API_KEY")
    elif place == "naver":
        client_id, client_secret = get("NAVER_CLIENT_ID"), get("NAVER_CLIENT_SECRET")
        if client_id:
            place_keys["client_id"] = client_id
        else:
            missing.append("NAVER_CLIENT_ID")
        if client_secret:
            place_keys["client_secret"] = client_secret
        else:
            missing.append("NAVER_CLIENT_SECRET")

    if missing or problems:
        raise ConfigError(build_setup_guide(missing, problems, llm, place))

    # 3) 모델과 주소 (선택 항목)
    model = get(f"{llm.upper()}_MODEL") or DEFAULT_MODELS[llm]
    llm_base_url = (get(f"{llm.upper()}_BASE_URL") or DEFAULT_BASE_URLS[llm]).rstrip("/")
    place_base_url = (get(f"{place.upper()}_BASE_URL") or DEFAULT_BASE_URLS[place]).rstrip("/")
    return Settings(
        llm_provider=llm,
        llm_model=model,
        llm_api_key=llm_key,
        llm_base_url=llm_base_url,
        place_provider=place,
        place_keys=place_keys,
        place_base_url=place_base_url,
    )


def build_setup_guide(missing: list[str], problems: list[str], llm: str, place: str) -> str:
    """키가 없을 때 화면에 보여 줄 설정 안내문."""
    lines = ["[설정 오류] API 키 설정이 끝나지 않아 프로그램을 종료합니다."]
    if missing:
        lines.append(f"  - 비어 있거나 예시 값 그대로인 항목: {', '.join(missing)}")
    for problem in problems:
        lines.append(f"  - {problem}")
    lines.append(f"  - 현재 선택: LLM={llm}, 장소 검색={place}")
    example = missing[0] if missing else "OPENAI_API_KEY"
    lines += [
        "",
        "[방법 1] .env 파일 (권장, 프로젝트 폴더에 만들기)",
        "  1) .env.example을 복사해 .env를 만듭니다.",
        "       Windows PowerShell : Copy-Item .env.example .env",
        "       macOS / Linux      : cp .env.example .env",
        "  2) .env를 메모장 등으로 열어 '=' 뒤에 키만 붙여 넣고 저장합니다. (따옴표, 공백 없이)",
        f"       예) {example}=발급받은_키",
        "",
        "[방법 2] 환경변수 (지금 열린 터미널 창에서만 유지)",
        f'  Windows PowerShell : $env:{example}="발급받은_키"',
        f'  macOS / Linux      : export {example}="발급받은_키"',
        "",
        "[키 발급처]",
        "  OPENAI_API_KEY         : https://platform.openai.com/api-keys",
        "  GEMINI_API_KEY         : https://aistudio.google.com/apikey",
        "  KAKAO_REST_API_KEY     : https://developers.kakao.com/console/app > [앱] > [플랫폼 키] > REST API 키",
        "                           (추가로 [카카오맵] > [사용 설정] 상태 ON 필요)",
        "  NAVER_CLIENT_ID/SECRET : https://developers.naver.com > Application > 애플리케이션 등록 (사용 API: 검색)",
        "",
        "주의: 키 값은 코드, README, 스크린샷, 채팅에 절대 붙여 넣지 마세요. .env는 Git에 올리지 않습니다.",
    ]
    return "\n".join(lines)
