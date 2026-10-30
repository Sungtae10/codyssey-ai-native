"""오류 타입, 오류 목록(errors), HTTP 상태 코드 분류, 조치 안내 문구.

세 단계(1차 추천, 맛집 검색, 리포트 생성)에서 생긴 오류를 ErrorCollector 한 곳에 모은 뒤,
같은 목록을 원본 JSON의 "errors" 배열과 리포트의 "오류 요약(errors)" 섹션에 그대로 쓴다.
오류가 없어도 빈 목록([])을 남긴다.
"""
from __future__ import annotations

from datetime import datetime

# ---------------------------------------------------------------------------
# 오류 타입 이름 (원본 JSON의 errors[].type 값)
# ---------------------------------------------------------------------------
AUTH_ERROR = "AUTH_ERROR"        # 401/403: 키가 틀렸거나, 권한(서비스 사용 설정)이 없음
QUOTA_ERROR = "QUOTA_ERROR"      # 429(사용량 한도), 402(결제/크레딧 부족)
NETWORK_ERROR = "NETWORK_ERROR"  # 연결 실패, 응답 시간 초과, 보안 연결(SSL) 실패
SERVER_ERROR = "SERVER_ERROR"    # 5xx: 제공자 서버 문제
HTTP_ERROR = "HTTP_ERROR"        # 그 밖의 4xx (400 잘못된 요청, 404 모델 이름 오류 등)
PARSE_ERROR = "PARSE_ERROR"      # 응답을 읽을 수 없음 (JSON 아님, 필수 키 누락, 타입 불일치)
EMPTY_RESULT = "EMPTY_RESULT"    # 장소 검색 결과 0건 (실패가 아니라 "데이터 없음" 상태)
FORMAT_ERROR = "FORMAT_ERROR"    # LLM 리포트가 정해진 틀을 지키지 않음 (기본 템플릿으로 대체)

# ---------------------------------------------------------------------------
# 단계 이름 (원본 JSON의 errors[].step 값)
# ---------------------------------------------------------------------------
STEP_RECOMMEND = "recommendation"     # [1/3] LLM 1차 추천
STEP_PLACE = "place_search"           # [2/3] 지도/장소 API 맛집 검색
STEP_REPORT = "report_generation"     # [3/3] LLM 최종 리포트

MAX_MESSAGE_LEN = 300


class ApiError(Exception):
    """외부 API 호출 또는 응답 해석 실패를 '오류 타입'과 함께 전달한다."""

    def __init__(self, err_type: str, message: str, status: int | None = None):
        super().__init__(message)
        self.err_type = err_type
        self.message = message
        self.status = status

    def __str__(self) -> str:
        return f"{self.err_type}: {self.message}"


class ErrorCollector:
    """오류 기록을 순서대로 쌓아 두는 목록. 프로그램 전체에서 하나만 만들어 돌려쓴다."""

    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, step: str, err_type: str, message: str) -> dict:
        record = {
            "step": step,
            "type": err_type,
            "message": str(message)[:MAX_MESSAGE_LEN],
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        self.items.append(record)
        return record

    def extend(self, records) -> None:
        """캐시 파일에 남아 있던 오류 기록을 이어 붙인다."""
        for rec in records or []:
            if isinstance(rec, dict) and rec.get("type"):
                self.items.append(dict(rec))

    def to_list(self) -> list[dict]:
        return [dict(rec) for rec in self.items]

    def __len__(self) -> int:
        return len(self.items)


def classify_http(status: int, body_text: str = "") -> str:
    """HTTP 상태 코드(와 응답 본문 일부)를 오류 타입 이름으로 바꾼다."""
    if status in (401, 403):
        return AUTH_ERROR
    if status in (402, 429):
        return QUOTA_ERROR
    if status >= 500:
        return SERVER_ERROR
    # Gemini generateContent는 틀린 키에 401 대신 400(API_KEY_INVALID)을 주는 경우가 있다.
    if status == 400 and ("API_KEY_INVALID" in body_text or "API key not valid" in body_text):
        return AUTH_ERROR
    return HTTP_ERROR


def _status_text(err: ApiError) -> str:
    return f"HTTP {err.status}" if err.status else err.err_type


def hint_for(err: ApiError, provider: str = "") -> str:
    """오류 타입별로 사용자가 바로 할 일을 한 문장으로 알려 준다."""
    t = err.err_type
    msg = err.message or ""
    if t == AUTH_ERROR:
        if "OPEN_MAP_AND_LOCAL" in msg:
            return ("인증 실패(카카오맵 미사용 설정). 카카오 개발자 콘솔에서 "
                    "[카카오맵] > [사용 설정] 상태를 ON으로 바꾸세요.")
        if provider == "kakao" and err.status == 403:
            return ("권한 없음(HTTP 403). 카카오 개발자 콘솔에서 [카카오맵] > [사용 설정] 상태가 ON인지, "
                    "KAKAO_REST_API_KEY에 REST API 키를 넣었는지 확인하세요.")
        key_names = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "kakao": "KAKAO_REST_API_KEY",
            "naver": "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET",
        }
        key = key_names.get(provider, "API 키")
        return f"인증 실패({_status_text(err)}). 키 설정을 확인하세요({key} 값, 앞뒤 공백, 따옴표)."
    if t == QUOTA_ERROR:
        if provider == "openai":
            return f"사용 한도 또는 결제 문제({_status_text(err)}). OpenAI 결제(크레딧)와 사용 한도를 확인하세요."
        return f"사용량 한도 초과({_status_text(err)}). 잠시 후 다시 실행하세요."
    if t == NETWORK_ERROR:
        return "네트워크 오류. 인터넷 연결과 방화벽/프록시를 확인하세요."
    if t == SERVER_ERROR:
        return f"제공자 서버 오류({_status_text(err)}). 잠시 후 다시 실행하세요."
    if t == HTTP_ERROR and err.status == 404:
        return "요청 주소나 모델 이름이 없습니다(HTTP 404). .env의 OPENAI_MODEL / GEMINI_MODEL 값을 확인하세요."
    if t == PARSE_ERROR:
        return "응답을 읽지 못했습니다. 다시 실행하거나 다른 모델로 바꿔 보세요."
    return f"요청 실패({_status_text(err)}). 오류 내용을 확인하세요."
