"""서비스 객체를 한곳에서 만들어 앱에 붙인다 (의존성 주입).

라우터는 request.app.state.container에서 서비스를 꺼내 쓴다.
테스트는 create_app(settings, store=MemoryStore(), llm=가짜LLM)으로 키 없이 같은 코드를 돌린다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Request

from .config import Settings
from .database import StoreProvider
from .rate_limit import RateLimiter
from .repositories.base import DocumentStore
from .services.ai_client import LLMClient
from .services.chat_service import ChatService
from .services.conversation_service import ConversationService
from .services.data_service import DataService
from .services.tools import ToolExecutor


@dataclass
class Container:
    settings: Settings
    store: StoreProvider
    data: DataService
    conversations: ConversationService
    llm: Any
    tools: ToolExecutor
    chat: ChatService
    limiter: RateLimiter


def build_container(settings: Settings, store: DocumentStore | None = None, llm: Any | None = None) -> Container:
    provider = StoreProvider(settings, store)
    data = DataService(provider.get, settings)
    conversations = ConversationService(provider.get, settings)
    llm_client = llm or LLMClient(settings)
    tools = ToolExecutor(data, conversations)
    chat = ChatService(data, conversations, llm_client, tools, settings)
    limiter = RateLimiter(
        settings.chat_rate_limit_per_minute,
        settings.chat_daily_limit,
        global_per_minute=settings.chat_global_rate_limit_per_minute,
        per_ip_day=settings.chat_daily_limit_per_ip,
    )
    return Container(settings, provider, data, conversations, llm_client, tools, chat, limiter)


def get_container(request: Request) -> Container:
    return request.app.state.container
