"""화면 검사 (브라우저로 1~2분): 예시 데이터의 모든 화면을 휴대폰 폭으로 열어 봅니다.

화면 목록은 화면이 쓰는 데이터(results.json, 없으면 sample-data.js)에서 자동으로 만듭니다 (예시 데이터는 18개).
다크와 라이트 두 테마에서 확인하는 것:
1. 글자 대비: 작은 글자 4.5:1, 큰 글자(24px 이상, 또는 18.66px 이상 굵게) 3:1 이상 (WCAG AA). 접힌 묶음도 펼쳐서 봅니다.
2. 가로 넘침: 390px, 320px 폭에서 화면이 옆으로 밀리지 않는지
3. 필수 부품: 예시 데이터 띠에 배경이 있는지, 안내 문구가 작은 글자인지, "원문 보기"에 밑줄이 있는지
4. 오류: 자바스크립트 오류가 없는지, 불러오지 못한 파일이 없는지
   (data/results.json이 없는 것과 글꼴 CDN에 못 닿는 것은 정상이라 넘어갑니다)

준비: pip install playwright && python -m playwright install chromium
사용법 (저장소 맨 위 폴더에서): python tests/ui_check.py
마지막 줄이 "화면 검사 통과"면 됩니다.
"""
import functools
import http.server
import json
import re
import socket
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
WIDTHS = (390, 320)
THEMES = ("dark", "light")
ALLOWED_FAILED = ("data/results.json", "cdn.jsdelivr.net", "favicon.ico")

CONTRAST_JS = r"""() => {
  const parse = (s) => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const L = (c) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
  const over = (top, under) => { const a = top[3]; return [0, 1, 2].map(i => top[i] * a + under[i] * (1 - a)).concat([1]); };
  const bgOf = (el) => { const stack = []; let e = el;
    while (e && e.nodeType === 1) { const c = parse(getComputedStyle(e).backgroundColor);
      if (c && c[3] > 0) stack.push(c); if (c && c[3] >= 1) break; e = e.parentElement; }
    let base = [255, 255, 255, 1]; for (let i = stack.length - 1; i >= 0; i--) base = over(stack[i], base); return base; };
  const out = []; const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const t = walker.currentNode; if (!t.textContent.trim()) continue;
    const el = t.parentElement; if (!el || seen.has(el)) continue; seen.add(el);
    const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const r = el.getBoundingClientRect(); if (r.width === 0 || r.height === 0) continue;
    if (el.closest('.sr-only')) continue;
    let fg = parse(cs.color); const bg = bgOf(el);
    let op = 1; let e = el; while (e && e.nodeType === 1) { op *= Number(getComputedStyle(e).opacity); e = e.parentElement; }
    fg = over([fg[0], fg[1], fg[2], fg[3] * op], bg);
    const l1 = L(fg), l2 = L(bg); const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    const size = parseFloat(cs.fontSize), weight = Number(cs.fontWeight) || 400;
    const need = (size >= 24 || (size >= 18.66 && weight >= 700)) ? 3 : 4.5;
    if (ratio < need) out.push({ text: t.textContent.trim().slice(0, 20), cls: String(el.className), ratio: Math.round(ratio * 100) / 100, need });
  }
  return out;
}"""

PARTS_JS = r"""() => {
  const q = (s) => document.querySelector(s);
  const cs = (el, p) => el ? getComputedStyle(el)[p] : null;
  return {
    banner_bg: cs(q('.sample-banner'), 'backgroundColor'),
    disclaimer_px: q('.disclaimer') ? parseFloat(cs(q('.disclaimer'), 'fontSize')) : null,
    evlink_deco: cs(q('.ev-link'), 'textDecorationLine'),
  };
}"""


def routes():
    """화면 주소 목록. 화면은 results.json이 있으면 그것을, 없으면 예시 데이터를 쓰므로 같은 쪽에서 만듭니다."""
    results = APP / "data" / "results.json"
    if results.exists():
        data = json.loads(results.read_text(encoding="utf-8"))
        pairs = [(c["id"], [p["id"] for p in c.get("promises", [])]) for c in data.get("companies", [])]
        sample = False
    else:
        ids = re.findall(r'"id": "([a-z0-9-]+)"', (APP / "data" / "sample-data.js").read_text(encoding="utf-8"))
        companies = [i for i in ids if not re.search(r"-(p|d)\d+$", i)]
        pairs = [(c, [i for i in ids if i.startswith(c + "-")]) for c in companies]
        sample = True
    out = ["#/"]
    for c, pids in pairs:
        out += [f"#/c/{c}", f"#/c/{c}/card"] + [f"#/c/{c}/p/{pid}" for pid in pids]
    return out, sample


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve():
    handler = functools.partial(QuietHandler, directory=str(APP))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def main():
    httpd, port = serve()
    rs, sample = routes()
    problems = []
    evlink_pages = 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for theme in THEMES:
                for width in WIDTHS:
                    ctx = browser.new_context(viewport={"width": width, "height": 844})
                    ctx.add_init_script(f"try {{ localStorage.setItem('ai-promise-theme', '{theme}'); }} catch (e) {{}}")
                    page = ctx.new_page()
                    page.on("pageerror", lambda e, t=theme: problems.append(f"[{t}] 자바스크립트 오류: {e}"))
                    page.on("requestfailed", lambda r, t=theme: None if any(a in r.url for a in ALLOWED_FAILED)
                            else problems.append(f"[{t}] 불러오기 실패: {r.url}"))
                    page.on("response", lambda r, t=theme: None if r.status < 400 or any(a in r.url for a in ALLOWED_FAILED)
                            else problems.append(f"[{t}] {r.status}: {r.url}"))
                    for route in rs:
                        page.goto(f"http://127.0.0.1:{port}/index.html{route}")
                        page.wait_for_timeout(400)
                        page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
                        page.wait_for_timeout(100)
                        over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                        if over > 0:
                            problems.append(f"[{theme} {width}px] {route}: 가로로 {over}px 넘침")
                        if width != WIDTHS[0]:
                            continue
                        seen = set()
                        for x in page.evaluate(CONTRAST_JS):
                            key = (x["cls"], x["ratio"])
                            if key not in seen:
                                seen.add(key)
                                problems.append(f"[{theme}] {route}: 대비 {x['ratio']}:1 (기준 {x['need']}) .{x['cls']} '{x['text']}'")
                        parts = page.evaluate(PARTS_JS)
                        if sample and parts["banner_bg"] in (None, "rgba(0, 0, 0, 0)", "transparent"):
                            problems.append(f"[{theme}] {route}: 예시 데이터 띠가 없거나 배경이 없음")
                        if parts["disclaimer_px"] is None or parts["disclaimer_px"] > 13:
                            problems.append(f"[{theme}] {route}: 안내 문구가 없거나 큼 ({parts['disclaimer_px']}px)")
                        if parts["evlink_deco"] is not None:
                            evlink_pages += 1
                            if "underline" not in parts["evlink_deco"]:
                                problems.append(f"[{theme}] {route}: '원문 보기' 링크에 밑줄이 없음")
                    ctx.close()
            browser.close()
    finally:
        httpd.shutdown()

    if evlink_pages == 0:
        problems.append("원문 링크가 있는 화면을 하나도 찾지 못함 (데이터나 화면 코드 확인 필요)")
    print(f"화면 {len(rs)}개 x 테마 {len(THEMES)}개 x 폭 {len(WIDTHS)}개 확인 ({'예시 데이터' if sample else 'results.json'})")
    if problems:
        for x in problems:
            print("문제:", x)
        sys.exit(1)
    print("화면 검사 통과")


if __name__ == "__main__":
    main()
