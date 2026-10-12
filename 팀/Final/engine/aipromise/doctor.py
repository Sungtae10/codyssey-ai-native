"""시작 전 점검: 첫 실제 실행 전에 설치, 키, PDF, 설정, 실제 API 1번 호출을 확인합니다.

  python run.py doctor --company samsung            (API 1번 호출 포함, 비용은 1원 안팎)
  python run.py doctor --company samsung --no-api   (인터넷 없이 설치와 파일만 확인)
"""
import importlib
import os
import sys

from .config import company_cfg, ENGINE_DIR

PACKAGES = [("langchain_openai", "langchain-openai"), ("langchain_chroma", "langchain-chroma"),
            ("chromadb", "chromadb"), ("pypdf", "pypdf"), ("dotenv", "python-dotenv"), ("yaml", "PyYAML")]


def _text_sample(path):
    """앞쪽 몇 쪽의 글자 수와 전체 쪽 수. 글자가 거의 없으면 스캔본(그림 PDF)일 수 있습니다."""
    if path.lower().endswith(".txt"):
        with open(path, encoding="utf-8") as f:
            pages = f.read().split("\f")
        return len(pages), sum(len(p) for p in pages[:5])
    from pypdf import PdfReader
    reader = PdfReader(path)
    n = len(reader.pages)
    chars = 0
    for i in range(min(n, 5)):
        chars += len((reader.pages[i].extract_text() or "").strip())
    return n, chars


def run_doctor(cfg, keys, api=True):
    problems, notes = [], []
    print("[시작 전 점검]")

    v = sys.version_info
    py_ok = v >= (3, 10)
    print(f"1. 파이썬 {v.major}.{v.minor}: " + ("OK" if py_ok else "3.10 이상이 필요합니다"))
    if not py_ok:
        problems.append("파이썬 3.10 이상을 설치하세요.")

    missing = []
    for mod, pip_name in PACKAGES:
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(pip_name)
    if missing:
        print("2. 설치: 빠진 것 " + ", ".join(missing))
        problems.append("engine 폴더에서 pip install -r requirements.txt 를 실행하세요.")
    else:
        print("2. 설치: OK")

    key = None
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ENGINE_DIR, ".env"))
        load_dotenv()
    except Exception:
        pass
    key = os.getenv("OPENAI_API_KEY")
    print("3. OpenAI 키: " + ("있음" if key else "없음"))
    if not key:
        problems.append("engine/.env 파일에 OPENAI_API_KEY=키 한 줄을 적으세요 (.env.example 참고).")

    print("4. PDF와 원문 링크")
    for k in keys:
        c = company_cfg(cfg, k)
        for r in c["promise_reports"] + c["evidence_reports"]:
            path = os.path.join(cfg["paths"]["pdf_dir"], r["pdf"])
            label = f"   {c['name']} {r['title']} ({r['pdf']})"
            if not os.path.exists(path):
                print(label + ": 파일 없음")
                problems.append(f"{r['pdf']} 를 {cfg['paths']['pdf_dir']} 에 넣으세요.")
                continue
            try:
                n, chars = _text_sample(path)
            except Exception as e:
                print(label + f": 열지 못함 ({type(e).__name__})")
                problems.append(f"{r['pdf']} 가 깨졌을 수 있습니다. DART에서 다시 받으세요.")
                continue
            if chars < 200:
                print(label + f": {n}쪽, 앞쪽 글자가 거의 없음")
                problems.append(f"{r['pdf']} 에서 글자를 읽지 못했습니다. 스캔본이면 DART 화면 글을 .txt로 저장해 쓰세요 (README 6장).")
            else:
                print(label + f": {n}쪽 OK")
            if not r.get("url"):
                notes.append(f"{c['name']} {r['title']}: config.yaml의 url이 비어 있어 화면의 원문 링크가 비게 됩니다.")

    if api and key and not missing:
        print("5. 실제 API 1번 호출")
        try:
            from .llm import LLM, get_embeddings
            log_dir = os.path.join(cfg["paths"]["work_dir"], "_doctor")
            os.makedirs(log_dir, exist_ok=True)
            llm = LLM(cfg, os.path.join(log_dir, "llm_log.jsonl"))
            data = llm.json("doctor", "너는 점검용 응답기다. JSON 하나만 출력한다.",
                            '{"ok": true} 를 그대로 출력해.', "judge_model", retries=1)
            chat_ok = data.get("ok") is True
            print(f"   판정 모델 {cfg['llm']['judge_model']}: " + ("OK" if chat_ok else f"응답이 예상과 다름 {data}"))
            if not chat_ok:
                problems.append("판정 모델 응답이 이상합니다. data/work/_doctor/llm_log.jsonl 을 확인하세요.")
            vec = get_embeddings(cfg).embed_query("AI 약속 점검")
            print(f"   임베딩 모델 {cfg['llm']['embed_model']}: OK ({len(vec)}차원)")
        except Exception as e:
            msg = str(e)
            hint = "키가 맞는지" if ("401" in msg or "auth" in msg.lower()) else \
                   "사용량 한도와 결제 상태" if ("429" in msg or "quota" in msg.lower()) else "인터넷 연결과 키"
            print(f"   실패: {type(e).__name__}: {msg[:160]}")
            problems.append(f"API 호출 실패. {hint}를 확인하세요.")
    elif api:
        print("5. 실제 API 1번 호출: 위 문제를 먼저 해결해야 시험할 수 있어요")
    else:
        print("5. 실제 API 1번 호출: 건너뜀 (--no-api)")

    print()
    for n in notes:
        print("(주의) " + n)
    if problems:
        print("고칠 것:")
        for p in problems:
            print("  - " + p)
    else:
        print("준비 완료: 이제 collect부터 실행하세요.")
    return problems
