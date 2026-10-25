"""배포 설정 파일 점검: render.yaml, 프론트 vercel.json, .gitignore가 앱 코드와 맞는지 확인한다."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]


def load_render():
    return yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))["services"][0]


def test_render_blueprint_matches_app():
    svc = load_render()
    assert svc["type"] == "web" and svc["runtime"] == "python" and svc["plan"] == "free"
    assert svc["rootDir"] == "backend" and (ROOT / "backend" / "requirements.txt").is_file()
    assert svc["startCommand"] == "uvicorn main:app --host 0.0.0.0 --port $PORT"
    assert svc["healthCheckPath"] == "/health"
    env = {e["key"]: e for e in svc["envVars"]}
    for secret in ("OPENAI_API_KEY", "FIREBASE_SERVICE_ACCOUNT_JSON"):
        assert env[secret].get("sync") is False and "value" not in env[secret]  # 키는 파일에 없음
    assert re.fullmatch(r"3\.13\.\d+", env["PYTHON_VERSION"]["value"])  # Render는 전체 버전 표기 필요


def test_render_cors_is_exact_list_only():
    env = {e["key"]: e for e in load_render()["envVars"]}
    assert "ALLOWED_ORIGIN_REGEX" not in env  # 넓은 정규식은 다른 사람의 Vercel 주소까지 허용할 수 있어 기본값에서 뺌
    origins = env["ALLOWED_ORIGINS"]["value"].split(",")
    assert origins[0] == "https://usdkrw-ai-assistant.vercel.app"
    assert all(o.startswith(("https://", "http://localhost", "http://127.0.0.1")) for o in origins)


def test_render_limits_match_app_defaults():
    from app.config import Settings

    env = {e["key"]: e.get("value") for e in load_render()["envVars"]}
    s = Settings()
    assert int(env["CHAT_RATE_LIMIT_PER_MINUTE"]) == s.chat_rate_limit_per_minute
    assert int(env["CHAT_DAILY_LIMIT_PER_IP"]) == s.chat_daily_limit_per_ip
    assert int(env["CHAT_GLOBAL_RATE_LIMIT_PER_MINUTE"]) == s.chat_global_rate_limit_per_minute
    assert int(env["CHAT_DAILY_LIMIT"]) == s.chat_daily_limit
    assert int(env["CHAT_DEADLINE_SECONDS"]) == s.chat_deadline_seconds
    assert env["OPENAI_MODEL"] == s.openai_model and env["OPENAI_FALLBACK_MODEL"] == s.openai_fallback_model


def test_vercel_config_and_gitignore():
    cfg = json.loads((ROOT / "frontend" / "vercel.json").read_text(encoding="utf-8"))
    assert cfg["outputDirectory"] == "public" and "generate-config.mjs" in cfg["buildCommand"]
    assert (ROOT / "frontend" / "public" / "index.html").is_file()
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (".env", "*-firebase-adminsdk-*.json", "firebase-key*.json", ".venv/"):
        assert pattern in ignore
