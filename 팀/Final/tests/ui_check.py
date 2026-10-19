"""화면 검사 (브라우저로 2~3분): results.json과 예시 데이터의 모든 화면을 휴대폰 폭과 노트북 폭으로 열어 봅니다.

화면 목록은 데이터에서 자동으로 만듭니다. results.json이 있으면 그 화면들을 보고, 예시 데이터(sample-data.js, 18개 화면, 판정 4가지와 방향성 약속이 모두 들어 있음)도
results.json 요청을 막아 한 번 더 봅니다.
다크와 라이트 두 테마에서 확인하는 것:
1. 글자 대비: 작은 글자 4.5:1, 큰 글자(24px 이상, 또는 18.66px 이상 굵게) 3:1 이상 (WCAG AA). 접힌 묶음도 펼쳐서 봅니다.
2. 가로 넘침: 390px, 320px, 1280px 폭에서 화면이 옆으로 밀리지 않는지
3. 필수 부품: 예시 데이터 띠에 배경이 있는지, 안내 문구가 작은 글자인지, "원문 보기"에 밑줄이 있는지
4. 오류: 자바스크립트 오류가 없는지, 불러오지 못한 파일이 없는지
   (results.json 막기 묶음의 404와 글꼴 CDN에 못 닿는 것은 정상이라 넘어갑니다. data/validation.json이 빠지면 문제로 잡습니다)
5. 화면이 제대로 그려졌는지: "찾는 화면이 없어요", "화면을 그리지 못했어요"가 나오면 문제입니다.
   예시 묶음은 띠에 "예시 데이터입니다"가 있어야 하고, results.json 묶음에는 없어야 합니다 (조용히 예시 데이터로 바뀐 것을 잡음).
   예시 데이터 화면은 18개여야 합니다.
6. 첫 화면 검색 (각 묶음에서 한 번): 분석 완료 기업은 결과로 가는 링크, 상장 기업(예: 현대자동차)은 "아직 분석 전",
   목록에 없는 이름은 "찾지 못했어요"가 나와야 합니다. 상장 기업 목록(data/listed-companies.json)도 불러와야 합니다.

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
WIDTHS = (390, 320, 1280)   # 글자 대비는 첫 폭에서만, 가로 넘침은 모든 폭에서 봅니다 (1280은 노트북·프로젝터)
THEMES = ("dark", "light")
ALLOWED_FAILED = ("data/results.json", "cdn.jsdelivr.net", "favicon.ico")
SAMPLE_ROUTES = 18          # 예시 데이터 화면 수 (첫 화면 1 + 기업 2곳 x (목록, 카드, 약속 6~7개))
SAMPLE_MARK = "예시 데이터입니다"
BROKEN_TEXTS = ("찾는 화면이 없어요", "화면을 그리지 못했어요")

SEARCH_JS = r"""(q) => {
  const input = document.getElementById('company-search');
  if (!input) return { missing: true };
  input.value = q; input.dispatchEvent(new Event('input', { bubbles: true }));
  const box = document.getElementById('search-results');
  return {
    links: Array.from(box.querySelectorAll('a.search-item')).map(a => a.getAttribute('href')),
    listed: box.querySelectorAll('.status-badge.is-listed').length,
    empty: box.querySelectorAll('.search-empty').length,
    help: (document.getElementById('search-help') || {}).textContent || '',
  };
}"""


def search_checks(page, tag):
    """첫 화면 검색 3상태 확인 (첫 화면을 연 직후에 부름)."""
    out = []
    page.wait_for_function("() => !document.getElementById('search-help') || !/불러오는 중/.test(document.getElementById('search-help').textContent)", timeout=5000)
    first = page.evaluate("() => { const a = document.querySelector('.company-list a.company'); return a ? { href: a.getAttribute('href'), name: a.querySelector('.company-name').textContent } : null; }")
    if first:
        r = page.evaluate(SEARCH_JS, first["name"])
        if r.get("missing"):
            return [f"[{tag}] 첫 화면에 검색창이 없음"]
        if first["href"] not in r["links"]:
            out.append(f"[{tag}] 검색 '{first['name']}': 분석 완료 결과 링크가 없음")
    else:
        out.append(f"[{tag}] 첫 화면에 분석 완료 기업이 없음")
    r = page.evaluate(SEARCH_JS, "현대자동차")
    if r.get("missing"):
        return out + [f"[{tag}] 첫 화면에 검색창이 없음"]
    if "상장 기업" not in r["help"] or "불러오지 못" in r["help"]:
        out.append(f"[{tag}] 상장 기업 목록을 불러오지 못함 ({r['help']})")
    if r["listed"] == 0:
        out.append(f"[{tag}] 검색 '현대자동차': '아직 분석 전' 결과가 없음")
    r = page.evaluate(SEARCH_JS, "없는회사이름123")
    if r["empty"] != 1:
        out.append(f"[{tag}] 검색 '없는회사이름123': '찾지 못했어요' 안내가 없음")
    page.evaluate(SEARCH_JS, "")
    return out

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
    banner_text: q('.sample-banner') ? q('.sample-banner').textContent : '',
    empty_text: Array.from(document.querySelectorAll('.empty')).map(e => e.textContent).join(' '),
  };
}"""


def _routes_for(pairs):
    out = ["#/"]
    for c, pids in pairs:
        out += [f"#/c/{c}", f"#/c/{c}/card"] + [f"#/c/{c}/p/{pid}" for pid in pids]
    return out


def passes():
    """검사할 묶음: (이름, 화면 주소들, 예시 데이터인지, results.json 요청을 막을지)."""
    ids = re.findall(r'"id": "([a-z0-9-]+)"', (APP / "data" / "sample-data.js").read_text(encoding="utf-8"))
    companies = [i for i in ids if not re.search(r"-(p|d)\d+$", i)]
    sample_routes = _routes_for([(c, [i for i in ids if i.startswith(c + "-")]) for c in companies])
    results = APP / "data" / "results.json"
    if not results.exists():
        return [("예시 데이터", sample_routes, True, False)]
    data = json.loads(results.read_text(encoding="utf-8"))
    real_routes = _routes_for([(c["id"], [p["id"] for p in c.get("promises", [])]) for c in data.get("companies", [])])
    return [("results.json", real_routes, False, False), ("예시 데이터", sample_routes, True, True)]


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
    groups = passes()
    problems = []
    evlink_pages = 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for label, rs, sample, block_results in groups:
              for theme in THEMES:
                for width in WIDTHS:
                    ctx = browser.new_context(viewport={"width": width, "height": 844})
                    if block_results:
                        ctx.route("**/data/results.json", lambda r: r.fulfill(status=404, body="not found"))
                    ctx.add_init_script(f"try {{ localStorage.setItem('ai-promise-theme', '{theme}'); }} catch (e) {{}}")
                    page = ctx.new_page()
                    tag = f"{label} {theme}"
                    page.on("pageerror", lambda e, t=tag: problems.append(f"[{t}] 자바스크립트 오류: {e}"))
                    page.on("requestfailed", lambda r, t=tag: None if any(a in r.url for a in ALLOWED_FAILED)
                            else problems.append(f"[{t}] 불러오기 실패: {r.url}"))
                    page.on("response", lambda r, t=tag: None if r.status < 400 or any(a in r.url for a in ALLOWED_FAILED)
                            else problems.append(f"[{t}] {r.status}: {r.url}"))
                    for route in rs:
                        page.goto(f"http://127.0.0.1:{port}/index.html{route}")
                        page.wait_for_timeout(400)
                        if route == "#/" and width == WIDTHS[0] and theme == THEMES[0]:
                            problems.extend(search_checks(page, tag))
                        page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
                        page.wait_for_timeout(100)
                        over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                        if over > 0:
                            problems.append(f"[{tag} {width}px] {route}: 가로로 {over}px 넘침")
                        if width != WIDTHS[0]:
                            continue
                        seen = set()
                        for x in page.evaluate(CONTRAST_JS):
                            key = (x["cls"], x["ratio"])
                            if key not in seen:
                                seen.add(key)
                                problems.append(f"[{tag}] {route}: 대비 {x['ratio']}:1 (기준 {x['need']}) .{x['cls']} '{x['text']}'")
                        parts = page.evaluate(PARTS_JS)
                        if any(b in parts["empty_text"] for b in BROKEN_TEXTS):
                            problems.append(f"[{tag}] {route}: 화면이 그려지지 않음 ({parts['empty_text'].strip()})")
                        if sample and parts["banner_bg"] in (None, "rgba(0, 0, 0, 0)", "transparent"):
                            problems.append(f"[{tag}] {route}: 예시 데이터 띠가 없거나 배경이 없음")
                        if sample and SAMPLE_MARK not in parts["banner_text"]:
                            problems.append(f"[{tag}] {route}: 예시 데이터 띠에 '{SAMPLE_MARK}'가 없음 (예시 데이터로 바뀌지 않음)")
                        if not sample and SAMPLE_MARK in parts["banner_text"]:
                            problems.append(f"[{tag}] {route}: results.json 화면인데 예시 데이터가 나옴 (결과 파일을 못 읽었거나 그리다 오류)")
                        if parts["disclaimer_px"] is None or parts["disclaimer_px"] > 13:
                            problems.append(f"[{tag}] {route}: 안내 문구가 없거나 큼 ({parts['disclaimer_px']}px)")
                        if parts["evlink_deco"] is not None:
                            evlink_pages += 1
                            if "underline" not in parts["evlink_deco"]:
                                problems.append(f"[{tag}] {route}: '원문 보기' 링크에 밑줄이 없음")
                    ctx.close()
            browser.close()
    finally:
        httpd.shutdown()

    if evlink_pages == 0:
        problems.append("원문 링크가 있는 화면을 하나도 찾지 못함 (데이터나 화면 코드 확인 필요)")
    for label, rs, sample, _ in groups:
        if sample and len(rs) != SAMPLE_ROUTES:
            problems.append(f"[{label}] 예시 데이터 화면이 {len(rs)}개입니다 ({SAMPLE_ROUTES}개여야 함, sample-data.js 확인)")
    for label, rs, _, _ in groups:
        print(f"화면 {len(rs)}개 x 테마 {len(THEMES)}개 x 폭 {len(WIDTHS)}개 확인 ({label})")
    if problems:
        for x in problems:
            print("문제:", x)
        sys.exit(1)
    print("화면 검사 통과")


if __name__ == "__main__":
    main()
