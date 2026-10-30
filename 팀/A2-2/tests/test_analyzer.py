"""실제 API와 DB 없이 실행하는 테스트 (팀원 C 한다혜).
실행: python -m unittest discover -s tests -t .
"""

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import ai_client
import analyzer

CFG = {"ai": {"api_key": "test-only", "model": "test-model"}}
SUMMARY = {"summary": "요약입니다.", "keywords": ["경제", "산업", "기술"], "sentiment": "neutral"}
INSIGHT = {"trends": [], "keywords": [], "common_points": [], "differences": [], "issues": [], "implications": "시사점"}


def response(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


class ClientTests(unittest.TestCase):
    def test_json_extraction(self):
        for text in ('{"a": 1}', '설명\n```json\n{"a": 1}\n```\n끝'):
            self.assertEqual(ai_client._extract_json(text), {"a": 1})
        self.assertEqual(ai_client._extract_json('설명 {오류} {"a": {"b": "}문자"}} 끝'), {"a": {"b": "}문자"}})
        for text in ('', '[]', '{"a":'):
            with self.assertRaises(ValueError):
                ai_client._extract_json(text)

    def test_missing_key(self):
        with patch.dict(sys.modules, {"openai": MagicMock()}) as modules:
            with self.assertLogs("ai_client", level="ERROR"):
                self.assertIsNone(ai_client.call_json("s", "u", {"ai": {}}))
            modules["openai"].OpenAI.assert_not_called()

    def test_retry_success_and_failure(self):
        for first_failure in (RuntimeError("failure"), response("invalid JSON")):
            sdk = MagicMock()
            create = sdk.OpenAI.return_value.__enter__.return_value.chat.completions.create
            create.side_effect = [first_failure, response('{"ok": true}')]
            with patch.dict(sys.modules, {"openai": sdk}), self.assertLogs("ai_client"):
                self.assertEqual(ai_client.call_json("system", "user", CFG), {"ok": True})
            self.assertEqual(create.call_count, 2)
            sdk.OpenAI.assert_called_with(api_key="test-only", max_retries=0, timeout=60.0)
            self.assertEqual(create.call_args.kwargs["model"], "test-model")
        sdk = MagicMock()
        create = sdk.OpenAI.return_value.__enter__.return_value.chat.completions.create
        create.side_effect = RuntimeError("failure")
        with patch.dict(sys.modules, {"openai": sdk}), self.assertLogs("ai_client", level="ERROR"):
            self.assertIsNone(ai_client.call_json("s", "u", CFG))
        self.assertEqual(create.call_count, 2)


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        # 메모리에서만 DB를 대체한다. 가짜 공용 파일은 만들지 않는다.
        self.db = MagicMock()
        self.modules = patch.dict(sys.modules, {"db": self.db})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.conn = object()

    def test_summary_limit_and_save(self):
        with patch.object(ai_client, "call_json", return_value=SUMMARY) as call:
            self.assertTrue(analyzer.summarize_one(self.conn, {"id": 7, "title": "제목", "body": "가" * 3000 + "제외"}, CFG))
        self.assertEqual(call.call_args.args[1], "제목: 제목\n본문: " + "가" * 3000)
        self.db.save_summary.assert_called_once_with(self.conn, article_id=7, model="test-model", **SUMMARY)

    def test_summary_failure(self):
        for result in (None, {}, {**SUMMARY, "sentiment": "wrong"}):
            with patch.object(ai_client, "call_json", return_value=result):
                self.assertFalse(analyzer.summarize_one(self.conn, {"id": 1}, CFG))
        self.db.save_summary.assert_not_called()
        self.db.save_summary.side_effect = RuntimeError()
        with patch.object(ai_client, "call_json", return_value=SUMMARY):
            self.assertFalse(analyzer.summarize_one(self.conn, {"id": 1}, CFG))

    def test_empty_range(self):
        self.db.get_clean.return_value = []
        with patch.object(ai_client, "call_json") as call, self.assertLogs("analyzer", level="INFO"):
            self.assertIsNone(analyzer.analyze_range(self.conn, "start", "end", None, CFG))
        call.assert_not_called()
        self.db.save_analysis.assert_not_called()

    def test_range_limits_and_save(self):
        self.db.get_clean.return_value = [
            {"title": f"title-{i}", "summary": "기존요약" if i == 0 else "", "body": "나" * 300 + "제외"}
            for i in range(61)
        ]
        with patch.object(ai_client, "call_json", return_value=INSIGHT) as call:
            self.assertEqual(analyzer.analyze_range(self.conn, "start", "end", "경제", CFG), INSIGHT)
        prompt = call.call_args.args[1]
        self.assertEqual(prompt.count("[기사 "), 60)
        self.assertIn("기존요약", prompt)
        self.assertIn("나" * 300, prompt)
        self.assertNotIn("제외", prompt)
        self.assertNotIn("title-60", prompt)
        self.db.get_clean.assert_called_once_with(self.conn, date_from="start", date_to="end", category="경제")
        self.db.save_analysis.assert_called_once_with(
            self.conn,
            {"date_from": "start", "date_to": "end", "category": "경제", "article_count": 60},
            INSIGHT,
            "test-model",
        )

    def test_range_failures(self):
        self.db.get_clean.return_value = [{"title": "기사"}]
        for result in (None, {}, {**INSIGHT, "trends": "wrong"}):
            with patch.object(ai_client, "call_json", return_value=result):
                self.assertIsNone(analyzer.analyze_range(self.conn, None, None, None, CFG))
        self.db.save_analysis.assert_not_called()
        self.db.save_analysis.side_effect = RuntimeError()
        with patch.object(ai_client, "call_json", return_value=INSIGHT):
            self.assertIsNone(analyzer.analyze_range(self.conn, None, None, None, CFG))
        self.db.get_clean.side_effect = RuntimeError()
        self.assertIsNone(analyzer.analyze_range(self.conn, None, None, None, CFG))


if __name__ == "__main__":
    unittest.main()
