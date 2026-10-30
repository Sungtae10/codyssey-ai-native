"""AI API 호출 래퍼. 응답은 항상 JSON dict 로 돌려준다.

담당: 팀원 C (한다혜).
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    """설명과 코드펜스를 건너뛰고 JSON 객체를 찾는다."""
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            # raw_decode로 끝 위치를 찾으면 문자열 안의 중괄호도 처리된다.
            _, end = decoder.raw_decode(text, start)
            result = json.loads(text[start:end])
        except json.JSONDecodeError:
            continue
        if isinstance(result, dict):
            return result
    raise ValueError("응답에 JSON 객체가 없습니다.")


def call_json(system, user, cfg) -> dict | None:
    """최대 두 번 요청한다. 설정이나 호출에 문제가 있으면 None을 반환한다."""
    ai_cfg = cfg.get("ai", {})
    api_key = ai_cfg.get("api_key")
    if not isinstance(api_key, str) or not api_key.strip():
        logger.error("AI API 키가 없습니다. cfg['ai']['api_key']를 확인하세요.")
        return None
    model = ai_cfg.get("model")
    if not isinstance(model, str) or not model.strip():
        logger.error("AI 모델명이 없습니다. cfg['ai']['model']을 확인하세요.")
        return None

    for attempt in range(2):
        try:
            # SDK가 없어도 이 파일을 불러오거나 문법 검사할 수 있다.
            from openai import OpenAI

            # SDK 자동 재시도를 끄고 여기서만 한 번 재시도한다.
            with OpenAI(api_key=api_key, max_retries=0, timeout=60.0) as client:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return _extract_json(response.choices[0].message.content or "")
        except Exception as exc:
            # 예외 전문에는 키나 기사 내용이 포함될 수 있어 종류만 기록한다.
            if attempt == 0:
                logger.warning("AI 요청 실패(%s). 한 번 재시도합니다.", type(exc).__name__)
            else:
                logger.error("AI 요청이 두 번 모두 실패했습니다(%s).", type(exc).__name__)
    return None
