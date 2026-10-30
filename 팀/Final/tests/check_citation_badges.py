"""원문 존재 확인 표시 검사 (브라우저로 약 30초): 화면의 "원문 존재 확인" 표시가 results.json의 citation_verified 값과 같은지 봅니다.

1. 실제 데이터: 약속 상세 화면마다 "원문 존재 확인" 표시 수가 citation_verified가 true인 근거 수와 같고,
   확인 4단계(처음에는 접혀 있어 펼친 뒤 읽음)의 문구("근거 문장 N개 중 M개 원문 존재 확인")도 데이터와 같아야 합니다.
2. 일부러 바꾼 사본: 근거가 2개 이상인 첫 약속의 근거 1개를 false로 바꾼 사본에서도 1과 같은 검사를 해서,
   false인 근거에는 표시가 붙지 않는지 확인합니다 (원본 파일은 바꾸지 않음).
자바스크립트 오류가 나도 실패입니다.

준비: pip install playwright && python -m playwright install chromium
사용법 (저장소 맨 위 폴더에서): python tests/check_citation_badges.py
마지막 줄이 "원문 존재 확인 표시 검사 통과"면 됩니다.
"""
import functools
import http.server
import json
import shutil
import socket
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
DEFAULT_LABEL = "원문 존재 확인"   # app.js의 기본 문구. results.json의 labels.citation_verified_label이 있으면 그 문구를 씁니다


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):   # 요청마다 찍히는 줄을 숨깁니다
        pass


def serve(root):
    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", free_port()), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def check(root, title):
    data = json.loads((Path(root) / "data" / "results.json").read_text(encoding="utf-8"))
    label = (data.get("labels") or {}).get("citation_verified_label") or DEFAULT_LABEL
    server = serve(root)
    port = server.server_address[1]
    problems, errors, count = [], [], 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        for company in data["companies"]:
            for promise in company["promises"]:
                evidence = promise.get("evidence") or []
                want = sum(1 for e in evidence if e.get("citation_verified") is True)
                page.goto(f"http://127.0.0.1:{port}/#/c/{company['id']}/p/{promise['id']}")
                page.wait_for_selector(".quote, .empty, main", timeout=5000)
                page.wait_for_timeout(150)
                # 10/20: 확인 4단계는 처음에 접혀 있어서, 글자를 읽기 전에 펼칩니다 (tests/ui_check.py와 같은 방식)
                page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
                got = page.locator(".verified").count()
                step_ok = True
                if evidence:
                    head = "근거 문장 " if promise.get("type") != "directional" else "찾은 문장 "
                    step_ok = f"{head}{len(evidence)}개 중 {want}개 {label}" in page.inner_text("body")
                count += 1
                if got != want or not step_ok:
                    problems.append(f"{company['id']}/{promise['id']}: 데이터 {want}개, 화면 표시 {got}개, 단계 문구 {'맞음' if step_ok else '다름'}")
        browser.close()
    server.shutdown()
    server.server_close()
    print(f"[{title}] 약속 {count}개, 다른 곳 {len(problems)}개, 자바스크립트 오류 {len(errors)}개")
    for line in problems + errors:
        print("  ", line)
    return not problems and not errors


def main():
    ok = check(APP, "실제 데이터")
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "app"
        shutil.copytree(APP, copy)
        path = copy / "data" / "results.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        target = next(((c, p) for c in data["companies"] for p in c["promises"] if len(p.get("evidence") or []) >= 2), None)
        if target is None:
            print("근거가 2개 이상인 약속이 없어 바꾼 사본 검사는 건너뜁니다")
        else:
            target[1]["evidence"][0]["citation_verified"] = False
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            print(f"바꾼 사본: {target[0]['id']}/{target[1]['id']}의 근거 {len(target[1]['evidence'])}개 중 1개를 false로")
            ok = check(copy, "바꾼 사본") and ok
    print("원문 존재 확인 표시 검사 통과" if ok else "원문 존재 확인 표시 검사 실패")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
