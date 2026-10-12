"""AI 모델 호출. 기존 DART-Foresight AI와 같은 구성(LangChain + OpenAI)을 씁니다.

- 모든 호출의 입력과 출력을 work/<기업>/llm_log.jsonl에 남깁니다.
  ("AI Agent 실행 기록" 증빙과 AI 사용 기록으로 씁니다)
- --mock으로 실행하면 인터넷 없이 가짜 모델이 돌아갑니다 (코드 점검용).
"""
import datetime
import json
import os
import re


def parse_json(text: str):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except Exception:
        return None


class LLM:
    def __init__(self, cfg, log_path, mock=False):
        self.cfg = cfg
        self.log_path = log_path
        self.mock = mock
        self._clients = {}
        if mock:
            from .mock import FakeLLM
            self._fake = FakeLLM()
        else:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
            load_dotenv()
            if not os.getenv("OPENAI_API_KEY"):
                raise SystemExit("OPENAI_API_KEY가 없습니다. engine/.env 파일에 키를 적어 주세요 (.env.example 참고).")

    def _client(self, model):
        if model not in self._clients:
            from langchain_openai import ChatOpenAI
            base = ChatOpenAI(model=model, temperature=self.cfg["llm"].get("temperature", 0))
            try:
                client = base.bind(response_format={"type": "json_object"})
            except Exception:
                client = base
            self._clients[model] = client
        return self._clients[model]

    def json(self, task: str, system: str, user: str, model_key: str, retries: int = 2):
        model = self.cfg["llm"][model_key]
        last_text = ""
        for attempt in range(retries + 1):
            if self.mock:
                text = self._fake.respond(task, system, user)
            else:
                msgs = [("system", system), ("human", user if attempt == 0 else user + "\n\n반드시 JSON 하나만 출력하세요.")]
                text = self._client(model).invoke(msgs).content
            last_text = text
            data = parse_json(text)
            self._log(task, model, system, user, text, ok=data is not None, attempt=attempt)
            if data is not None:
                return data
        raise RuntimeError(f"[{task}] 모델 응답을 JSON으로 읽지 못했습니다: {last_text[:200]}")

    def _log(self, task, model, system, user, text, ok, attempt):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        rec = {
            "time": datetime.datetime.now().isoformat(timespec="seconds"),
            "task": task, "model": "mock" if self.mock else model, "attempt": attempt, "parsed": ok,
            "system": system, "user": user, "output": text,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def get_embeddings(cfg):
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=cfg["llm"]["embed_model"])
