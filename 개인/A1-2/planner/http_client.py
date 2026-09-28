"""외부 API 공통 호출 함수.

- get_json()  : 장소 검색처럼 서버의 데이터를 "조회"할 때. GET, 조건은 URL 쿼리 파라미터(?query=...)
- post_json() : LLM 처럼 긴 입력을 "보내서 새 결과를 생성"할 때. POST, 입력은 JSON 본문(body)

두 함수 모두 _request() 하나를 거친다. 여기서 하는 일:
1) 응답 코드로 오류 타입을 나눈다 (401/403 인증, 429 한도, 5xx 서버, 연결 실패 네트워크, JSON 아님 파싱)
2) 일시적 오류(연결 실패, 시간 초과, 5xx)만 1회 다시 보낸다. 4xx는 다시 보내도 같으므로 바로 멈춘다.
3) 오류 메시지에 API 키가 섞여 나가지 않도록 *** 로 가린다.
"""
from __future__ import annotations

import json
import time

import requests

from .errors import NETWORK_ERROR, PARSE_ERROR, SERVER_ERROR, ApiError, classify_http

CONNECT_TIMEOUT = 10      # 서버와 연결을 맺을 때까지 기다리는 최대 시간(초)
RETRY_WAIT_SEC = 1.5      # 일시적 오류 뒤 다시 보내기 전 대기 시간(초)
TRANSIENT_RETRIES = 1     # 일시적 오류 재시도 횟수(무한 재시도 금지)

_SECRETS: list[str] = []


def register_secrets(values) -> None:
    """가려야 할 키 값을 등록한다. 이후 오류 메시지와 저장 파일에서 *** 로 바뀐다."""
    for value in values or []:
        if isinstance(value, str) and len(value) >= 6 and value not in _SECRETS:
            _SECRETS.append(value)


def mask(text) -> str:
    """등록된 키 값이 문자열에 들어 있으면 *** 로 바꾼다."""
    text = "" if text is None else str(text)
    for secret in _SECRETS:
        text = text.replace(secret, "***")
    return text


def get_json(url: str, *, params: dict | None = None, headers: dict | None = None,
             timeout: float = 15) -> dict:
    """GET 요청을 보내고 JSON 응답(dict)을 돌려준다."""
    return _request("GET", url, params=params, headers=headers, timeout=timeout)


def post_json(url: str, *, body: dict, headers: dict | None = None, timeout: float = 90) -> dict:
    """POST 요청(JSON 본문)을 보내고 JSON 응답(dict)을 돌려준다."""
    return _request("POST", url, json_body=body, headers=headers, timeout=timeout)


def _request(method: str, url: str, *, params=None, json_body=None, headers=None,
             timeout: float = 30) -> dict:
    last_error: ApiError | None = None
    for attempt in range(TRANSIENT_RETRIES + 1):
        try:
            resp = requests.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=(CONNECT_TIMEOUT, timeout),
            )
        except requests.Timeout:
            last_error = ApiError(NETWORK_ERROR, f"응답 시간 초과({timeout:g}초)")
        except requests.exceptions.SSLError:
            last_error = ApiError(NETWORK_ERROR, "보안 연결(SSL) 실패(회사/학교 네트워크의 프록시 설정 확인)")
        except requests.ConnectionError:
            last_error = ApiError(NETWORK_ERROR, "서버에 연결하지 못함(인터넷 연결, 방화벽, 프록시 확인)")
        except requests.RequestException as exc:
            # 예외 문구에는 요청 URL이 들어갈 수 있으므로 예외 이름만 남긴다.
            last_error = ApiError(NETWORK_ERROR, f"요청 실패({type(exc).__name__})")
        else:
            if resp.status_code < 400:
                return _parse_json_body(resp)
            body_text = resp.text or ""
            err_type = classify_http(resp.status_code, body_text)
            last_error = ApiError(
                err_type,
                mask(f"HTTP {resp.status_code}{_error_detail(body_text)}"),
                resp.status_code,
            )
            if err_type != SERVER_ERROR:
                raise last_error  # 4xx: 같은 요청을 다시 보내도 결과가 같으므로 바로 멈춘다
        if attempt < TRANSIENT_RETRIES:
            time.sleep(RETRY_WAIT_SEC)
    raise last_error


def _parse_json_body(resp) -> dict:
    try:
        data = resp.json()
    except ValueError:
        raise ApiError(PARSE_ERROR, "응답 본문이 JSON 형식이 아님") from None
    if not isinstance(data, dict):
        raise ApiError(PARSE_ERROR, "응답 JSON의 최상위가 객체(dict)가 아님")
    return data


def _error_detail(body_text: str) -> str:
    """제공자마다 다른 오류 본문에서 사람이 읽을 메시지 한 줄만 뽑는다.

    OpenAI/Gemini: {"error": {"message": ...}} | Kakao: {"message": ...} 또는 {"code": -401, "msg": ...}
    | Naver: {"errorMessage": ...}
    (카카오 오류 문구에는 앱 키가 그대로 들어가기도 해서, 호출하는 쪽에서 mask()로 가린다)
    """
    try:
        data = json.loads(body_text)
    except ValueError:
        return ""
    message = ""
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            message = err.get("message") or err.get("status") or ""
        elif isinstance(err, str):
            message = err
        message = message or data.get("message") or data.get("msg") or data.get("errorMessage") or ""
    message = " ".join(str(message).split())
    return f": {message[:160]}" if message else ""
