"""
MCP 호출 흐름 확인용 클라이언트.
server.py를 stdio로 띄우고, 도구 목록을 읽은 뒤 몇 개를 실제로 불러 결과를 출력한다.

실행
  API_BASE_URL=https://<내-render-주소>.onrender.com python check_client.py
  python check_client.py --ask "최근 1년 중 가장 높았던 날은?"   # AI 비서까지 호출 (OpenAI 과금 1회)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "server.py"


def show(title: str, result) -> None:
    print(f"\n### {title}")
    data = getattr(result, "structured_content", None) or getattr(result, "structuredContent", None)
    if data is None:
        data = [getattr(c, "text", str(c)) for c in result.content]
    text = json.dumps(data, ensure_ascii=False, indent=1)
    print(text if len(text) < 1500 else text[:1500] + "\n...(생략)")


async def main(ask: str | None) -> int:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=dict(os.environ))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print("도구 목록:", ", ".join(names))
            show("get_data_summary", await session.call_tool("get_data_summary", {"reason": "MCP 점검"}))
            show(
                "get_data_by_range 2026-10",
                await session.call_tool("get_data_by_range", {"start_date": "2026-10", "end_date": "2026-10"}),
            )
            show("get_top_records desc 3", await session.call_tool("get_top_records", {"order": "desc", "limit": 3}))
            if ask:
                show("ask_assistant", await session.call_tool("ask_assistant", {"message": ask}))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ask", default=None, help="AI 비서에게 보낼 질문 (생략하면 도구만 확인)")
    sys.exit(asyncio.run(main(parser.parse_args().ask)))
