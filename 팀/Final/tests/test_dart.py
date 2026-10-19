"""OpenDART 자동 수집 시험 (인터넷, 인증키, API 키 없이 몇 초)

  python tests/test_dart.py   (마지막 줄 "DART 자동 수집 시험 통과")

1. 보고서 고르기: 사업보고서/반기보고서 이름과 기간, 정정 보고서(가장 늦은 본문 정정), 첨부만 고친 정정은 뒤로
2. 기업 찾기: 종목코드, 정확히 같은 이름, 이름이 같은 법인이 여럿이면 보고서를 낸 법인만
3. DART XML → 글: 장 제목은 한 줄, 큰 장마다 쪽 구분, 표·특수문자(&amp;, &cr;) 처리, 요약(SUMMARY)과 표지 목차는 본문과 섞이지 않음
4. 가짜 OpenDART 응답으로 fetch_company 전체: .txt와 manifest, 장 찾기, DART 원문 주소
5. 오류 메시지에 인증키가 찍히지 않음
6. 받은 글로 엔진 1~7단계(가짜 모델) → 쪽 번호 없음, 원문 링크는 DART 주소, 결과 파일과 화면 미리 보기까지
보고서 글은 모두 가상 회사의 지어낸 문장입니다.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine")
TMP = os.path.join(ROOT, "tests", "tmp", "dart_case")
sys.path.insert(0, ENGINE)

from aipromise import dart  # noqa: E402
from aipromise.collect import locate_sections  # noqa: E402
from aipromise.textutil import clean_page_text  # noqa: E402

problems = []


def check(cond, msg):
    if not cond:
        problems.append(msg)


def dart_xml(sections, kind="사업보고서"):
    """DART 공시 XML과 비슷한 모양 (dart4.xsd의 주요 태그만)."""
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<DOCUMENT xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="dart4.xsd">',
           f'<DOCUMENT-NAME ACODE="11011">{kind}</DOCUMENT-NAME>',
           '<COMPANY-NAME AREGCIK="00999999">테스트전자</COMPANY-NAME>',
           '<SUMMARY><EXTRACTION ACODE="FSCC">II. 사업의 내용 요약에만 있는 글</EXTRACTION></SUMMARY>',
           '<BODY>',
           '<COVER><COVER-TITLE AUNIT="SUBMIT_DOC">사 업 보 고 서</COVER-TITLE><P>(제 9 기)</P></COVER>',
           # 표지 뒤 목차처럼 보이는 짧은 쪽: 본문 장으로 잘못 잡히면 안 됨
           '<P>목 차</P><P>I. 회사의 개요</P><P>II. 사업의 내용</P><P>III. 재무에 관한 사항</P><P>IV. 이사의 경영진단 및 분석의견</P>']
    for title, subs in sections:
        out.append(f'<SECTION-1 ACLASS="MANDATORY" APARTSOURCE="SOURCE"><TITLE ATOC="Y" AASSOCNOTE="D-0-1-0-0">{title}</TITLE>')
        for sub, paras in subs:
            if sub:
                out.append(f'<SECTION-2 ACLASS="MANDATORY"><TITLE ATOC="Y" AASSOCNOTE="D-0-1-1-0">{sub}</TITLE>')
            for p in paras:
                out.append(f'<P><SPAN USERMARK="F-14">{p}</SPAN></P>')
            if sub:
                out.append('</SECTION-2>')
        out.append('<PGBRK/></SECTION-1>')
    out += ['</BODY>', '</DOCUMENT>']
    return "\n".join(out)


TABLE = ('<TABLE-GROUP><TABLE><TBODY><TR><TD>구분</TD><TD>내용</TD></TR>'
         '<TR><TD>AI 투자</TD><TD>R&amp;D 센터 확대</TD></TR></TBODY></TABLE></TABLE-GROUP>')

Y2024 = dart_xml([
    ("I. 회사의 개요", [
        ("1. 회사의 개요", ["당사는 전자부품을 만드는 가상의 회사입니다."]),
        ("5. 정관에 관한 사항", ["당사는 정기주주총회에서 AI 학습용 데이터 판매업을 사업목적에 추가하였습니다.",
                              "신규 사업목적으로 추가한 AI 학습용 데이터 판매업을 2025년부터 추진할 계획입니다."])]),
    ("II. 사업의 내용", [
        ("1. 사업의 개요", ['<IMG USERMARK="F-1"/>그림 아래 설명 문장입니다.',   # 스스로 닫는 IMG: 다음 </IMG>까지 지우면 안 됨
                         "당사는 2025년 중 A공장 조립 라인에 AI 기반 외관 검사 시스템을&cr;도입할 계획입니다.",
                         "또한 2025년 상반기까지 고객센터에 생성형 AI 상담 서비스를 출시할 예정입니다.",
                         "AI 시장은 앞으로 크게 성장할 것으로 예상됩니다.",
                         "당사는 국내 물류센터 3곳에 AI 수요 예측 시스템을 2025년까지 적용할 계획입니다."]),
        ("6. 주요계약 및 연구개발활동", ["당사는 R&amp;D 조직과 함께 해외 법인 5곳에 사내 AI 번역 도구를 2025년 중 도입할 예정입니다.", TABLE])]),
    ("III. 재무에 관한 사항", [("1. 요약재무정보", ["매출액은 100억원입니다."])]),
    ("IV. 이사의 경영진단 및 분석의견", [(None, ['<IMAGE><IMG>chart01.jpg</IMG></IMAGE>',
                                          "AI를 활용하여 제조 경쟁력을 지속적으로 강화해 나가겠습니다.",
                                          "AI 전환을 전담하는 조직을 2025년에 신설할 계획입니다."])]),
    ("V. 회계감사인의 감사의견 등", [(None, ["감사의견은 적정입니다."])]),
])
Y2025 = dart_xml([
    ("I. 회사의 개요", [("5. 정관에 관한 사항", ["AI 학습용 데이터 판매업은 시장 여건 변화로 현재 추진하지 않고 있으며, 향후 1년 이내 추진 계획은 없습니다."])]),
    ("II. 사업의 내용", [(None, ["당기 중 A공장 조립 2개 라인에 AI 기반 외관 검사 시스템을 적용하였습니다.",
                               "2025년 4월 고객센터에 생성형 AI 상담 서비스를 출시하였습니다.",
                               "국내 물류센터 1곳에 AI 수요 예측 시스템을 시범 적용하였습니다."])]),
    ("III. 재무에 관한 사항", [(None, ["매출액은 110억원입니다."])]),
    ("IV. 이사의 경영진단 및 분석의견", [(None, ["2025년 1월 대표이사 직속 AI전환실을 신설하였습니다."])]),
    ("V. 회계감사인의 감사의견 등", [(None, ["감사의견은 적정입니다."])]),
])
H2026 = dart_xml([
    ("I. 회사의 개요", [("1. 회사의 개요", ["당사는 전자부품을 만드는 가상의 회사입니다."])]),
    ("II. 사업의 내용", [(None, ["당사는 AI 외관 검사 라인을 추가로 넓히고 있습니다."])]),
    ("III. 재무에 관한 사항", [(None, ["반기 매출액은 60억원입니다."])]),
    ("IV. 이사의 경영진단 및 분석의견", [(None, ["반기보고서에는 기재하지 않습니다."])]),
    ("V. 회계감사인의 감사의견 등", [(None, ["검토의견은 적정입니다."])]),
], kind="반기보고서")

FILINGS = [
    {"report_nm": "사업보고서 (2024.12)", "rcept_no": "20250310000001", "rcept_dt": "20250310"},
    {"report_nm": "[기재정정]사업보고서 (2024.12)", "rcept_no": "20250402000002", "rcept_dt": "20250402"},
    {"report_nm": "[첨부정정]사업보고서 (2024.12)", "rcept_no": "20250520000003", "rcept_dt": "20250520"},
    {"report_nm": "분기보고서 (2025.03)", "rcept_no": "20250515000009", "rcept_dt": "20250515"},
    {"report_nm": "반기보고서 (2025.06)", "rcept_no": "20250814000008", "rcept_dt": "20250814"},
    {"report_nm": "사업보고서 (2025.12)", "rcept_no": "20260312000004", "rcept_dt": "20260312"},
    {"report_nm": "반기보고서 (2026.06)", "rcept_no": "20260814000005", "rcept_dt": "20260814"},
]
DOCS = {"20250402000002": Y2024, "20260312000004": Y2025, "20260814000005": H2026}


def zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(name, text.encode("utf-8"))
    return buf.getvalue()


CORPS = """<?xml version="1.0" encoding="UTF-8"?><result>
<list><corp_code>00999999</corp_code><corp_name>테스트전자</corp_name><corp_eng_name>TEST</corp_eng_name><stock_code>999990</stock_code><modify_date>20260101</modify_date></list>
<list><corp_code>00888881</corp_code><corp_name>중복은행</corp_name><corp_eng_name>DUP</corp_eng_name><stock_code> </stock_code><modify_date>20100101</modify_date></list>
<list><corp_code>00888882</corp_code><corp_name>중복은행</corp_name><corp_eng_name>DUP</corp_eng_name><stock_code> </stock_code><modify_date>20260101</modify_date></list>
<list><corp_code>00777777</corp_code><corp_name>신한지주</corp_name><corp_eng_name>SFG</corp_eng_name><stock_code>055550</stock_code><modify_date>20260101</modify_date></list>
</result>"""

calls = []


def fake_get(path, params, key, timeout=90, tries=3):
    calls.append((path, dict(params)))
    if path == "corpCode.xml":
        return zip_bytes({"CORPCODE.xml": CORPS})
    if path == "list.json":
        if params.get("corp_code") == "00888881":   # 이름만 같은 옛 법인: 정기공시 없음
            return json.dumps({"status": "013", "message": "조회된 데이타가 없습니다."}).encode("utf-8")
        return json.dumps({"status": "000", "message": "정상", "page_no": 1, "total_page": 1,
                           "list": FILINGS}, ensure_ascii=False).encode("utf-8")
    if path == "document.xml":
        no = params["rcept_no"]
        if no not in DOCS:
            return '<?xml version="1.0" encoding="UTF-8"?><result><status>014</status><message>파일이 존재하지 않습니다.</message></result>'.encode("utf-8")
        # 첨부(감사보고서)가 본문보다 커도 본문(접수번호.xml)을 골라야 함
        return zip_bytes({f"{no}.xml": DOCS[no], f"{no}_00760.xml": "<DOCUMENT>" + "감사보고서 " * 20000 + "</DOCUMENT>"})
    raise AssertionError(path)


def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP)

    # 1) 보고서 고르기
    check(dart.report_target("y2024") == ("사업보고서", "2024.12"), "y2024 → 사업보고서 (2024.12)")
    check(dart.report_target("h2026") == ("반기보고서", "2026.06"), "h2026 → 반기보고서 (2026.06)")
    check(dart.report_target("x1") is None, "알 수 없는 키는 None")
    check(dart.pick_report(FILINGS, "y2024")["rcept_no"] == "20250402000002", "정정 보고서 중 본문 정정(가장 늦은 것)을 골라야 함")
    check(dart.pick_report(FILINGS, "y2025")["rcept_no"] == "20260312000004", "2025 사업보고서")
    check(dart.pick_report(FILINGS, "h2026")["rcept_no"] == "20260814000005", "2026 반기보고서")
    check(dart.pick_report(FILINGS[:3][2:], "y2024")["rcept_no"] == "20250520000003", "첨부정정만 있으면 그것이라도")
    check(dart.pick_report(FILINGS, "y2023") is None, "없는 보고서는 None")
    import datetime
    check(dart.search_window("y2024", datetime.date(2026, 10, 19)) == ("20250101", "20261019"), "사업보고서 검색 기간")
    check(dart.search_window("h2026", datetime.date(2026, 10, 19)) == ("20260701", "20261019"), "반기보고서 검색 기간")

    # 2) 기업 찾기
    corps = dart.parse_corp_codes(zip_bytes({"CORPCODE.xml": CORPS}))
    check(len(corps) == 4 and corps[0]["stock_code"] == "999990", f"기업 목록 읽기: {corps[:1]}")
    check([c["corp_code"] for c in dart.match_corps(corps, "아무이름", "055550")] == ["00777777"], "종목코드로 찾기")
    check([c["corp_code"] for c in dart.match_corps(corps, "신한")] == [], "비슷한 이름은 쓰지 않음")
    check(len(dart.match_corps(corps, "중복은행")) == 2, "정확히 같은 이름 2곳")

    # 3) XML → 글
    text = dart.xml_to_text(Y2024)
    pages = [clean_page_text(p) for p in text.split("\f")]
    check("<" not in text and "&amp;" not in text and "&cr;" not in text, "태그와 특수문자가 남음")
    check("R&D" in text and "요약에만 있는 글" not in text, "&amp; 처리, SUMMARY 제외")
    check("그림 아래 설명 문장입니다." in text and "외관 검사" in text and "6. 주요계약 및 연구개발활동" in text,
          "스스로 닫는 IMG 뒤의 본문이 지워짐 (10/19 카카오 반기보고서 문제)")
    check(any(ln == "II. 사업의 내용" for ln in text.splitlines()), "장 제목이 한 줄로 있어야 함")
    # 쪽: 문서 이름(표지 앞) 1 + 표지와 목차 1 + 큰 장 5 = 7
    check(len(pages) == 7, f"문서 이름 1쪽 + 표지(목차) 1쪽 + 큰 장 5쪽이어야 함: {len(pages)}")
    toc_page = next(i for i, pg in enumerate(pages) if "목 차" in pg)
    loc = locate_sections(pages, ["I5", "II", "IV"])
    check(all(loc.get(k) for k in ("I5", "II", "IV")), f"장 찾기 실패: {loc}")
    check(loc["II"]["start"][0] != toc_page and "외관 검사" in pages[loc["II"]["start"][0]],
          f"II장이 목차 쪽이 아니라 본문 쪽에서 시작해야 함: {loc['II']}, 목차 쪽 {toc_page}")
    check(dart.decode_xml('<?xml version="1.0" encoding="euc-kr"?><A>가</A>'.encode("cp949")).endswith("<A>가</A>"), "euc-kr XML 읽기")
    check(dart.main_xml_name(["1.xml", "20250402000002_00760.xml", "20250402000002.xml"], "20250402000002") == "20250402000002.xml", "본문 XML 고르기")

    # 4) 가짜 OpenDART로 기업 1곳 전체
    real_get, real_sleep = dart._get, dart.time.sleep
    dart._get, dart.time.sleep = fake_get, (lambda s: None)
    try:
        comp = {"key": "demo_dart", "name": "테스트전자", "stock_code": "999990",
                "promise_reports": [{"key": "y2024", "title": "2024 사업보고서", "pdf": "x.pdf"}],
                "evidence_reports": [{"key": "y2025", "title": "2025 사업보고서", "pdf": "y.pdf"},
                                     {"key": "h2026", "title": "2026 반기보고서", "pdf": "z.pdf"}]}
        logs = []
        entry = dart.fetch_company("TESTKEY", comp, os.path.join(TMP, "dart"),
                                   lambda: dart.parse_corp_codes(fake_get("corpCode.xml", {}, "k")), log=logs.append)
        reps = entry["reports"]
        check(entry["corp_code"] == "00999999", f"고유번호: {entry['corp_code']}")
        check(all(reps[k]["found"] for k in ("y2024", "y2025", "h2026")), f"보고서 3개 모두 찾아야 함: {reps}")
        check(reps["y2024"]["url"] == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20250402000002", reps["y2024"].get("url"))
        check(reps["y2024"]["xml_member"] == "20250402000002.xml", "첨부가 아닌 본문 XML을 읽어야 함")
        check(reps["y2024"]["sections_found"] == {"I5": True, "II": True, "IV": True}, reps["y2024"]["sections_found"])
        check(reps["y2024"]["section_chars"]["II"] > 150 and reps["y2024"]["xml_tags"]["SECTION-1"] == 5,
              f"장 글자 수, XML 태그 수 기록: {reps['y2024'].get('section_chars')} {reps['y2024'].get('xml_tags')}")
        check(any("너무 짧습니다" in ln for ln in logs), "짧은 II장 경고가 기록에 있어야 함 (가상 회사 II장은 짧음)")
        check(reps["h2026"]["sections_found"]["I5"] is False, "반기보고서에는 정관 장이 없음")
        check(os.path.exists(os.path.join(TMP, "dart", "demo_dart_y2024.txt")), "글 파일이 없음")
        lists = [c for c in calls if c[0] == "list.json"]
        check(len(lists) == 1 and lists[0][1]["bgn_de"] == "20250101", f"목록은 한 번에, 가장 이른 시작일부터: {lists}")
        check(lists[0][1]["last_reprt_at"] == "N" and lists[0][1]["pblntf_ty"] == "A", "정정 전 보고서까지, 정기공시만")
        # 이름이 같은 법인이 여럿이면 보고서를 낸 법인만
        dup = dict(comp, key="dup", name="중복은행", stock_code=None)
        e2 = dart.fetch_company("TESTKEY", dup, os.path.join(TMP, "dart"),
                                lambda: dart.parse_corp_codes(fake_get("corpCode.xml", {}, "k")), log=logs.append)
        check(e2["corp_code"] == "00888882", f"보고서를 낸 법인을 골라야 함: {e2['corp_code']}")
        # 없는 접수번호: ZIP 대신 오류 XML → 상태 코드가 든 오류
        try:
            dart.download_document("TESTKEY", "20990101000000")
            check(False, "없는 문서인데 오류가 나지 않음")
        except dart.DartError as e:
            check("014" in str(e), f"오류 상태 코드가 없음: {e}")
    finally:
        dart._get, dart.time.sleep = real_get, real_sleep

    # 5) 인증키가 오류 메시지에 찍히지 않음
    real_open = dart.urllib.request.urlopen

    def boom(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 500, "server error", {}, None)
    dart.urllib.request.urlopen, dart.time.sleep = boom, (lambda s: None)
    try:
        dart._get("list.json", {"corp_code": "1"}, "SECRETKEY_SHOULD_NOT_PRINT", tries=2)
        check(False, "실패해야 함")
    except dart.DartError as e:
        check("SECRETKEY" not in str(e) and "HTTP 500" in str(e), f"오류 메시지: {e}")
    finally:
        dart.urllib.request.urlopen, dart.time.sleep = real_open, real_sleep

    # 6) 받은 글로 엔진 1~7단계 (가짜 모델)
    manifest = {"companies": {"demo_dart": entry}}
    with open(os.path.join(TMP, "dart", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
    cfg_path = os.path.join(TMP, "config.yaml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write("""
llm: {extract_model: mock, judge_model: mock, card_model: mock, embed_model: mock, temperature: 0}
paths:
  pdf_dir: ../tests/tmp/dart_case/pdf
  dart_dir: ../tests/tmp/dart_case/dart
  work_dir: ../tests/tmp/dart_case/work
  results_file: ../tests/tmp/dart_case/results/ai_promise_data.json
  labels_file: labels.json
  eval_dir: ../tests/tmp/dart_case/eval
sections: [I5, II, IV]
keywords: [AI, 인공지능, 머신러닝, 딥러닝, "생성형 AI", 생성형AI]
retrieval: {use_vector: false, top_windows: 8, max_candidates: 24, max_attempts: 3}
companies: {}
candidates:
  demo_dart:
    name: 테스트전자 (가상 회사)
    stock_code: "999990"
    check_note: "AI 엔진 결과예요(사람 검토 전)."
    promise_reports:
      - {key: y2024, title: "2024 사업보고서", pdf: none_2024.pdf, url: ""}
    evidence_reports:
      - {key: y2025, title: "2025 사업보고서", pdf: none_2025.pdf, url: ""}
      - {key: h2026, title: "2026 반기보고서", pdf: none_2026h1.pdf, url: ""}
section_pages: {}
""")
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "analyze_companies.py"), "demo_dart", "--skip-fetch", "--mock",
                        "--config", cfg_path], capture_output=True, text=True, cwd=ENGINE)
    out = r.stdout
    check(r.returncode == 0, f"analyze_companies 실패 ({r.returncode}): {out[-1500:]} {r.stderr[-1500:]}")
    check("[기업별 결과]" in out and "DART 자동 수집" in out and "[화면 데이터 미리 보기]" in out, out[-1500:])
    work = os.path.join(TMP, "work", "demo_dart")
    col = json.load(open(os.path.join(work, "collected_y2024.json"), encoding="utf-8"))
    check(col["source"] == "dart" and col["source_file"] == "demo_dart_y2024.txt", "DART 글을 읽어야 함")
    sents = [s for sec in col["sections"].values() for s in sec["sentences"]]
    check(sents and all(s["page"] is None for s in sents), "DART 글은 쪽 번호가 없어야 함")
    check(any("A공장 조립 라인에 AI 기반 외관 검사 시스템을 도입할 계획입니다" in s["text"] for s in sents), "&cr;로 나뉜 문장이 이어져야 함")
    judged = json.load(open(os.path.join(work, "judged.json"), encoding="utf-8"))["promises"]
    spec = [p for p in judged if p["type"] == "specific"]
    check(len(spec) >= 4, f"구체적 약속이 모자람: {len(spec)}")
    check(all(p["source"]["url"].startswith("https://dart.fss.or.kr/dsaf001/main.do?rcpNo=2025") for p in judged), "약속 원문 링크")
    evs = [e for p in judged for e in p.get("evidence", [])]
    check(evs and all(e["citation_verified"] for e in evs), "인용 검사 통과 근거가 있어야 함")
    check(all(e["source"]["url"].startswith("https://dart.fss.or.kr/dsaf001/main.do?rcpNo=2026") for e in evs), "근거 원문 링크")
    res = json.load(open(os.path.join(TMP, "results", "ai_promise_data.json"), encoding="utf-8"))
    c0 = res["companies"][0]
    check(c0["data_mode"] == "engine" and c0["reports"]["promise"][0]["url"].endswith("20250402000002"), "결과 파일의 보고서 링크")
    check(all(p["source"].get("page") is None for p in c0["promises"]), "결과 파일에 쪽 번호가 없어야 함")

    if problems:
        print("DART 자동 수집 시험 실패:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("DART 자동 수집 시험 통과")


if __name__ == "__main__":
    main()
