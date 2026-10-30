"""가짜 API 서버 (E2E 테스트용).

OpenAI, Gemini, Kakao Local, Naver 지역 검색의 요청 주소와 응답 모양을 흉내 내는 로컬 HTTP 서버다.
프로그램은 *_BASE_URL 환경변수로 이 서버를 가리키면, 코드 수정 없이 실제와 같은 방식(헤더, GET/POST,
JSON 본문)으로 요청을 보낸다. 키가 틀리면 실제 서비스처럼 401/400을 돌려준다.

단독 실행(연습용, 실제 키 없이 흐름만 확인):
    python tests/fake_api_server.py
    -> 화면에 나오는 환경변수를 설정한 뒤 --results-dir practice_results로 실행
"""
from __future__ import annotations

import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import fakes  # noqa: E402

# 연습용 키: "e2e-"로 시작하는 8자 이상 값은 모두 올바른 키로 받는다(검증할 때 키 값을 바꿔 써도 되게).
# 아래 값은 env()가 기본으로 나눠 주는 예시일 뿐 실제 키가 아니다.
VALID_PREFIX = "e2e-"
VALID_KEYS = {
    "openai": "e2e-openai-key-000000",
    "gemini": "e2e-gemini-key-000000",
    "kakao": "e2e-kakao-key-000000",
    "naver_id": "e2e-naver-id-000000",
    "naver_secret": "e2e-naver-secret-000000",
}
SINGLE_CITY = "제주"
MULTI_CITIES = ["제주", "강릉", "경주"]


def _key_ok(value: str | None) -> bool:
    return bool(value) and value.startswith(VALID_PREFIX) and len(value) >= 8


def _header_key(value: str | None, scheme: str) -> str:
    """'KakaoAK 키', 'Bearer 키' 모양의 헤더에서 키만 꺼낸다. 모양이 다르면 빈 문자열."""
    prefix = f"{scheme} "
    return value[len(prefix):] if value and value.startswith(prefix) else ""


class FakeApiHandler(BaseHTTPRequestHandler):
    server_version = "FakeApi/1.0"

    def log_message(self, fmt, *args):  # 테스트 화면을 조용하게
        pass

    # ------------------------------------------------------------ 공통
    def _record(self, body=None):
        parsed = urlparse(self.path)
        self.server.requests.append({
            "method": self.command,
            "path": parsed.path,
            "query": {k: v[0] for k, v in parse_qs(parsed.query).items()},
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": body,
        })
        return parsed

    def _send(self, status: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            return None

    # ------------------------------------------------------------ GET: 장소 검색
    def do_GET(self):
        parsed = self._record()
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if parsed.path == "/kakao/v2/local/search/keyword.json":
            if not _key_ok(_header_key(self.headers.get("Authorization"), "KakaoAK")):
                return self._send(401, {"errorType": "AccessDeniedError", "message": "cannot find appkey"})
            if "없는메뉴" in query.get("query", ""):
                return self._send(200, {"meta": {"total_count": 0, "pageable_count": 0, "is_end": True},
                                        "documents": []})
            return self._send(200, fakes.kakao_keyword(query.get("query", ""), int(query.get("size", 15))))
        if parsed.path == "/naver/v1/search/local.json":
            if not (_key_ok(self.headers.get("X-Naver-Client-Id"))
                    and _key_ok(self.headers.get("X-Naver-Client-Secret"))):
                return self._send(401, {"errorMessage": "Authentication failed (인증에 실패했습니다.)",
                                        "errorCode": "024"})
            return self._send(200, fakes.naver_local(query.get("query", ""), int(query.get("display", 5))))
        return self._send(404, {"error": {"message": f"unknown path {parsed.path}"}})

    # ------------------------------------------------------------ POST: LLM
    def do_POST(self):
        body = self._body()
        parsed = self._record(body)
        if parsed.path == "/openai/v1/chat/completions":
            if not _key_ok(_header_key(self.headers.get("Authorization"), "Bearer")):
                return self._send(401, {"error": {"message": "Incorrect API key provided.",
                                                  "type": "invalid_request_error", "code": "invalid_api_key"}})
            user = body["messages"][-1]["content"]
            json_mode = (body.get("response_format") or {}).get("type") == "json_object"
            return self._send(200, fakes.openai_chat(_answer(user, json_mode)))
        match = re.fullmatch(r"/gemini/v1beta/models/([^/:]+):generateContent", parsed.path)
        if match:
            if parsed.query and "key=" in parsed.query:
                return self._send(400, {"error": {"message": "키를 URL에 넣지 마세요(테스트 규칙)"}})
            if not _key_ok(self.headers.get("x-goog-api-key")):
                return self._send(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT",
                                                  "message": "API key not valid. Please pass a valid API key.",
                                                  "details": [{"reason": "API_KEY_INVALID"}]}})
            user = body["contents"][-1]["parts"][0]["text"]
            json_mode = (body.get("generationConfig") or {}).get("responseMimeType") == "application/json"
            return self._send(200, fakes.gemini_generate(_answer(user, json_mode)))
        return self._send(404, {"error": {"message": f"unknown path {parsed.path}"}})


def _answer(prompt: str, json_mode: bool) -> str:
    """가짜 LLM: 1차 추천이면 JSON, 리포트면 틀을 지킨 Markdown."""
    if json_mode:
        if "recommended_cities" in prompt:
            n = int(re.search(r"정확히 (\d+)개", prompt).group(1))
            return json.dumps(fakes.multi_recommendation(MULTI_CITIES[:n]), ensure_ascii=False)
        return json.dumps(fakes.recommendation(SINGLE_CITY), ensure_ascii=False)
    date_text, cities = fakes.cities_from_report_prompt(prompt)
    return fakes.report_markdown(date_text, cities)


class FakeApiServer:
    """with 문이나 start()/stop()으로 쓰는 백그라운드 서버."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.httpd = ThreadingHTTPServer((host, port), FakeApiHandler)
        self.httpd.requests = []
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def requests(self) -> list[dict]:
        return self.httpd.requests

    def env(self) -> dict[str, str]:
        base = self.base_url
        return {
            "OPENAI_BASE_URL": f"{base}/openai/v1",
            "GEMINI_BASE_URL": f"{base}/gemini/v1beta",
            "KAKAO_BASE_URL": f"{base}/kakao",
            "NAVER_BASE_URL": f"{base}/naver",
            "OPENAI_API_KEY": VALID_KEYS["openai"],
            "GEMINI_API_KEY": VALID_KEYS["gemini"],
            "KAKAO_REST_API_KEY": VALID_KEYS["kakao"],
            "NAVER_CLIENT_ID": VALID_KEYS["naver_id"],
            "NAVER_CLIENT_SECRET": VALID_KEYS["naver_secret"],
        }

    def start(self) -> "FakeApiServer":
        self.thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


if __name__ == "__main__":
    server = FakeApiServer(port=int(sys.argv[1]) if len(sys.argv) > 1 else 8765).start()
    print(f"가짜 API 서버 실행 중: {server.base_url}  (끝내려면 Ctrl+C)")
    print("다른 PowerShell 창에서 아래를 붙여 넣은 뒤 실행하세요 (연습용 키, 실제 키 아님):")
    for name, value in server.env().items():
        print(f'  $env:{name}="{value}"')
    print('  python travel_planner.py -date "2026-10-10" --results-dir practice_results')
    print("연습이 끝나면 환경변수를 넣은 PowerShell 창을 닫으세요. 그 창에서 실제 실행을 하면 가짜 주소로 요청합니다.")
    try:
        server.thread.join()
    except KeyboardInterrupt:
        server.stop()
