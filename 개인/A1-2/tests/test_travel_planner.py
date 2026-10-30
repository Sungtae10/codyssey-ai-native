"""자동 테스트: 실제 API 키와 인터넷 없이, API 응답을 가짜로 바꿔 전체 흐름을 검증한다.

실행: python -m unittest -v   (프로젝트 폴더에서)

- 단위 테스트: 날짜 검사, 설정/키 누락, JSON 추출·검증, 지명 보정, 장소 필드 통일, HTTP 오류 분류
- 흐름 테스트: requests.request를 가짜(FakeAPI)로 바꿔 travel_planner.main()을 끝까지 실행
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import travel_planner  # noqa: E402
from planner import http_client  # noqa: E402
from planner.config import ConfigError, load_env, load_settings  # noqa: E402
from planner.errors import (  # noqa: E402
    AUTH_ERROR, EMPTY_RESULT, FORMAT_ERROR, HTTP_ERROR, NETWORK_ERROR, PARSE_ERROR, QUOTA_ERROR,
    SERVER_ERROR, ApiError, classify_http, hint_for,
)
from planner.places import KakaoPlaceClient, NaverPlaceClient, kakao_category, normalize_city  # noqa: E402
from planner.schema import REQUIRED_KEYS, extract_json, validate_recommendation  # noqa: E402
from tests import fakes  # noqa: E402

TEST_KEYS = {
    "OPENAI_API_KEY": "test-openai-key-1234567890",
    "GEMINI_API_KEY": "test-gemini-key-1234567890",
    "KAKAO_REST_API_KEY": "test-kakao-key-1234567890",
    "NAVER_CLIENT_ID": "test-naver-id-12345",
    "NAVER_CLIENT_SECRET": "test-naver-secret-12345",
}
CONFIG_VARS = [
    "LLM_PROVIDER", "PLACE_PROVIDER", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "KAKAO_REST_API_KEY", "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "OPENAI_MODEL", "GEMINI_MODEL",
    "OPENAI_BASE_URL", "GEMINI_BASE_URL", "KAKAO_BASE_URL", "NAVER_BASE_URL",
]
DATE = "2026-10-10"
SECTIONS = ["## 추천 지역", "## 추천 이유", "## 날씨 요약", "## 행사/축제", "## 맛집 추천",
            "## 1일 일정 제안", "## 오류 요약(errors)"]


# =============================================================================
# 가짜 HTTP
# =============================================================================
class FakeResponse:
    def __init__(self, status: int = 200, payload=None, text: str | None = None):
        self.status_code = status
        self._payload = payload
        if text is not None:
            self.text = text
        else:
            self.text = json.dumps(payload, ensure_ascii=False) if payload is not None else ""

    def json(self):
        if self._payload is not None:
            return self._payload
        return json.loads(self.text)  # JSON이 아니면 ValueError


class FakeAPI:
    """requests.request 대신 끼우는 가짜. 제공자별로 응답 순서를 정해 두고, 호출을 기록한다."""

    def __init__(self):
        self.queues: dict[str, list] = {"openai": [], "gemini": [], "kakao": [], "naver": []}
        self.calls: list[dict] = []

    def add(self, provider: str, *responses) -> "FakeAPI":
        self.queues[provider].extend(responses)
        return self

    @staticmethod
    def provider_of(url: str) -> str:
        if "openai" in url:
            return "openai"
        if "googleapis" in url or "generateContent" in url:
            return "gemini"
        if "kakao" in url:
            return "kakao"
        if "naver" in url:
            return "naver"
        raise AssertionError(f"알 수 없는 URL: {url}")

    def __call__(self, method, url, params=None, json=None, headers=None, timeout=None, **_):
        provider = self.provider_of(url)
        self.calls.append({"provider": provider, "method": method, "url": url, "params": params or {},
                           "json": json, "headers": headers or {}})
        queue = self.queues[provider]
        if not queue:
            raise AssertionError(f"예상하지 못한 호출: {method} {url}")
        item = queue.pop(0)
        if callable(item) and not isinstance(item, (FakeResponse, BaseException)):
            item = item(method, url, params or {}, json, headers or {})
        if isinstance(item, BaseException):
            raise item
        return item

    def count(self, provider: str) -> int:
        return sum(1 for c in self.calls if c["provider"] == provider)

    def of(self, provider: str) -> list[dict]:
        return [c for c in self.calls if c["provider"] == provider]


def openai_json(obj) -> FakeResponse:
    return FakeResponse(200, fakes.openai_chat(json.dumps(obj, ensure_ascii=False)))


def openai_text(text: str) -> FakeResponse:
    return FakeResponse(200, fakes.openai_chat(text))


def openai_report(with_placeholders: bool = True):
    """리포트 프롬프트를 읽고 지역 이름에 맞춘 초안을 돌려주는 가짜 LLM."""
    def respond(method, url, params, body, headers):
        date_text, cities = fakes.cities_from_report_prompt(body["messages"][1]["content"])
        return openai_text(fakes.report_markdown(date_text, cities, with_placeholders))
    return respond


def gemini_json(obj) -> FakeResponse:
    return FakeResponse(200, fakes.gemini_generate(json.dumps(obj, ensure_ascii=False)))


def gemini_report():
    def respond(method, url, params, body, headers):
        date_text, cities = fakes.cities_from_report_prompt(body["contents"][0]["parts"][0]["text"])
        return FakeResponse(200, fakes.gemini_generate(fakes.report_markdown(date_text, cities)))
    return respond


def kakao_ok(**kw):
    def respond(method, url, params, body, headers):
        return FakeResponse(200, fakes.kakao_keyword(params["query"], params["size"], **kw))
    return respond


def kakao_empty():
    return FakeResponse(200, {"meta": {"total_count": 0, "pageable_count": 0, "is_end": True}, "documents": []})


def naver_ok():
    def respond(method, url, params, body, headers):
        return FakeResponse(200, fakes.naver_local(params["query"], params["display"]))
    return respond


# =============================================================================
# 1. 입력(argparse)
# =============================================================================
class ArgumentTests(unittest.TestCase):
    def parse(self, *argv):
        return travel_planner.build_parser().parse_args(list(argv))

    def test_date_option_forms(self):
        for argv in (["-date", DATE], ["--date", DATE], [f"-date={DATE}"], [f"--date={DATE}"]):
            self.assertEqual(self.parse(*argv).date, date(2026, 10, 10), argv)

    def test_invalid_date_prints_usage_and_exits_2(self):
        for bad in ["2026/10/10", "2026-13-01", "2026-02-30", "26-10-10", "2026-1-5", "abc"]:
            err = io.StringIO()
            with redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
                self.parse("-date", bad)
            self.assertEqual(ctx.exception.code, 2, bad)
            self.assertIn("usage:", err.getvalue())
            self.assertIn(bad, err.getvalue())

    def test_missing_date_exits_2(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            self.parse()
        self.assertEqual(ctx.exception.code, 2)

    def test_option_ranges(self):
        for argv in (["--count", "0"], ["--count", "16"], ["--cities", "4"], ["--keyword", " "]):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
                self.parse("-date", DATE, *argv)
            self.assertEqual(ctx.exception.code, 2, argv)
        args = self.parse("-date", DATE)
        self.assertEqual((args.cities, args.count, args.keyword, args.no_cache), (1, 5, "맛집", False))


# =============================================================================
# 2. 설정(.env, 키 누락)
# =============================================================================
class ConfigTests(unittest.TestCase):
    def test_missing_keys_raise_guide(self):
        with self.assertRaises(ConfigError) as ctx:
            load_settings({})
        text = str(ctx.exception)
        for word in ["OPENAI_API_KEY", "KAKAO_REST_API_KEY", "$env:", "export ", "Copy-Item", ".env"]:
            self.assertIn(word, text)

    def test_placeholder_values_count_as_missing(self):
        with self.assertRaises(ConfigError):
            load_settings({"OPENAI_API_KEY": "YOUR_KEY", "KAKAO_REST_API_KEY": "여기에_키"})

    def test_provider_auto_selection(self):
        s = load_settings({"GEMINI_API_KEY": TEST_KEYS["GEMINI_API_KEY"],
                           "NAVER_CLIENT_ID": "id-123456", "NAVER_CLIENT_SECRET": "secret-123456"})
        self.assertEqual((s.llm_provider, s.place_provider, s.llm_model), ("gemini", "naver", "gemini-3.5-flash-lite"))
        s = load_settings({"OPENAI_API_KEY": TEST_KEYS["OPENAI_API_KEY"], "GEMINI_API_KEY": "g-1234567",
                           "KAKAO_REST_API_KEY": TEST_KEYS["KAKAO_REST_API_KEY"]})
        self.assertEqual((s.llm_provider, s.place_provider, s.llm_model), ("openai", "kakao", "gpt-4o-mini"))

    def test_cli_option_overrides_and_bad_provider(self):
        env = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "o-1234567", "GEMINI_API_KEY": "g-1234567",
               "KAKAO_REST_API_KEY": "k-1234567"}
        self.assertEqual(load_settings(env, llm_provider="gemini").llm_provider, "gemini")
        with self.assertRaises(ConfigError) as ctx:
            load_settings(dict(env, LLM_PROVIDER="claude"))
        self.assertIn("지원하지 않습니다", str(ctx.exception))

    def test_secret_not_in_repr(self):
        s = load_settings({"OPENAI_API_KEY": TEST_KEYS["OPENAI_API_KEY"],
                           "KAKAO_REST_API_KEY": TEST_KEYS["KAKAO_REST_API_KEY"]})
        self.assertNotIn(TEST_KEYS["OPENAI_API_KEY"], repr(s))
        self.assertNotIn(TEST_KEYS["KAKAO_REST_API_KEY"], s.describe())
        self.assertEqual(s.custom_base_urls(), [])  # 기본 주소면 안내 없음
        # 가짜 서버/프록시 주소를 쓰면 화면 안내에 호스트까지만 보인다(주소 속 계정 정보는 숨김)
        s = load_settings({"OPENAI_API_KEY": TEST_KEYS["OPENAI_API_KEY"],
                           "KAKAO_REST_API_KEY": TEST_KEYS["KAKAO_REST_API_KEY"],
                           "KAKAO_BASE_URL": "http://user:pw-123@127.0.0.1:8765/kakao"})
        self.assertEqual(s.custom_base_urls(), ["KAKAO_BASE_URL(http://127.0.0.1:8765)"])

    def test_env_file_encodings(self):
        """메모장(UTF-8 BOM), PowerShell 리다이렉션(UTF-16)으로 만든 .env도 읽는다."""
        content = 'OPENAI_API_KEY = "abc-1234567890"\nKAKAO_REST_API_KEY=kakao-1234567890  # 주석\n'
        for encoding in ("utf-8", "utf-8-sig", "utf-16"):
            with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {}):
                for name in CONFIG_VARS:
                    os.environ.pop(name, None)
                path = Path(tmp) / ".env"
                path.write_text(content, encoding=encoding)
                note = load_env(path)
                self.assertIn(".env 사용", note)
                self.assertEqual(os.environ.get("OPENAI_API_KEY"), "abc-1234567890", encoding)
                self.assertEqual(os.environ.get("KAKAO_REST_API_KEY"), "kakao-1234567890", encoding)

    def test_env_file_does_not_override_existing_env(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"OPENAI_API_KEY": "from-shell-123"}):
            path = Path(tmp) / ".env"
            path.write_text("OPENAI_API_KEY=from-file-123\n", encoding="utf-8")
            load_env(path)
            self.assertEqual(os.environ["OPENAI_API_KEY"], "from-shell-123")


# =============================================================================
# 3. JSON 추출과 스키마 검증
# =============================================================================
class SchemaTests(unittest.TestCase):
    GOOD = fakes.recommendation("제주")

    def test_extract_json_variants(self):
        raw = json.dumps(self.GOOD, ensure_ascii=False)
        self.assertEqual(extract_json(raw)["recommended_city"], "제주")
        self.assertEqual(extract_json(f"```json\n{raw}\n```")["recommended_city"], "제주")
        self.assertEqual(extract_json(f"추천 결과입니다.\n{raw}\n참고하세요!")["recommended_city"], "제주")
        tricky = '{"recommended_city": "제주", "weather": "중괄호 {포함} 문장", "events": ["a"], "reason": "b"}'
        self.assertEqual(extract_json("앞말 " + tricky)["weather"], "중괄호 {포함} 문장")

    def test_extract_json_failure(self):
        for bad in ["", "JSON 없음", '{"recommended_city": "제주", '] :
            with self.assertRaises(ValueError):
                extract_json(bad)

    def test_validate_ok_with_light_normalization(self):
        data = dict(self.GOOD, events="단일 행사")
        ok, problems, out = validate_recommendation(data)
        self.assertTrue(ok, problems)
        self.assertEqual(out["events"], ["단일 행사"])
        ok, _, out = validate_recommendation(dict(self.GOOD, events=["a", "b", "c", "d"], extra="버림"))
        self.assertEqual(out["events"], ["a", "b", "c"])
        self.assertEqual(set(out), set(REQUIRED_KEYS))  # 필수 키만 남고 모르는 키(extra)는 버림
        self.assertLessEqual({"recommended_city", "weather", "events", "reason"}, set(REQUIRED_KEYS))  # 과제 4개 키

    def test_validate_problems(self):
        ok, problems, _ = validate_recommendation({k: v for k, v in self.GOOD.items() if k != "reason"})
        self.assertFalse(ok)
        self.assertTrue(any("reason" in p for p in problems))
        ok, problems, _ = validate_recommendation(dict(self.GOOD, events=3))
        self.assertFalse(ok)
        ok, problems, _ = validate_recommendation(dict(self.GOOD, recommended_city="속초·양양"))
        self.assertFalse(ok)
        self.assertTrue(any("여러 개" in p for p in problems))
        ok, _, _ = validate_recommendation(["not", "dict"])
        self.assertFalse(ok)

    def test_validate_multi_cities(self):
        ok, problems, out = validate_recommendation(fakes.multi_recommendation(), n_cities=3)
        self.assertTrue(ok, problems)
        self.assertEqual(out["recommended_city"], "제주")  # 기본 스키마 유지
        self.assertEqual([c["recommended_city"] for c in out["recommended_cities"]], ["제주", "강릉", "경주"])
        ok, problems, _ = validate_recommendation(fakes.multi_recommendation(("제주", "제주", "경주")), n_cities=3)
        self.assertFalse(ok)
        ok, _, _ = validate_recommendation(fakes.multi_recommendation(("제주", "강릉")), n_cities=3)
        self.assertFalse(ok)


# =============================================================================
# 4. 지명 보정과 장소 필드 통일
# =============================================================================
class PlaceTests(unittest.TestCase):
    def test_normalize_city(self):
        cases = {
            "제주": "제주", "강릉시": "강릉", "제주특별자치도": "제주", "강원도": "강원",
            "속초·양양": "속초", "제주도 서귀포시": "서귀포", "강원 강릉": "강릉",
            "전주 한옥마을": "전주", "경주(보문단지)": "경주", "부산광역시": "부산",
            "서울 종로구": "종로", "해운대구": "해운대", "중구": "중구", "양평군": "양평",
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_city(raw), expected, raw)

    def test_kakao_fields_and_region_filter(self):
        client = KakaoPlaceClient({"rest_api_key": "k"}, "https://dapi.kakao.com")
        with mock.patch.object(KakaoPlaceClient, "_request",
                               return_value=(fakes.kakao_keyword("제주 맛집", 15, foreign=2)["documents"], {})):
            result = client.search("제주", "맛집", 5)
        self.assertEqual(result["query"], "제주 맛집")
        self.assertEqual(len(result["items"]), 5)
        for item in result["items"]:
            self.assertIn("제주", item["address"])       # 서울 결과는 걸러짐
            self.assertIsInstance(item["lat"], float)
            self.assertIsInstance(item["lng"], float)
            self.assertFalse(item["category"].startswith("음식점 >"))
            self.assertEqual(item["city"], "제주")
            for key in ("name", "address", "category", "url"):
                self.assertIsInstance(item[key], str)
        # 카테고리 그룹: 기본은 음식점(FD6), --keyword 카페면 카페(CE7)
        self.assertEqual(kakao_category("제주 맛집"), "FD6")
        self.assertEqual(kakao_category("제주 카페"), "CE7")

    def test_naver_fields(self):
        client = NaverPlaceClient({"client_id": "i", "client_secret": "s"}, "https://openapi.naver.com")
        with mock.patch.object(NaverPlaceClient, "_request",
                               return_value=(fakes.naver_local("제주 맛집", 5)["items"], {})):
            result = client.search("제주", "맛집", 5)
        first, second = result["items"][0], result["items"][1]
        self.assertNotIn("<b>", first["name"])
        self.assertIn("&", first["name"])                          # &amp; -> &
        self.assertAlmostEqual(first["lng"], 126.53, places=2)       # 1265300000 / 10^7
        self.assertAlmostEqual(first["lat"], 33.5, places=2)
        self.assertTrue(second["url"].startswith("https://map.naver.com/p/search/"))  # link가 빈 경우


# =============================================================================
# 5. HTTP 오류 분류, 재시도, 키 가리기
# =============================================================================
class HttpTests(unittest.TestCase):
    def setUp(self):
        self.sleep = mock.patch.object(http_client.time, "sleep", lambda s: None)
        self.sleep.start()

    def tearDown(self):
        self.sleep.stop()

    def test_classify_http(self):
        self.assertEqual(classify_http(401), AUTH_ERROR)
        self.assertEqual(classify_http(403), AUTH_ERROR)
        self.assertEqual(classify_http(429), QUOTA_ERROR)
        self.assertEqual(classify_http(402), QUOTA_ERROR)
        self.assertEqual(classify_http(500), SERVER_ERROR)
        self.assertEqual(classify_http(503), SERVER_ERROR)
        self.assertEqual(classify_http(404), HTTP_ERROR)
        self.assertEqual(classify_http(400, '{"error": {"message": "API key not valid."}}'), AUTH_ERROR)
        self.assertEqual(classify_http(400, '{"error": {"message": "bad"}}'), HTTP_ERROR)

    def test_transient_error_retried_once(self):
        calls = []

        def flaky(method, url, **kw):
            calls.append(url)
            if len(calls) == 1:
                raise requests.Timeout("slow")
            return FakeResponse(200, {"ok": True})

        with mock.patch.object(http_client.requests, "request", flaky):
            self.assertEqual(http_client.get_json("https://example.test/a"), {"ok": True})
        self.assertEqual(len(calls), 2)

    def test_network_error_gives_up_after_one_retry(self):
        calls = []

        def down(method, url, **kw):
            calls.append(url)
            raise requests.ConnectionError(f"failed to connect {url}")

        with mock.patch.object(http_client.requests, "request", down):
            with self.assertRaises(ApiError) as ctx:
                http_client.get_json("https://example.test/b?secret-in-url")
        self.assertEqual(ctx.exception.err_type, NETWORK_ERROR)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("secret-in-url", ctx.exception.message)   # URL을 메시지에 넣지 않음

    def test_4xx_not_retried_and_secret_masked(self):
        calls = []
        secret = "test-echo-key-1234567890"
        http_client.register_secrets([secret])

        def unauthorized(method, url, **kw):
            calls.append(url)
            return FakeResponse(401, {"errorType": "AccessDeniedError", "message": f"wrong appkey {secret}"})

        with mock.patch.object(http_client.requests, "request", unauthorized):
            with self.assertRaises(ApiError) as ctx:
                http_client.get_json("https://example.test/c")
        self.assertEqual(len(calls), 1)
        self.assertEqual(ctx.exception.err_type, AUTH_ERROR)
        self.assertTrue(ctx.exception.message.startswith("HTTP 401"))
        self.assertNotIn(secret, ctx.exception.message)
        self.assertIn("***", ctx.exception.message)

        # 카카오 공통 오류 모양 {"code", "msg"}: 문구 속 앱 키도 가리고, 403이면 카카오맵 설정을 안내
        def forbidden(method, url, **kw):
            return FakeResponse(403, {"code": -3, "msg": f"This api is not allowed by using app_key({secret})."})

        with mock.patch.object(http_client.requests, "request", forbidden):
            with self.assertRaises(ApiError) as ctx:
                http_client.get_json("https://example.test/c2")
        self.assertIn("This api is not allowed", ctx.exception.message)
        self.assertNotIn(secret, ctx.exception.message)
        self.assertIn("[카카오맵] > [사용 설정]", hint_for(ctx.exception, "kakao"))

    def test_non_json_body_is_parse_error(self):
        with mock.patch.object(http_client.requests, "request",
                               lambda *a, **k: FakeResponse(200, text="<html>not json</html>")):
            with self.assertRaises(ApiError) as ctx:
                http_client.post_json("https://example.test/d", body={})
        self.assertEqual(ctx.exception.err_type, PARSE_ERROR)


# =============================================================================
# 6. 전체 흐름 (travel_planner.main을 끝까지 실행)
# =============================================================================
class FlowTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.results = Path(self.tmp.name) / "results"
        self.env = mock.patch.dict(os.environ, {})
        self.env.start()
        for name in CONFIG_VARS:
            os.environ.pop(name, None)
        self.fake = FakeAPI()
        self.request_patch = mock.patch.object(http_client.requests, "request", self.fake)
        self.request_patch.start()
        self.sleep_patch = mock.patch.object(http_client.time, "sleep", lambda s: None)
        self.sleep_patch.start()

    def tearDown(self):
        self.sleep_patch.stop()
        self.request_patch.stop()
        self.env.stop()
        self.tmp.cleanup()

    def use(self, llm: str = "openai", place: str = "kakao") -> None:
        os.environ.update({"LLM_PROVIDER": llm, "PLACE_PROVIDER": place, **TEST_KEYS})

    def cli(self, *args) -> tuple[int, str, str]:
        argv = ["-date", DATE, *args, "--results-dir", str(self.results),
                "--env-file", str(Path(self.tmp.name) / "none.env")]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = travel_planner.main(argv)
        return code, out.getvalue(), err.getvalue()

    def raw(self, tag: str = DATE) -> dict:
        return json.loads((self.results / f"{tag}_raw.json").read_text(encoding="utf-8"))

    def report(self, tag: str = DATE) -> str:
        return (self.results / f"{tag}_travel_plan.md").read_text(encoding="utf-8")

    def assert_sections(self, md: str) -> None:
        self.assertTrue(md.startswith(f"# {DATE} 국내 여행 추천 리포트"))
        for section in SECTIONS:
            self.assertIn(section, md)
        self.assertNotIn("{{RESTAURANTS", md)
        self.assertNotIn("\u2014", md)


class FlowTests(FlowTestCase):
    def test_happy_path_openai_kakao(self):
        self.use("openai", "kakao")
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", kakao_ok())
        code, out, err = self.cli()
        self.assertEqual(code, 0, err)

        # 진행 로그 (과제 예시와 같은 흐름)
        for line in ["[1/3] 1차 추천 생성 중(LLM)...", '- recommended_city: "제주"',
                     "[2/3] 맛집 검색 중(지도/장소 API)...", "맛집 5곳 검색 완료",
                     "[3/3] 최종 리포트 생성 중(LLM)...", "- 리포트 생성 완료",
                     f"완료! {(self.results / (DATE + '_travel_plan.md')).as_posix()} 를 확인하세요."]:
            self.assertIn(line, out)

        # 원본 JSON: 1차 추천 + 맛집 목록 + errors
        raw = self.raw()
        self.assertEqual(set(raw["recommendation"]), set(REQUIRED_KEYS))  # 과제 4개 키 (단일 지역 모드)
        self.assertIsInstance(raw["recommendation"]["events"], list)
        self.assertEqual(len(raw["restaurants"]), 5)
        for item in raw["restaurants"]:
            for key in ("name", "address", "category", "url"):
                self.assertIsInstance(item[key], str)
            self.assertIsInstance(item["lat"], float)
            self.assertIsInstance(item["lng"], float)
        self.assertEqual(raw["errors"], [])
        self.assertEqual(raw["place_searches"][0]["query"], "제주 맛집")
        self.assertFalse(raw["meta"]["cache"]["used"])

        # 리포트: 필수 섹션 + 실제 맛집 이름 + 오류 없음 표기
        md = self.report()
        self.assert_sections(md)
        self.assertIn(raw["restaurants"][0]["name"], md)
        self.assertIn("- 없음 (모든 단계 정상 처리)", md)

        # REST 호출 방식: LLM은 POST(JSON 본문), 장소 검색은 GET(쿼리 파라미터), 키는 헤더로만
        rec_call, report_call = self.fake.of("openai")
        self.assertEqual(rec_call["method"], "POST")
        self.assertTrue(rec_call["url"].endswith("/chat/completions"))
        self.assertEqual(rec_call["headers"]["Authorization"], f"Bearer {TEST_KEYS['OPENAI_API_KEY']}")
        self.assertEqual(rec_call["json"]["response_format"], {"type": "json_object"})
        self.assertNotIn("response_format", report_call["json"])
        kakao_call = self.fake.of("kakao")[0]
        self.assertEqual(kakao_call["method"], "GET")
        self.assertEqual(kakao_call["headers"]["Authorization"], f"KakaoAK {TEST_KEYS['KAKAO_REST_API_KEY']}")
        self.assertEqual(kakao_call["params"]["query"], "제주 맛집")
        self.assertEqual(kakao_call["params"]["category_group_code"], "FD6")
        for call in self.fake.calls:
            for key in TEST_KEYS.values():
                self.assertNotIn(key, call["url"])

    def test_happy_path_gemini_naver(self):
        self.use("gemini", "naver")
        self.fake.add("gemini", gemini_json(fakes.recommendation("강릉")), gemini_report())
        self.fake.add("naver", naver_ok())
        code, out, err = self.cli()
        self.assertEqual(code, 0, err)
        rec_call = self.fake.of("gemini")[0]
        self.assertEqual(rec_call["method"], "POST")
        self.assertIn("/models/gemini-3.5-flash-lite:generateContent", rec_call["url"])
        self.assertNotIn("key=", rec_call["url"])
        self.assertEqual(rec_call["headers"]["x-goog-api-key"], TEST_KEYS["GEMINI_API_KEY"])
        self.assertEqual(rec_call["json"]["generationConfig"]["responseMimeType"], "application/json")
        naver_call = self.fake.of("naver")[0]
        self.assertEqual(naver_call["method"], "GET")
        self.assertEqual(naver_call["headers"]["X-Naver-Client-Id"], TEST_KEYS["NAVER_CLIENT_ID"])
        self.assertEqual(naver_call["headers"]["X-Naver-Client-Secret"], TEST_KEYS["NAVER_CLIENT_SECRET"])
        self.assertEqual(naver_call["params"]["display"], 5)
        raw = self.raw()
        self.assertEqual(raw["recommendation"]["recommended_city"], "강릉")
        self.assertEqual(len(raw["restaurants"]), 5)
        self.assertNotIn("<b>", raw["restaurants"][0]["name"])
        self.assert_sections(self.report())

    def test_empty_result_continues_with_no_data(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", kakao_empty())
        code, out, err = self.cli()
        self.assertEqual(code, 0, err)
        self.assertIn("검색 결과 0건(키워드/카테고리를 바꿔 재시도하지 않고 다음 단계로 진행)", out)
        raw = self.raw()
        self.assertEqual(raw["restaurants"], [])
        self.assertEqual(raw["errors"][0]["step"], "place_search")
        self.assertEqual(raw["errors"][0]["type"], EMPTY_RESULT)
        self.assertEqual(raw["errors"][0]["message"], "0 results for query=제주 맛집")
        md = self.report()
        self.assert_sections(md)
        self.assertIn("- 데이터 없음 (장소 검색 결과 0건", md)
        self.assertIn("EMPTY_RESULT", md)

    def test_place_auth_error_continues(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", FakeResponse(401, {"errorType": "AccessDeniedError", "message": "cannot find appkey"}))
        code, out, err = self.cli()
        self.assertEqual(code, 0, err)
        self.assertIn("- 오류: 인증 실패(HTTP 401). 키 설정을 확인하세요", out)
        self.assertIn("- 맛집 섹션은 '데이터 없음'으로 처리하고 계속 진행합니다.", out)
        self.assertIn("- 리포트 생성 완료", out)
        error = self.raw()["errors"][0]
        self.assertEqual((error["step"], error["type"]), ("place_search", AUTH_ERROR))
        self.assertTrue(error["message"].startswith("HTTP 401"))
        md = self.report()
        self.assert_sections(md)
        self.assertIn("- 데이터 없음 (장소 검색 실패: AUTH_ERROR", md)

    def test_kakao_open_map_not_enabled_hint(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", FakeResponse(403, {"errorType": "NotAuthorizedError",
                                                  "message": "App(test) disabled OPEN_MAP_AND_LOCAL service."}))
        code, out, _ = self.cli()
        self.assertEqual(code, 0)
        self.assertIn("[카카오맵] > [사용 설정] 상태를 ON", out)

    def test_place_network_error_retries_once_then_continues(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", requests.ConnectionError("down"), requests.ConnectionError("down"))
        code, out, _ = self.cli()
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.count("kakao"), 2)  # 일시적 오류는 1회만 재시도
        self.assertEqual(self.raw()["errors"][0]["type"], NETWORK_ERROR)

    def test_broken_json_repaired_with_one_retry(self):
        self.use()
        broken = '추천은 다음과 같습니다: {"recommended_city": "제주", "weather": "맑음", '
        self.fake.add("openai", openai_text(broken), openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", kakao_ok())
        code, out, err = self.cli()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.fake.count("openai"), 3)  # 1차 + 재요청 1회 + 리포트
        retry_prompt = self.fake.of("openai")[1]["json"]["messages"][1]["content"]
        self.assertIn("필수 키만 가진 JSON 객체 하나로 다시 출력", retry_prompt)
        self.assertIn("재시도 성공", out)
        error = self.raw()["errors"][0]
        self.assertEqual((error["step"], error["type"]), ("recommendation", PARSE_ERROR))
        self.assertIn("재시도 성공", error["message"])

    def test_broken_json_twice_stops_after_one_retry(self):
        self.use()
        self.fake.add("openai", openai_text("JSON 아님"), openai_text("여전히 JSON 아님"))
        code, out, err = self.cli()
        self.assertEqual(code, 1)
        self.assertEqual(self.fake.count("openai"), 2)   # 무한 재시도 없음
        self.assertEqual(self.fake.count("kakao"), 0)
        self.assertIn("[중단] 1차 추천(LLM) 단계가 실패", err)
        raw = self.raw()
        self.assertIsNone(raw["recommendation"])
        self.assertEqual([e["type"] for e in raw["errors"]], [PARSE_ERROR, PARSE_ERROR])

    def test_llm_auth_error_stops_with_hint(self):
        self.use()
        self.fake.add("openai", FakeResponse(401, {"error": {"message": "Incorrect API key provided."}}))
        code, out, err = self.cli()
        self.assertEqual(code, 1)
        self.assertIn("AUTH_ERROR", err)
        self.assertIn("OPENAI_API_KEY", err)
        self.assertFalse((self.results / f"{DATE}_travel_plan.md").exists())

    def test_report_llm_failure_falls_back_to_template(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")),
                      FakeResponse(429, {"error": {"message": "Rate limit reached"}}))
        self.fake.add("kakao", kakao_ok())
        code, out, err = self.cli()
        self.assertEqual(code, 0, err)
        self.assertIn("기본 템플릿으로 리포트를 작성하고 계속 진행합니다", out)
        md = self.report()
        self.assert_sections(md)
        for slot in ("### 오전", "### 오후", "### 저녁"):
            self.assertIn(slot, md)
        self.assertIn("프로그램 기본 템플릿으로 작성", md)
        self.assertIn("QUOTA_ERROR", md)
        self.assertEqual(self.raw()["errors"][0]["step"], "report_generation")

    def test_report_without_placeholder_falls_back_to_template(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report(with_placeholders=False))
        self.fake.add("kakao", kakao_ok())
        code, out, _ = self.cli()
        self.assertEqual(code, 0)
        md = self.report()
        self.assert_sections(md)
        self.assertNotIn("식당 A", md)          # LLM이 지어낸 식당은 들어가지 않음
        self.assertEqual(self.raw()["errors"][0]["type"], FORMAT_ERROR)

    def test_report_cleanup(self):
        """코드블록 감싸기, LLM이 쓴 오류 섹션, em dash를 정리한다."""
        self.use()

        def messy(method, url, params, body, headers):
            date_text, cities = fakes.cities_from_report_prompt(body["messages"][1]["content"])
            md = fakes.report_markdown(date_text, cities).replace("선선합니다.", "선선합니다 \u2014 겉옷 필수.")
            md += "\n\n## 오류 요약\n- LLM이 지어낸 오류"
            return openai_text(f"```markdown\n{md}\n```")

        self.fake.add("openai", openai_json(fakes.recommendation("제주")), messy)
        self.fake.add("kakao", kakao_ok())
        self.assertEqual(self.cli()[0], 0)
        md = self.report()
        self.assert_sections(md)
        self.assertNotIn("```", md)
        self.assertNotIn("LLM이 지어낸 오류", md)
        self.assertIn("선선합니다, 겉옷 필수.", md)
        self.assertEqual(md.count("## 오류 요약"), 1)

    def test_cache_hit_skips_recommendation_and_search(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", kakao_ok())
        self.assertEqual(self.cli()[0], 0)
        first_names = [r["name"] for r in self.raw()["restaurants"]]

        self.fake.calls.clear()
        self.fake.add("openai", openai_report())      # 두 번째 실행: 리포트용 LLM 1회만
        code, out, err = self.cli()
        self.assertEqual(code, 0, err)
        self.assertIn("[캐시]", out)
        self.assertEqual(self.fake.count("openai"), 1)
        self.assertEqual(self.fake.count("kakao"), 0)
        raw = self.raw()
        self.assertTrue(raw["meta"]["cache"]["used"])
        self.assertEqual([r["name"] for r in raw["restaurants"]], first_names)
        self.assertIn("캐시: 사용", self.report())

    def test_cache_not_used_after_failed_run(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", FakeResponse(401, {"message": "cannot find appkey"}))
        self.cli()
        self.fake.calls.clear()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", kakao_ok())
        code, out, _ = self.cli()
        self.assertEqual(code, 0)
        self.assertIn("이전 결과에 오류(AUTH_ERROR)가 있어 캐시로 쓰지 않습니다", out)
        self.assertEqual(self.fake.count("kakao"), 1)
        self.assertEqual(self.raw()["errors"], [])

    def test_no_cache_flag_and_changed_conditions_call_again(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", kakao_ok())
        self.cli()
        self.fake.calls.clear()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", kakao_ok())
        self.cli("--no-cache")
        self.assertEqual((self.fake.count("openai"), self.fake.count("kakao")), (2, 1))
        self.fake.calls.clear()
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", kakao_ok())
        code, out, _ = self.cli("--count", "3")
        self.assertIn("실행 조건", out)
        self.assertEqual((self.fake.count("openai"), self.fake.count("kakao")), (2, 1))
        self.assertEqual(len(self.raw()["restaurants"]), 3)

    def test_bonus_multiple_cities(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.multi_recommendation(("제주", "강릉", "경주"))), openai_report())
        self.fake.add("kakao", kakao_ok(), kakao_ok(), kakao_ok())
        code, out, err = self.cli("--cities", "3")
        self.assertEqual(code, 0, err)
        tag = f"{DATE}_3cities"
        raw = self.raw(tag)
        rec = raw["recommendation"]
        self.assertEqual(rec["recommended_city"], "제주")  # 기본 스키마 유지
        self.assertEqual([c["recommended_city"] for c in rec["recommended_cities"]], ["제주", "강릉", "경주"])
        self.assertEqual({r["city"] for r in raw["restaurants"]}, {"제주", "강릉", "경주"})
        self.assertEqual([s["query"] for s in raw["place_searches"]], ["제주 맛집", "강릉 맛집", "경주 맛집"])
        self.assertIn("[1] 제주: 맛집 5곳 검색 완료", out)
        self.assertIn("[3] 경주: 맛집 5곳 검색 완료", out)
        md = self.report(tag)
        for heading in ("## 1. 제주", "## 2. 강릉", "## 3. 경주"):
            self.assertIn(heading, md)
        self.assertEqual(md.count("| # | 이름 | 분류 | 주소 | 지도 |"), 3)
        self.assertNotIn("{{RESTAURANTS", md)
        # LLM이 목록 기호 없이 한 줄씩 쓴 부분은 글머리표로 보정(안 하면 GitHub에서 한 줄로 붙어 보임)
        self.assertIn("## 추천 지역\n- 제주\n- 강릉\n- 경주", md)
        self.assertEqual(md.count("- **오전**: 산책"), 3)
        self.assertNotIn("\n**오후**", md)
        self.assertIn("\n\n| # | 이름 |", md)  # 맛집 표는 목록으로 바뀌지 않음

    def test_bonus_multi_city_partial_failure(self):
        self.use()
        self.fake.add("openai", openai_json(fakes.multi_recommendation(("제주", "강릉"))), openai_report())
        self.fake.add("kakao", kakao_ok(), kakao_empty())
        code, out, _ = self.cli("--cities", "2")
        self.assertEqual(code, 0)
        md = self.report(f"{DATE}_2cities")
        self.assertIn("- 데이터 없음 (장소 검색 결과 0건, 검색어: 강릉 맛집)", md)
        self.assertEqual(md.count("| # | 이름 | 분류 | 주소 | 지도 |"), 1)

    def test_naver_count_is_clamped_to_five(self):
        self.use("openai", "naver")
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("naver", naver_ok())
        code, out, _ = self.cli("--count", "10")
        self.assertEqual(code, 0)
        self.assertIn("최대 5곳", out)
        self.assertEqual(self.fake.of("naver")[0]["params"]["display"], 5)

    def test_saved_files_never_contain_keys(self):
        self.use()
        leak = TEST_KEYS["KAKAO_REST_API_KEY"]
        self.fake.add("openai", openai_json(fakes.recommendation("제주")), openai_report())
        self.fake.add("kakao", FakeResponse(401, {"message": f"invalid appkey: {leak}"}))
        self.cli()
        for path in self.results.rglob("*"):
            text = path.read_text(encoding="utf-8")
            for key in TEST_KEYS.values():
                self.assertNotIn(key, text, path.name)
        self.assertIn("***", json.dumps(self.raw()["errors"], ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
