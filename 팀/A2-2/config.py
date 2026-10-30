"""설정 파일(config.json)과 환경변수(.env)를 읽고 로깅을 초기화한다.

담당: 팀원 A (팀장)
- load_config(): config.json 이 없으면 config.example.json 을 대신 읽는다.
- API 키는 코드나 config.json 에 쓰지 않고 .env 의 환경변수에서만 읽는다.
"""
import json
import logging
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _abs(path: str) -> str:
    """상대경로를 프로젝트 루트 기준 절대경로로 바꾼다."""
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


def load_config() -> dict:
    load_dotenv(os.path.join(BASE_DIR, ".env"))

    cfg_path = os.path.join(BASE_DIR, "config.json")
    if not os.path.exists(cfg_path):
        cfg_path = os.path.join(BASE_DIR, "config.example.json")
        logging.getLogger(__name__).warning("config.json 이 없어 config.example.json 을 사용합니다.")

    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    cfg["db_path"] = _abs(cfg.get("db_path", "data/news.db"))
    cfg["output_dir"] = _abs(cfg.get("output_dir", "output"))
    os.makedirs(os.path.dirname(cfg["db_path"]), exist_ok=True)
    os.makedirs(cfg["output_dir"], exist_ok=True)

    ai = cfg.setdefault("ai", {})
    provider = ai.get("provider", "openai")
    key_name = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
    ai["api_key"] = os.getenv(key_name)  # 없으면 None, ai_client 에서 처리
    return cfg


def setup_logging(level: str = "INFO") -> None:
    os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(levelname)s] %(asctime)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(BASE_DIR, "logs", "app.log"), encoding="utf-8"),
        ],
    )
