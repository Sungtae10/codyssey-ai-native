"""AI 모델 호출. 기존 DART-Foresight AI와 같은 구성(LangChain + OpenAI)을 씁니다.

- 모든 호출의 입력과 출력을 work/<기업>/llm_log.jsonl에 남깁니다.
  ("AI Agent 실행 기록" 증빙과 AI 사용 기록으로 씁니다)
- --mock으로 실행하면 인터넷 없이 가짜 모델이 돌아갑니다 (코드 점검용).
- 10/19: temperature가 null이면 보내지 않습니다. 설정한 모델을 부르지 못하면(권한, 매개변수 오류)
  fallback_model로 바꿔 계속하고, 어떤 모델이 실제로 답했는지 기록(llm_log.jsonl, used_models)에 남깁니다.
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
        self.used_models = {}      # 작업 이름 → 실제로 답한 모델 (실행 끝에 출력)
        self.last_model = None     # 마지막 호출에서 실제로 답한 모델 (결과 파일에 남김)
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
            # 10/19: 여러 기업을 동시에 돌릴 때 요청 제한(429)에 바로 대체 모델로 넘어가지 않도록 재시도를 늘립니다
            kwargs = {"model": model, "max_retries": 6}
            temp = self.cfg["llm"].get("temperature", 0)
            if temp is not None:
                kwargs["temperature"] = temp
            base = ChatOpenAI(**kwargs)
            try:
                client = base.bind(response_format={"type": "json_object"})
            except Exception:
                client = base
            self._clients[model] = client
        return self._clients[model]

    def models_for(self, model_key: str):
        """설정한 모델, 그다음 대체 모델 순서."""
        first = self.cfg["llm"][model_key]
        fb = self.cfg["llm"].get("fallback_model")
        return [first] + ([fb] if fb and fb != first else [])

    def json(self, task: str, system: str, user: str, model_key: str, retries: int = 2):
        last_text, last_error = "", None
        for model in self.models_for(model_key):
            for attempt in range(retries + 1):
                if self.mock:
                    text = self._fake.respond(task, system, user)
                else:
                    msgs = [("system", system), ("human", user if attempt == 0 else user + "\n\n반드시 JSON 하나만 출력하세요.")]
                    try:
                        text = self._client(model).invoke(msgs).content
                    except Exception as e:  # 모델 권한 없음, 지원하지 않는 매개변수 등: 대체 모델로 넘어감
                        last_error = f"{type(e).__name__}: {str(e)[:300]}"
                        self._log(task, model, system, user, "", ok=False, attempt=attempt, error=last_error)
                        print(f"  [{task}] {model} 호출 실패, 대체 모델로 넘어갑니다: {last_error[:120]}")
                        break
                if isinstance(text, list):  # 일부 모델은 내용을 조각 목록으로 돌려줌
                    text = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in text)
                last_text = text
                data = parse_json(text)
                self._log(task, model, system, user, text, ok=data is not None, attempt=attempt)
                if data is not None:
                    self.last_model = "mock" if self.mock else model
                    self.used_models.setdefault(task, set()).add(self.last_model)
                    return data
        raise RuntimeError(f"[{task}] 모델 응답을 JSON으로 읽지 못했습니다: {(last_error or last_text)[:200]}")

    def _log(self, task, model, system, user, text, ok, attempt, error=None):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        rec = {
            "time": datetime.datetime.now().isoformat(timespec="seconds"),
            "task": task, "model": "mock" if self.mock else model, "attempt": attempt, "parsed": ok,
            "system": system, "user": user, "output": text,
        }
        if error:
            rec["error"] = error
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def get_embeddings(cfg):
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=cfg["llm"]["embed_model"], max_retries=6)
