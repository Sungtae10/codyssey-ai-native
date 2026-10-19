"""화면 정적 검사 (브라우저 없이 몇 초): 화면 코드와 CSS가 서로 맞는지 봅니다.

1. app.js가 쓰는 class가 css/style.css에 모두 있는지
   (디자인 시안의 style.css를 통째로 바꾸다 10/12 부품이 빠지는 일을 막으려고 만들었어요)
2. 꼭 있어야 하는 부품 규칙(예시 데이터 띠, 안내 문구, 원문 보기 등)이 있는지
3. index.html이 CSS와 JS를 제대로 부르는지
4. 화면 문구와 예시 데이터에 단정 표현("거짓", "AI 워싱" 등)과 em dash가 없는지

사용법 (저장소 맨 위 폴더에서): python tests/test_ui_static.py
마지막 줄이 "화면 정적 검사 통과"면 됩니다.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
sys.path.insert(0, str(ROOT / "engine"))
from aipromise.textutil import FORBIDDEN_WORDS  # noqa: E402

JS = (APP / "js" / "app.js").read_text(encoding="utf-8")
CSS = (APP / "css" / "style.css").read_text(encoding="utf-8")
HTML = (APP / "index.html").read_text(encoding="utf-8")
SAMPLE = (APP / "data" / "sample-data.js").read_text(encoding="utf-8")

# 스타일 없이 다른 class와 함께 붙는 표시용 class
MODIFIER_ONLY = {"check-note"}

# 지우면 화면이 깨지거나 규칙을 어기게 되는 부품
REQUIRED_SELECTORS = [
    ".sample-banner", ".disclaimer", ".count-line", ".company-reports",
    ".verdict-confirmed", ".verdict-partial", ".verdict-not_found", ".verdict-not_pursued", ".verdict-none",
    ".directional", ".ev-foot", ".verified", ".ev-link",
]


def css_classes(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = set()
    for selector in re.findall(r"([^{}]+)\{", css):
        out |= set(re.findall(r"\.([A-Za-z_][\w-]*)", selector))
    return out


def css_selectors(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = set()
    for selector in re.findall(r"([^{}]+)\{", css):
        out |= {s.strip() for s in selector.split(",")}
    return out


def js_classes(js):
    used = set()
    for m in re.finditer(r"class(?:Name)?\s*=\s*[\"']([^\"']*)[\"']", js):
        used |= {c for c in m.group(1).split() if c}
    # 이어 붙여 만드는 class: 'verdict-' + CSS_NAME[code], 'verdict-none', check-icon의 ok/no
    names = re.search(r"CSS_NAME\s*=\s*\{([^}]*)\}", js)
    if names:
        used |= {"verdict-" + v for v in re.findall(r":\s*'([\w-]+)'", names.group(1))}
    if "'verdict-none'" in js:
        used.add("verdict-none")
    for a, b in re.findall(r"\?\s*'([\w-]+)'\s*:\s*'([\w-]+)'", js):
        if a not in ("light", "dark"):
            used |= {a, b}
    return used


def main():
    problems = []

    defined = css_classes(CSS)
    used = js_classes(JS)
    missing = sorted(c for c in used if c not in defined and c not in MODIFIER_ONLY)
    if missing:
        problems.append(f"app.js가 쓰는데 CSS에 없는 class: {missing}")

    selectors = css_selectors(CSS)
    lost = [s for s in REQUIRED_SELECTORS if s not in selectors]
    if lost:
        problems.append(f"꼭 있어야 하는 부품 규칙이 없음: {lost}")

    if CSS.count("{") != CSS.count("}"):
        problems.append(f"CSS 중괄호 짝이 안 맞음 ({{ {CSS.count('{')}개, }} {CSS.count('}')}개)")

    for need in ('href="css/style.css"', 'src="js/app.js"', 'src="data/sample-data.js"'):
        if need not in HTML:
            problems.append(f"index.html에 {need}가 없음")

    for name, text in (("app.js", JS), ("sample-data.js", SAMPLE), ("index.html", HTML), ("style.css", CSS)):
        bad = [w for w in FORBIDDEN_WORDS if w in text]
        if bad:
            problems.append(f"{name}에 단정 표현: {bad}")
        if chr(0x2014) in text:
            problems.append(f"{name}에 em dash(U+2014)가 {text.count(chr(0x2014))}개")

    # 첫 화면 검색에 쓰는 상장 기업 목록 (한국거래소 상장 종목, 기준일과 출처가 있어야 함)
    listed_path = APP / "data" / "listed-companies.json"
    try:
        listed = json.loads(listed_path.read_text(encoding="utf-8"))
        rows = listed.get("companies") or []
        names = {r[1] for r in rows if isinstance(r, list) and len(r) == 3}
        if len(rows) < 2000 or len(names) != len(rows):
            problems.append(f"listed-companies.json 형식이 이상함 (행 {len(rows)}개, 이름 {len(names)}개)")
        if not listed.get("as_of") or not listed.get("source_url") or listed.get("count") != len(rows):
            problems.append("listed-companies.json에 as_of, source_url, count(행 수와 같아야 함)가 필요함")
        for must in ("삼성전자", "SK하이닉스", "현대차"):
            if must not in names:
                problems.append(f"listed-companies.json에 {must}가 없음")
    except (OSError, ValueError) as e:
        problems.append(f"listed-companies.json을 읽지 못함: {e}")

    print(f"app.js가 쓰는 class {len(used)}개, CSS에 있는 class {len(defined)}개")
    if problems:
        for p in problems:
            print("문제:", p)
        sys.exit(1)
    print("화면 정적 검사 통과")


if __name__ == "__main__":
    main()
