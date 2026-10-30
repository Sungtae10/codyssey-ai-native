"""E2E 테스트: 실제 프로그램(travel_planner.py)을 별도 프로세스로 실행해, 로컬 가짜 API 서버와
진짜 HTTP 통신을 하게 한다. 요청 방식(GET/POST), 헤더, 파일 저장, 종료 코드를 끝에서 끝까지 확인한다.

실행: python -m unittest -v   (프로젝트 폴더에서, 다른 테스트와 함께 실행됨)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fake_api_server import VALID_KEYS, FakeApiServer  # noqa: E402

CONFIG_VARS = [
    "LLM_PROVIDER", "PLACE_PROVIDER", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "KAKAO_REST_API_KEY", "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "OPENAI_MODEL", "GEMINI_MODEL",
    "OPENAI_BASE_URL", "GEMINI_BASE_URL", "KAKAO_BASE_URL", "NAVER_BASE_URL",
]
DATE = "2026-10-10"


class CliEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = FakeApiServer().start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.results = Path(self.tmp.name) / "results"
        self.server.requests.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, llm="openai", place="kakao", drop=(), override=None):
        env = {k: v for k, v in os.environ.items() if k not in CONFIG_VARS}
        env.update(self.server.env())
        env.update({"LLM_PROVIDER": llm, "PLACE_PROVIDER": place, "PYTHONIOENCODING": "utf-8"})
        env["NO_PROXY"] = "127.0.0.1,localhost," + env.get("NO_PROXY", "")
        env["no_proxy"] = env["NO_PROXY"]
        for name in drop:
            env.pop(name, None)
        env.update(override or {})
        cmd = [sys.executable, str(ROOT / "travel_planner.py"), *args,
               "--results-dir", str(self.results), "--env-file", str(Path(self.tmp.name) / "none.env")]
        return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True,
                              encoding="utf-8", timeout=90)

    def raw(self, tag=DATE):
        return json.loads((self.results / f"{tag}_raw.json").read_text(encoding="utf-8"))

    def calls(self, prefix):
        return [r for r in self.server.requests if r["path"].startswith(prefix)]

    def test_success_openai_kakao(self):
        proc = self.run_cli("-date", DATE)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for line in ("[1/3] 1차 추천 생성 중(LLM)...", '- recommended_city: "제주"',
                     "[2/3] 맛집 검색 중(지도/장소 API)...", "맛집 5곳 검색 완료",
                     "[3/3] 최종 리포트 생성 중(LLM)...", "완료!"):
            self.assertIn(line, proc.stdout)
        self.assertTrue((self.results / f"{DATE}_travel_plan.md").is_file())
        raw = self.raw()
        self.assertEqual(raw["errors"], [])
        self.assertEqual(len(raw["restaurants"]), 5)
        llm_calls, place_calls = self.calls("/openai/"), self.calls("/kakao/")
        self.assertEqual([c["method"] for c in llm_calls], ["POST", "POST"])
        self.assertEqual([c["method"] for c in place_calls], ["GET"])
        self.assertEqual(place_calls[0]["query"]["query"], "제주 맛집")
        self.assertEqual(llm_calls[0]["headers"]["authorization"], f"Bearer {VALID_KEYS['openai']}")

    def test_gemini_naver_two_cities(self):
        proc = self.run_cli("--date", DATE, "--cities", "2", llm="gemini", place="naver")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        raw = self.raw(f"{DATE}_2cities")
        self.assertEqual([c["recommended_city"] for c in raw["recommendation"]["recommended_cities"]],
                         ["제주", "강릉"])
        self.assertEqual(len(self.calls("/naver/")), 2)
        gemini = self.calls("/gemini/")
        self.assertTrue(all("key" not in c["query"] for c in gemini))
        self.assertEqual(gemini[0]["headers"]["x-goog-api-key"], VALID_KEYS["gemini"])

    def test_wrong_kakao_key_continues(self):
        proc = self.run_cli("-date", DATE, override={"KAKAO_REST_API_KEY": "wrong-kakao-key-999"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("인증 실패(HTTP 401)", proc.stdout)
        self.assertIn("'데이터 없음'으로 처리하고 계속 진행", proc.stdout)
        error = self.raw()["errors"][0]
        self.assertEqual((error["step"], error["type"]), ("place_search", "AUTH_ERROR"))
        report = (self.results / f"{DATE}_travel_plan.md").read_text(encoding="utf-8")
        self.assertIn("데이터 없음", report)
        self.assertNotIn("wrong-kakao-key-999", report)

    def test_wrong_gemini_key_stops(self):
        proc = self.run_cli("-date", DATE, llm="gemini", override={"GEMINI_API_KEY": "wrong-gemini-key-999"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("AUTH_ERROR", proc.stderr)       # 400 API_KEY_INVALID도 인증 오류로 분류
        self.assertIn("GEMINI_API_KEY", proc.stderr)

    def test_empty_result_keyword(self):
        proc = self.run_cli("-date", DATE, "--keyword", "없는메뉴")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("검색 결과 0건", proc.stdout)
        self.assertEqual(self.raw()["errors"][0]["type"], "EMPTY_RESULT")

    def test_missing_key_exits_3(self):
        proc = self.run_cli("-date", DATE, drop=["OPENAI_API_KEY"])
        self.assertEqual(proc.returncode, 3)
        self.assertIn("[설정 오류]", proc.stderr)
        self.assertIn("OPENAI_API_KEY", proc.stderr)
        self.assertEqual(self.server.requests, [])     # 키가 없으면 API를 부르지 않는다

    def test_invalid_date_exits_2(self):
        proc = self.run_cli("-date", "2026-13-45")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage:", proc.stderr)
        self.assertEqual(self.server.requests, [])

    def test_cache_second_run(self):
        self.assertEqual(self.run_cli("-date", DATE).returncode, 0)
        self.server.requests.clear()
        proc = self.run_cli("-date", DATE)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("[캐시]", proc.stdout)
        self.assertEqual(len(self.calls("/kakao/")), 0)
        self.assertEqual(len(self.calls("/openai/")), 1)


if __name__ == "__main__":
    unittest.main()
