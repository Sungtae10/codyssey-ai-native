"""채팅 요청 횟수 제한 (OpenAI 과금 보호).

- 같은 IP: 1분에 CHAT_RATE_LIMIT_PER_MINUTE번(기본 10), 하루 CHAT_DAILY_LIMIT_PER_IP번(기본 100)
- 서버 전체: 1분에 CHAT_GLOBAL_RATE_LIMIT_PER_MINUTE번(기본 30), 하루 CHAT_DAILY_LIMIT번(기본 300)

IP는 요청 헤더로 알아내므로 마음먹고 바꾸면 피할 수 있다(최선 노력).
그래서 진짜 비용 상한은 IP와 관계없는 "서버 전체" 제한이 맡는다.
서버 메모리에 세므로 재시작하면 0부터 다시 센다. Render 무료 서버 1대 기준으로 충분하다.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from .errors import RateLimitedError

KST = timezone(timedelta(hours=9))
WINDOW = 60.0


class RateLimiter:
    def __init__(
        self,
        per_minute: int,
        per_day: int,
        global_per_minute: int = 30,
        per_ip_day: int = 100,
    ) -> None:
        self._per_minute = per_minute
        self._per_day = per_day
        self._global_per_minute = global_per_minute
        self._per_ip_day = per_ip_day
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._global_hits: deque[float] = deque()
        self._day = ""
        self._day_count = 0
        self._ip_day_count: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    @staticmethod
    def _wait(oldest: float, now: float) -> int:
        return int(WINDOW - (now - oldest)) + 1

    def check(self, key: str) -> None:
        now = time.monotonic()
        today = datetime.now(KST).date().isoformat()
        with self._lock:
            if today != self._day:  # 한국 시간 자정에 하루 횟수 초기화
                self._day, self._day_count = today, 0
                self._ip_day_count.clear()
            if self._day_count >= self._per_day:
                raise RateLimitedError(
                    f"오늘 이 서비스의 AI 질문 한도({self._per_day}회)를 모두 썼습니다. 내일 다시 시도하세요."
                )
            if self._ip_day_count[key] >= self._per_ip_day:
                raise RateLimitedError(
                    f"오늘 이 기기에서 쓸 수 있는 AI 질문 수({self._per_ip_day}회)를 모두 썼습니다. 내일 다시 시도하세요."
                )
            while self._global_hits and now - self._global_hits[0] > WINDOW:
                self._global_hits.popleft()
            if len(self._global_hits) >= self._global_per_minute:
                wait = self._wait(self._global_hits[0], now)
                raise RateLimitedError(f"지금 질문이 많아 잠시 쉬고 있어요. {wait}초 뒤에 다시 시도하세요.")
            hits = self._hits[key]
            while hits and now - hits[0] > WINDOW:
                hits.popleft()
            if len(hits) >= self._per_minute:
                raise RateLimitedError(f"질문이 너무 빠릅니다. {self._wait(hits[0], now)}초 뒤에 다시 시도하세요.")
            hits.append(now)
            self._global_hits.append(now)
            self._day_count += 1
            self._ip_day_count[key] += 1
            if len(self._hits) > 5000:  # 오래된 IP 기록 정리
                for ip in [k for k, v in self._hits.items() if not v or now - v[-1] > WINDOW]:
                    del self._hits[ip]
