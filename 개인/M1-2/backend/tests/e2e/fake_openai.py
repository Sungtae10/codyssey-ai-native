"""
테스트용 가짜 OpenAI 서버 (로컬 전체 흐름 점검 전용, 배포에 쓰지 않음).

OPENAI_BASE_URL=http://127.0.0.1:9100/v1 로 백엔드를 띄우면, 실제 openai 라이브러리가
이 서버로 Chat Completions 요청을 보낸다. 키 없이도 다음을 확인할 수 있다.
- 백엔드가 시스템 프롬프트에 데이터 요약을 넣어 보내는지 (요청 본문을 로그 파일에 저장)
- 도구 호출(function calling) 왕복이 HTTP로 실제로 이어지는지
답변 글에는 항상 "[테스트용 가짜 모델]"을 붙여 실제 AI 답과 헷갈리지 않게 한다.

실행: python tests/e2e/fake_openai.py --port 9100 --log /tmp/fake_openai.jsonl [--delay 3]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import time

import uvicorn
from fastapi import FastAPI, Request

app = FastAPI()
LOG_PATH = None
DELAY = 0.0  # 답을 늦게 주어 화면의 "답변 중" 상태를 시험할 때 사용 (초)
TAG = "[테스트용 가짜 모델]"


def completion(model: str, content: str | None = None, tool: tuple[str, dict] | None = None) -> dict:
    message: dict = {"role": "assistant", "content": content}
    finish = "stop"
    if tool:
        name, args = tool
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": f"call_{int(time.time() * 1000)}", "type": "function",
                 "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}
            ],
        }
        finish = "tool_calls"
    return {
        "id": "chatcmpl-fake",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 1200, "completion_tokens": 80, "total_tokens": 1280},
    }


def pick_tool(question: str) -> tuple[str, dict] | None:
    if "가장 높" in question or "최고" in question:
        return "get_top_records", {"order": "desc", "limit": 3, "reason": "가장 높았던 날을 순서대로 확인하려고"}
    if "날짜별" in question or "첫째 주" in question:
        return "get_data_by_range", {"start_date": "2026-09-01", "end_date": "2026-09-07",
                                     "reason": "9월 첫째 주 값을 날짜별로 읽으려고"}
    if "크게 오른" in question or "변동" in question:
        return "get_statistics", {"reason": "하루 상승 폭이 가장 컸던 날을 확인하려고"}
    if "지난번" in question or "이전 대화" in question:
        return "list_conversations", {"limit": 5, "reason": "이전 대화 목록을 확인하려고"}
    return None


def answer_from_tool(name: str, result: dict) -> str:
    if "error" in result:
        return f"{TAG} 도구 {name}가 오류를 돌려줬어요: {result['error']}"
    if name == "get_top_records":
        rows = "\n".join(f"- {r['date']}: {r['value']:,.2f}원" for r in result.get("records", []))
        return f"{TAG} get_top_records 결과로 답해요.\n{rows}"
    if name == "get_data_by_range":
        recs = result.get("records") or []
        rows = "\n".join(f"- {r['date']}: {r['value']:,.2f}원" for r in recs)
        return (f"{TAG} {result.get('start')} ~ {result.get('end')} 값 {result.get('count')}개, "
                f"평균 {result.get('average'):,.2f}원이에요.\n{rows}")
    if name == "get_statistics":
        rises = result.get("top_rises", [])[:3]
        rows = "\n".join(f"- {r['date']}: +{r['change']:,.2f}원 ({r['change_pct']:+.2f}%)" for r in rises)
        return f"{TAG} 하루 상승 폭이 컸던 날이에요.\n{rows}"
    if name == "list_conversations":
        rows = "\n".join(f"- {c['title']}" for c in result.get("conversations", []))
        return f"{TAG} 최근 대화 목록이에요.\n{rows or '- (없음)'}"
    return f"{TAG} 도구 {name} 결과를 받았어요."


def answer_from_prompt(system: str, question: str) -> str:
    def line(prefix: str) -> str:
        m = re.search(rf"^- {re.escape(prefix)}: (.+)$", system, re.M)
        return m.group(1) if m else "(없음)"
    return (
        f"{TAG} 질문 '{question}'에 시스템 프롬프트로 받은 요약만 보고 답해요.\n"
        f"- 데이터 기간: {line('데이터 기간')}\n- 최근 트렌드: {line('최근 트렌드')}\n"
        "실제 배포에서는 이 자리에 GPT의 답이 들어가요."
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> dict:
    body = await request.json()
    if DELAY:
        await asyncio.sleep(DELAY)
    if LOG_PATH:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(body, ensure_ascii=False) + "\n")
    model = body.get("model", "fake")
    messages = body.get("messages", [])
    last = messages[-1]
    if last.get("role") == "tool":
        call_name = None
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                call_name = msg["tool_calls"][0]["function"]["name"]
                break
        return completion(model, answer_from_tool(call_name or "?", json.loads(last.get("content") or "{}")))
    question = str(last.get("content", ""))
    if body.get("tools") and body.get("tool_choice") != "none":
        tool = pick_tool(question)
        if tool:
            return completion(model, tool=tool)
    system = next((m["content"] for m in messages if m.get("role") == "system"), "")
    return completion(model, answer_from_prompt(system, question))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9100)
    parser.add_argument("--log", default=None)
    parser.add_argument("--delay", type=float, default=0.0)
    args = parser.parse_args()
    LOG_PATH = args.log
    DELAY = args.delay
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
