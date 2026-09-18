"""AI API 호출 래퍼. 응답은 항상 JSON dict 로 돌려준다.

담당: 팀원 C
- API 키 없음 / 호출 실패 / JSON 파싱 실패 모두 None 반환 + 로그.
"""
import json
import logging
import re

log = logging.getLogger(__name__)


def call_json(system: str, user: str, cfg: dict) -> dict | None:
    ai = cfg["ai"]
    if not ai.get("api_key"):
        log.error("API 키가 설정되지 않았습니다 (.env 확인)")
        return None

    for attempt in range(2):
        try:
            text = _call(system, user, ai)
            m = re.search(r"\{.*\}", text, re.S)
            return json.loads(m.group(0) if m else text)
        except Exception as e:  # noqa: BLE001
            log.warning("AI 호출 실패(%d/2): %s", attempt + 1, e)
    log.error("AI 호출 최종 실패")
    return None


def _call(system: str, user: str, ai: dict) -> str:
    """공급자별 실제 호출. TODO(팀원 C): anthropic 분기가 필요하면 추가."""
    if ai.get("provider") == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=ai["api_key"])
        resp = client.messages.create(
            model=ai["model"], max_tokens=1024, system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text
    from openai import OpenAI
    client = OpenAI(api_key=ai["api_key"])
    resp = client.chat.completions.create(
        model=ai["model"], temperature=0.2,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content
