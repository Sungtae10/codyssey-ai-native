"""0단계: OpenDART에서 보고서를 자동으로 찾고 받아 글(.txt)로 바꿉니다. (10/19 추가)

사람이 DART에서 PDF를 받는 단계를 대신합니다. 받은 글은 1단계(collect)가 PDF 대신 읽습니다.

하는 일 (기업마다)
1. 기업 고유번호(corp_code) 찾기: config에 corp_code가 있으면 그대로 쓰고, 없으면 OpenDART 기업 목록에서
   종목코드(stock_code, 상장사) 또는 정확히 같은 이름으로 찾습니다. 이름이 같은 법인이 여럿이면
   필요한 보고서를 실제로 낸 법인만 남기고, 그래도 여럿이면 멈춥니다 (예: 신한은행과 신한지주는 다른 법인).
2. 정기공시 목록(list.json)에서 보고서 키에 맞는 보고서를 고릅니다.
   y2024 → "사업보고서 (2024.12)", y2025 → "사업보고서 (2025.12)", h2026 → "반기보고서 (2026.06)".
   정정 보고서가 있으면 가장 늦게 낸 것을 쓰되, 첨부서류만 고친 정정([첨부정정], [첨부추가])보다 본문이 든 보고서를 먼저 씁니다.
3. 공시서류 원본(document.xml, ZIP 안의 XML)을 받아 본문 XML을 글로 바꿉니다.
   장 제목(TITLE)은 따로 한 줄로 두어 1단계가 "II. 사업의 내용" 같은 제목 줄로 장을 찾게 하고,
   큰 장(SECTION-1)마다 쪽 구분(\\f)을 넣어 목차가 있어도 본문과 섞이지 않게 합니다.
   이 쪽은 PDF 쪽 번호와 다르므로 화면에는 쪽 번호를 내보내지 않습니다 (collect에서 page를 비움).
4. data/dart/<기업>_<보고서키>.txt와 data/dart/manifest.json(접수번호, 보고서 이름, DART 원문 주소, 글자 수)을 남깁니다.
   원문 주소는 https://dart.fss.or.kr/dsaf001/main.do?rcpNo=<접수번호> 로, 화면의 "원문 보기" 링크가 됩니다.

인증키는 환경 변수 OPENDART_API_KEY(또는 engine/.env)에서만 읽고, 화면·기록·오류 메시지에 절대 찍지 않습니다.
"""
import datetime
import hashlib
import html
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

API = "https://opendart.fss.or.kr/api"
VIEWER = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={}"
UA = "ai-promise-engine/1.0 (+https://github.com/Sungtae10/ai-promise)"

# OpenDART 응답 상태 코드 (개발가이드 기준)
STATUS_HINT = {
    "010": "등록되지 않은 인증키입니다",
    "011": "사용할 수 없는 인증키입니다",
    "012": "접근할 수 없는 IP입니다",
    "013": "조회된 데이터가 없습니다",
    "014": "파일이 존재하지 않습니다",
    "020": "요청 제한을 초과했습니다 (잠시 뒤 다시)",
    "021": "조회 가능한 회사 개수를 초과했습니다",
    "100": "필드의 부적절한 값입니다",
    "101": "부적절한 접근입니다",
    "800": "시스템 점검 중입니다",
    "900": "정의되지 않은 오류입니다",
    "901": "개인정보 보유기간이 지나 인증키를 쓸 수 없습니다 (OpenDART에서 다시 동의)",
}


class DartError(Exception):
    pass


def api_key():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
        load_dotenv()
    except Exception:
        pass
    key = (os.getenv("OPENDART_API_KEY") or "").strip()
    if not key:
        raise DartError("OPENDART_API_KEY가 없습니다. engine/.env에 OPENDART_API_KEY=인증키 한 줄을 적거나, "
                        "GitHub 자동 실행이면 저장소 Settings > Secrets and variables > Actions에 등록하세요.")
    return key


def _get(path, params, key, timeout=90, tries=3):
    """GET 요청. 실패하면 2번 더 시도합니다. 오류 메시지에 주소(인증키 포함)를 넣지 않습니다."""
    query = urllib.parse.urlencode({"crtfc_key": key, **params})
    req = urllib.request.Request(f"{API}/{path}?{query}", headers={"User-Agent": UA})
    last = None
    for n in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code < 500 and e.code != 429:
                break
        except Exception as e:  # 연결 끊김, 시간 초과
            last = type(e).__name__
        time.sleep(2 + 3 * n)
    raise DartError(f"OpenDART {path} 요청 실패 ({last})")


def _status_error(path, status, message):
    hint = STATUS_HINT.get(status, "")
    extra = f" ({hint})" if hint and hint not in (message or "") else ""
    return DartError(f"OpenDART {path} 상태 {status}: {message or ''}{extra}")


# ---------- 1. 기업 고유번호 ----------

def parse_corp_codes(zip_bytes):
    """corpCode.xml(ZIP)을 [{corp_code, corp_name, stock_code, modify_date}]로 읽습니다."""
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    name = next((n for n in z.namelist() if n.lower().endswith(".xml")), None)
    if not name:
        raise DartError("기업 목록 ZIP에 XML이 없습니다")
    out = []
    for _, el in ET.iterparse(io.BytesIO(z.read(name))):
        if el.tag != "list":
            continue
        row = {k: (el.findtext(k) or "").strip() for k in ("corp_code", "corp_name", "stock_code", "modify_date")}
        out.append(row)
        el.clear()
    return out


def load_corp_codes(key, cache_dir):
    """기업 목록은 하루에 한 번만 받아 cache_dir/_corpcode.zip에 둡니다."""
    path = os.path.join(cache_dir, "_corpcode.zip")
    fresh = os.path.exists(path) and (time.time() - os.path.getmtime(path)) < 20 * 3600
    if fresh:
        with open(path, "rb") as f:
            data = f.read()
    else:
        data = _get("corpCode.xml", {}, key, timeout=180)
        if data[:2] != b"PK":
            raise _status_error("corpCode.xml", *_xml_status(data))
        os.makedirs(cache_dir, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
    return parse_corp_codes(data)


def match_corps(corps, name, stock_code=None):
    """종목코드가 있으면 종목코드로, 없으면 정확히 같은 이름으로 찾습니다 (비슷한 이름은 쓰지 않음)."""
    if stock_code:
        return [c for c in corps if c["stock_code"] == stock_code]
    return [c for c in corps if c["corp_name"] == name]


# ---------- 2. 보고서 고르기 ----------

def report_target(report_key):
    """보고서 키 → (보고서 종류, 기간). y2024 → ('사업보고서', '2024.12'), h2026 → ('반기보고서', '2026.06')."""
    m = re.fullmatch(r"y(\d{4})", report_key or "")
    if m:
        return "사업보고서", f"{m.group(1)}.12"
    m = re.fullmatch(r"h(\d{4})", report_key or "")
    if m:
        return "반기보고서", f"{m.group(1)}.06"
    return None


def search_window(report_key, today=None):
    """그 보고서를 낼 만한 기간: 사업보고서는 다음 해 1월 1일부터, 반기보고서는 그해 7월 1일부터 오늘까지."""
    kind, period = report_target(report_key)
    year = int(period[:4])
    start = datetime.date(year + 1, 1, 1) if kind == "사업보고서" else datetime.date(year, 7, 1)
    end = today or datetime.date.today()
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def list_filings(key, corp_code, bgn_de, end_de):
    """정기공시(A) 목록. 정정 전 보고서까지 모두 받습니다 (last_reprt_at=N)."""
    out, page = [], 1
    while True:
        raw = _get("list.json", {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de, "pblntf_ty": "A",
                                 "last_reprt_at": "N", "page_no": page, "page_count": 100}, key)
        data = json.loads(raw.decode("utf-8"))
        status = data.get("status")
        if status == "013":
            break
        if status != "000":
            raise _status_error("list.json", status, data.get("message"))
        out.extend(data.get("list") or [])
        if page >= int(data.get("total_page") or 1):
            break
        page += 1
    return out


def pick_report(filings, report_key):
    """목록에서 보고서 키에 맞는 보고서 1건. 없으면 None."""
    target = report_target(report_key)
    if not target:
        return None
    want = f"{target[0]}({target[1]})"
    cands = []
    for f in filings:
        m = re.match(r"^\s*(?:\[([^\]]*)\])?\s*(.+)$", f.get("report_nm") or "")
        if not m:
            continue
        prefix, base = (m.group(1) or ""), re.sub(r"\s+", "", m.group(2))
        if base == want:
            cands.append((prefix, f))
    if not cands:
        return None
    body = [c for c in cands if "첨부" not in c[0]] or cands
    return max(body, key=lambda c: c[1].get("rcept_no", ""))[1]


# ---------- 3. 원문 받기, 글로 바꾸기 ----------

def _xml_status(data):
    """오류일 때 OpenDART가 ZIP 대신 보내는 XML/JSON에서 상태 코드와 메시지를 꺼냅니다."""
    text = data[:2000].decode("utf-8", "replace")
    st = re.search(r"<status>\s*(\d+)\s*</status>|\"status\"\s*:\s*\"(\d+)\"", text)
    msg = re.search(r"<message>\s*(.*?)\s*</message>|\"message\"\s*:\s*\"(.*?)\"", text, re.S)
    status = (st.group(1) or st.group(2)) if st else "?"
    message = ((msg.group(1) or msg.group(2)) if msg else "ZIP이 아닌 응답").strip()
    return status, message


def decode_xml(raw):
    """XML 선언의 인코딩을 따르고, 없거나 틀리면 utf-8, cp949 순서로 읽습니다."""
    head = raw[:300].decode("ascii", "ignore")
    m = re.search(r'encoding="([^"]+)"', head)
    tried = []
    for enc in ([m.group(1)] if m else []) + ["utf-8", "cp949"]:
        if enc.lower() in tried:
            continue
        tried.append(enc.lower())
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


def main_xml_name(names, rcept_no):
    """ZIP 안의 본문 XML: 접수번호.xml이 본문이고, 접수번호_00760.xml 같은 것은 첨부(감사보고서 등)입니다."""
    xmls = [n for n in names if n.lower().endswith(".xml")]
    exact = [n for n in xmls if os.path.basename(n) == f"{rcept_no}.xml"]
    return exact[0] if exact else None


def download_document(key, rcept_no):
    data = _get("document.xml", {"rcept_no": rcept_no}, key, timeout=300)
    if data[:2] != b"PK":
        raise _status_error("document.xml", *_xml_status(data))
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    name = main_xml_name(names, rcept_no)
    if not name:  # 이름 규칙이 다르면 가장 큰 XML을 본문으로 봅니다
        xmls = [n for n in names if n.lower().endswith(".xml")]
        if not xmls:
            raise DartError(f"{rcept_no}: ZIP 안에 XML이 없습니다 ({names[:5]})")
        name = max(xmls, key=lambda n: z.getinfo(n).file_size)
    return decode_xml(z.read(name)), name, names


_DROP = re.compile(r"<(SUMMARY|TOC|IMAGE|IMG|EXTRACTION)\b.*?</\1\s*>", re.S | re.I)
_BLOCK_END = re.compile(r"</\s*(P|TITLE|TR|TABLE|TABLE-GROUP|SECTION-\d|COVER-TITLE|LIBRARY|PART|LI|CORRECTION)\s*>"
                        r"|<\s*BR\s*/?>|<\s*PGBRK\b[^>]*>", re.I)
_CELL_END = re.compile(r"</\s*(TD|TH|TE|TU)\s*>", re.I)


def xml_to_text(xml):
    """DART 공시 XML → 글. 큰 장(SECTION-1, 표지, 첨부 묶음)마다 \\f로 쪽을 나누고, 장 제목은 한 줄로 둡니다."""
    x = re.sub(r"<\?xml[^>]*\?>", "", xml)
    x = re.sub(r"<!--.*?-->", "", x, flags=re.S)
    x = _DROP.sub("", x)
    x = re.sub(r"<\s*(SECTION-1|COVER|LIBRARY)\b", "\f<\\1", x, flags=re.I)
    x = re.sub(r"<\s*TITLE\b[^>]*>", "\n", x, flags=re.I)
    x = _BLOCK_END.sub("\n", x)
    x = _CELL_END.sub(" ", x)
    x = re.sub(r"<[^>]+>", "", x)
    x = x.replace("&cr;", "\n")
    x = html.unescape(x)
    pages = []
    for page in x.split("\f"):
        lines = [re.sub(r"[ \t 　]+", " ", ln).strip() for ln in page.splitlines()]
        text = "\n".join(ln for ln in lines if ln)
        if text:
            pages.append(text)
    return "\f".join(pages)


# ---------- 4. 기업 1곳 받기 ----------

def fetch_company(key, company, out_dir, corps_loader, log=print, today=None):
    """기업 1곳의 보고서를 모두 받아 .txt로 저장하고 manifest 항목을 돌려줍니다.
    corps_loader: 기업 목록이 필요할 때만 부르는 함수 (config에 corp_code가 있으면 부르지 않음)."""
    from .collect import locate_sections, SECTIONS
    from .textutil import clean_page_text

    reports = list(company.get("promise_reports") or []) + list(company.get("evidence_reports") or [])
    targets = [r for r in reports if report_target(r.get("key"))]
    if not targets:
        raise DartError(f"{company['name']}: 보고서 키(y2024, h2026 같은 이름)가 없어 찾을 수 없습니다")

    # 1) 고유번호
    if company.get("corp_code"):
        corp = {"corp_code": str(company["corp_code"]), "corp_name": company["name"],
                "stock_code": str(company.get("stock_code") or ""), "how": "config"}
    else:
        found = match_corps(corps_loader(), company["name"], company.get("stock_code"))
        how = "종목코드" if company.get("stock_code") else "정확히 같은 이름"
        if len(found) > 1:  # 이름이 같은 법인이 여럿: 필요한 보고서를 낸 법인만 남김
            keep = []
            for c in found:
                bgn, end = search_window(targets[0]["key"], today)
                if pick_report(list_filings(key, c["corp_code"], bgn, end), targets[0]["key"]):
                    keep.append(c)
            found = keep
            how += ", 보고서 낸 법인"
        if len(found) != 1:
            names = ", ".join(f"{c['corp_name']}({c['corp_code']}, 종목 {c['stock_code'] or '없음'})" for c in found) or "없음"
            raise DartError(f"{company['name']}: 고유번호를 하나로 정하지 못했습니다 (찾은 법인: {names}). "
                            "config.yaml에 corp_code를 적어 주세요.")
        corp = dict(found[0], how=how)
    log(f"  고유번호 {corp['corp_code']} ({corp['corp_name']}, 종목 {corp['stock_code'] or '없음'}, 찾은 방법: {corp['how']})")

    # 2) 목록 한 번에 받기 (가장 이른 보고서의 시작일부터 오늘까지)
    windows = [search_window(r["key"], today) for r in targets]
    filings = list_filings(key, corp["corp_code"], min(w[0] for w in windows), max(w[1] for w in windows))
    log(f"  정기공시 {len(filings)}건 확인")

    entry = {"corp_code": corp["corp_code"], "corp_name": corp["corp_name"], "stock_code": corp["stock_code"],
             "corp_found_by": corp["how"], "reports": {}}
    os.makedirs(out_dir, exist_ok=True)
    for r in targets:
        f = pick_report(filings, r["key"])
        kind, period = report_target(r["key"])
        if not f:
            log(f"  {r['title']}: '{kind} ({period})'를 목록에서 찾지 못했습니다")
            entry["reports"][r["key"]] = {"title": r["title"], "found": False, "want": f"{kind} ({period})"}
            continue
        xml, member, members = download_document(key, f["rcept_no"])
        text = xml_to_text(xml)
        fname = f"{company['key']}_{r['key']}.txt"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as g:
            g.write(text)
        pages = [clean_page_text(p) for p in text.split("\f")]
        loc = locate_sections(pages, ["I5", "II", "IV"])
        sections = {k: bool(loc.get(k)) for k in ("I5", "II", "IV")}
        entry["reports"][r["key"]] = {
            "title": r["title"], "found": True, "report_nm": f["report_nm"].strip(), "rcept_no": f["rcept_no"],
            "rcept_dt": f.get("rcept_dt", ""), "url": VIEWER.format(f["rcept_no"]), "file": fname,
            "xml_member": os.path.basename(member), "zip_members": len(members), "chars": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], "sections_found": sections,
        }
        found_txt = ", ".join(f"{SECTIONS[k]['name'].split(' > ')[-1]} {'OK' if ok else '없음'}" for k, ok in sections.items())
        log(f"  {r['title']}: {f['report_nm'].strip()} 접수 {f['rcept_no']} ({f.get('rcept_dt', '')}), "
            f"글자 {len(text):,}, 장 찾기 [{found_txt}]")
        time.sleep(0.5)  # 요청 간격 (요청 제한 배려)
    return entry


def manifest_path(cfg):
    return os.path.join(dart_dir(cfg), "manifest.json")


def dart_dir(cfg):
    d = cfg["paths"].get("dart_dir")
    return d or os.path.join(os.path.dirname(cfg["paths"]["pdf_dir"]), "dart")


def load_manifest(cfg):
    path = manifest_path(cfg)
    if not os.path.exists(path):
        return {"companies": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_manifest(cfg, manifest):
    path = manifest_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    manifest["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    return path


def apply_manifest(cfg, company):
    """받아 둔 DART 글이 있으면 보고서마다 text(파일 이름), url(비어 있을 때만), no_pages를 채웁니다.
    company_cfg가 부르므로 collect, doctor, export가 모두 같은 원문 주소를 씁니다."""
    entry = (load_manifest(cfg).get("companies") or {}).get(company["key"])
    if not entry:
        return company
    base = dart_dir(cfg)
    for group in ("promise_reports", "evidence_reports"):
        new = []
        for r in company.get(group) or []:
            r = dict(r)
            got = (entry.get("reports") or {}).get(r.get("key")) or {}
            if got.get("found"):
                # 원문 주소는 글 파일이 없어도(저장소에는 글을 올리지 않음) 접수번호로 채웁니다 (export에 필요)
                if not r.get("url"):
                    r["url"] = got.get("url", "")
                if got.get("file") and os.path.exists(os.path.join(base, got["file"])):
                    r["text"] = got["file"]
                    r["no_pages"] = True
            new.append(r)
        company[group] = new
    return company
