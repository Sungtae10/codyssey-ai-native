"""가짜 모델(--mock)과 가상 회사 보고서로 1~7단계, 내보내기, 화면 점검, 평가가 끝까지 도는지 시험합니다.

  python tests/test_mock.py

인터넷과 API 키가 필요 없습니다. 보고서 글은 모두 가상 회사의 지어낸 문장입니다.
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, "tests", "tmp")
ENGINE = os.path.join(ROOT, "engine")

TOC = "목 차\nI. 회사의 개요\n1. 회사의 개요\n5. 정관에 관한 사항\nII. 사업의 내용\nIII. 재무에 관한 사항\nIV. 이사의 경영진단 및 분석의견\nV. 회계감사인의 감사의견 등"

R2024 = [
    TOC,
    "I. 회사의 개요\n1. 회사의 개요\n당사는 전자부품을 만드는 가상의 회사입니다.\n5. 정관에 관한 사항\n"
    "당사는 정기주주총회에서 AI 학습용 데이터 판매업을 사업목적에 추가하였습니다.\n"
    "신규 사업목적으로 추가한 AI 학습용 데이터 판매업을 2025년부터 추진할 계획입니다.",
    "II. 사업의 내용\n1. 사업의 개요\n당사는 2025년 중 A공장 조립 라인에 AI 기반 외관 검사 시스템을\n도입할 계획입니다.\n"
    "또한 2025년 상반기까지 고객센터에 생성형 AI 상담 서비스를 출시할 예정입니다.\n"
    "AI 시장은 앞으로 크게 성장할 것으로 예상됩니다.\n"
    "당사는 국내 물류센터 3곳에 AI 수요 예측 시스템을 2025년까지 적용할 계획입니다.",
    "6. 주요계약 및 연구개발활동\n당사는 해외 법인 5곳에 사내 AI 번역 도구를 2025년 중 도입할 예정입니다.\n"
    "III. 재무에 관한 사항\n1. 요약재무정보\n매출액은 100억원입니다.",
    "IV. 이사의 경영진단 및 분석의견\nAI를 활용하여 제조 경쟁력을 지속적으로 강화해 나가겠습니다.\n"
    "AI 전환을 전담하는 조직을 2025년에 신설할 계획입니다.\nV. 회계감사인의 감사의견 등\n감사의견은 적정입니다.",
]
R2025 = [
    TOC,
    "I. 회사의 개요\n5. 정관에 관한 사항\nAI 학습용 데이터 판매업은 시장 여건 변화로 현재 추진하지 않고 있으며, 향후 1년 이내 추진 계획은 없습니다.",
    "II. 사업의 내용\n당기 중 A공장 조립 2개 라인에 AI 기반 외관 검사 시스템을 적용하였습니다.\n"
    "2025년 4월 고객센터에 생성형 AI 상담 서비스를 출시하였습니다.\n"
    "국내 물류센터 1곳에 AI 수요 예측 시스템을 시범 적용하였습니다.\nIII. 재무에 관한 사항\n매출액은 110억원입니다.",
    "IV. 이사의 경영진단 및 분석의견\n2025년 1월 대표이사 직속 AI전환실을 신설하였습니다.\nV. 회계감사인의 감사의견 등\n감사의견은 적정입니다.",
]
R2026 = [
    TOC,
    "II. 사업의 내용\n당사는 AI 외관 검사 라인을 추가로 넓히고 있습니다.\nIII. 재무에 관한 사항\n반기 매출액은 60억원입니다.",
    "IV. 이사의 경영진단 및 분석의견\n반기보고서에는 기재하지 않습니다.\nV. 회계감사인의 감사의견 등\n검토의견은 적정입니다.",
]

CONFIG = """
llm: {extract_model: mock, judge_model: mock, card_model: mock, embed_model: mock, temperature: 0}
paths:
  pdf_dir: ../tests/tmp/pdf
  work_dir: ../tests/tmp/work
  results_file: ../tests/tmp/results/ai_promise_data.json
  labels_file: labels.json
  eval_dir: ../tests/tmp/eval
sections: [I5, II, IV]
keywords: [AI, 인공지능, 머신러닝, 딥러닝, 생성형, 자동화, 지능형]
retrieval: {use_vector: false, top_windows: 8, max_candidates: 24, max_attempts: 3}
companies:
  demo:
    name: 테스트전자 (가상 회사)
    check_note: "시험용 검증 안내 문구"
    promise_reports:
      - {key: y2024, title: "2024 사업보고서", pdf: demo_2024.txt, url: "https://example.com/demo/2024"}
    evidence_reports:
      - {key: y2025, title: "2025 사업보고서", pdf: demo_2025.txt, url: "https://example.com/demo/2025"}
      - {key: h2026, title: "2026 반기보고서", pdf: demo_2026h1.txt, url: "https://example.com/demo/2026h1"}
candidates:
  demo_scan:
    name: 후보전자 (가상 회사)
    promise_reports:
      - {key: y2024, title: "2024 사업보고서", pdf: demo_2024.txt, url: ""}
    evidence_reports:
      - {key: y2025, title: "2025 사업보고서", pdf: no_such_2025.txt, url: ""}
  junk:
    name: 깨진글자 (가상 회사)
    promise_reports:
      - {key: y2024, title: "2024 사업보고서", pdf: junk_2024.txt, url: ""}
    evidence_reports: []
section_pages: {}
"""


def run(*args):
    cmd = [sys.executable, os.path.join(ENGINE, "run.py"), *args, "--config", os.path.join(TMP, "config.yaml")]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ENGINE)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit(f"실패: {' '.join(args)}")
    return r.stdout


def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(os.path.join(TMP, "pdf"))
    for name, pages in (("demo_2024.txt", R2024), ("demo_2025.txt", R2025), ("demo_2026h1.txt", R2026)):
        with open(os.path.join(TMP, "pdf", name), "w", encoding="utf-8") as f:
            f.write("\f".join(pages))
    cfg = CONFIG
    with open(os.path.join(TMP, "config.yaml"), "w", encoding="utf-8") as f:
        f.write(cfg)
    # config.yaml의 상대 경로는 engine 폴더 기준이므로, 시험용 설정 파일도 engine 기준 경로를 씁니다.
    # 시작 전 점검: 키가 없는 환경이라 "고칠 것"이 나와도 되고, PDF 3개는 OK여야 합니다.
    cmd = [sys.executable, os.path.join(ENGINE, "run.py"), "doctor", "--company", "demo", "--no-api",
           "--config", os.path.join(TMP, "config.yaml")]
    d = subprocess.run(cmd, capture_output=True, text=True, cwd=ENGINE, env={**os.environ, "OPENAI_API_KEY": ""})
    print(d.stdout)
    assert "[시작 전 점검]" in d.stdout and d.stdout.count("쪽 OK") == 3, "doctor 점검 실패"
    # 장 찾기 미리 보기: 보고서 3개 모두 한 줄씩, 반기보고서에는 정관 장이 없어 (주의)가 나와야 함
    assert d.stdout.count("장 찾기:") == 3 and "II. 사업의 내용 OK" in d.stdout, "doctor 장 찾기 미리 보기 실패"
    assert "2026 반기보고서: I. 회사의 개요 > 5. 정관에 관한 사항 장을 제목으로 못 찾았습니다" in d.stdout, d.stdout
    # 글자가 깨져 읽히는 PDF(예: "(cid:123)"만 나오는 경우)는 doctor가 먼저 알려 줘야 함
    with open(os.path.join(TMP, "pdf", "junk_2024.txt"), "w", encoding="utf-8") as f:
        f.write("(cid:123)(cid:45) " * 60)
    cmd_j = [sys.executable, os.path.join(ENGINE, "run.py"), "doctor", "--company", "junk", "--no-api",
             "--config", os.path.join(TMP, "config.yaml")]
    dj = subprocess.run(cmd_j, capture_output=True, text=True, cwd=ENGINE, env={**os.environ, "OPENAI_API_KEY": ""})
    assert "글자가 깨져 보임" in dj.stdout and "글자가 깨져 읽힙니다" in dj.stdout, dj.stdout
    run("all", "--company", "demo", "--mock")
    exp = run("export")  # --companies 없이: companies만 내보내고 후보 기업(candidates)은 넣지 않아야 함
    assert "demo_scan" not in exp and "후보전자" not in exp, "후보 기업이 기본 내보내기에 들어감"
    out = run("check", "--file", os.path.join(TMP, "results", "ai_promise_data.json"))
    assert "문제 없음" in out or "(주의)" in out

    data = json.load(open(os.path.join(TMP, "results", "ai_promise_data.json"), encoding="utf-8"))
    assert [c["id"] for c in data["companies"]] == ["demo"], data["companies"]
    assert data["companies"][0].get("check_note") == "시험용 검증 안내 문구", "check_note가 결과 파일에 없음"
    sample = json.load(open(os.path.join(ROOT, "tests", "sample_data.json"), encoding="utf-8")) \
        if os.path.exists(os.path.join(ROOT, "tests", "sample_data.json")) else None
    if sample:
        assert set(data) == set(sample), "최상위 항목 이름이 예시 데이터와 다릅니다"
        assert set(data["companies"][0]) - {"check_note"} == set(sample["companies"][0]), "기업 항목 이름이 다릅니다"
        sp = sample["companies"][0]["promises"][0]
        dp = data["companies"][0]["promises"][0]
        assert set(sp) <= set(dp), f"약속 항목이 모자랍니다: {set(sp) - set(dp)}"

    # 가짜 정답으로 평가 스크립트 시험
    gold_src = os.path.join(TMP, "eval", "gold", "demo_정답매길목록.csv")
    rows = list(csv.DictReader(open(gold_src, encoding="utf-8-sig")))
    expected = {"AI 학습용 데이터": "회사가 미추진으로 공시", "외관 검사": "근거 확인", "상담 서비스": "근거 확인",
                "물류센터": "일부 확인", "번역 도구": "공시에서 확인 불가", "전담하는 조직": "근거 확인"}
    for who in ("합의", "김성태", "서원"):
        enc = "cp949" if who == "서원" else "utf-8-sig"  # 서원 파일: 엑셀에서 그냥 'CSV'(cp949)로 저장한 경우를 시험
        with open(os.path.join(TMP, "eval", "gold", f"demo_{who}.csv"), "w", encoding=enc, newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                r = dict(r)
                if r["분류"] == "구체적":
                    lab = next((v for k, v in expected.items() if k in r["약속 문장"]), "공시에서 확인 불가")
                    if who == "서원" and "물류센터" in r["약속 문장"]:
                        lab = "근거 확인"  # 일부러 한 건 다르게
                    r["판정"] = lab
                w.writerow(r)
    # 공유 폴더의 연습5건 시트를 구글 시트에서 CSV로 받은 모양: 맨 위 안내 줄, 괄호 설명이 붙은 칸 이름, '예' 줄, BOM 없음
    with open(os.path.join(TMP, "eval", "gold", "demo_사람약속목록.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["1~4칸은 김성태가 채워요. '예' 줄은 형식 예시예요(실제 문장 아님).", "", "", ""])
        w.writerow(["번호", "약속 문장 (원문 그대로)", "약속 위치 (보고서, 장)", "분류 (구체적/방향성)"])
        w.writerow(["예", "2025년 중 A공장 조립 라인 전체에 AI 외관 검사를 도입할 계획입니다", "2024 사업보고서, II. 사업의 내용", "구체적"])
        w.writerow([1, "당사는 2025년 중 A공장 조립 라인에 AI 기반 외관 검사 시스템을 도입할 계획입니다.", "2024 사업보고서, II. 사업의 내용", "구체적"])
        w.writerow([2, "당사는 해외 법인 5곳에 사내 AI 번역 도구를 2025년 중 도입할 예정입니다.", "2024 사업보고서, II. 사업의 내용", "구체적"])
        w.writerow([3, "당사는 2026년까지 사내 AI 교육을 전 직원으로 넓힐 계획입니다.", "", ""])  # AI가 못 찾는 문장(시험용)
        w.writerow([4, "당사는 서버용 메모리 수요 대응에 집중할 계획입니다.", "", ""])  # AI 관련 말이 없는 문장: v2로 비율에서 빠져야 함
    r = subprocess.run([sys.executable, os.path.join(ROOT, "eval", "evaluate.py"), "--companies", "demo", "--dev",
                        "--gold-dir", os.path.join(TMP, "eval", "gold"), "--work-root", os.path.join(TMP, "work"),
                        "--out-dir", os.path.join(TMP, "eval", "results")], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit("평가 스크립트 실패")
    res = json.load(open(os.path.join(TMP, "eval", "results", "results.json"), encoding="utf-8"))[0]
    assert res["n"] >= 5 and res["citation_verified"] in (None, 1.0) and res["unsupported_execution_claims"] == 0
    ex = res["extraction"]
    assert ex and ex["human"] == 3 and ex["found"] == 2, f"사람 약속 목록 읽기 실패 ('예' 줄과 안내 줄은 빼고 3건이어야 함): {ex}"
    assert ex["excluded_no_ai_word"] == 1, f"AI 관련 말이 없는 문장을 빼지 못함 (판정기준 v2): {ex}"
    # 약속 찾기 비교: 키워드 규칙은 "AI 시장은 ... 성장할 것으로 예상됩니다"(전망)까지 골라 8개, 엔진은 7개.
    # 사람 목록 3건 중 보고서에 있는 2건을 둘 다 찾음.
    cmp_ = res["extraction_compare"]
    assert cmp_ and cmp_["keyword_rule"]["n_pred"] == 8 and cmp_["engine"]["n_pred"] == 7, cmp_
    assert abs(cmp_["keyword_rule"]["precision"] - 2 / 8) < 1e-9 and abs(cmp_["engine"]["precision"] - 2 / 7) < 1e-9, cmp_
    assert abs(cmp_["keyword_rule"]["recall"] - 2 / 3) < 1e-9 and abs(cmp_["engine"]["recall"] - 2 / 3) < 1e-9, cmp_
    md = open(os.path.join(TMP, "eval", "results", "results.md"), encoding="utf-8").read()
    assert "AI 관련 말이 없는 1개" in md, "결과표에 뺀 개수가 없음"
    assert res["human_agreement"]["n"] >= 5, "cp949로 저장한 판정 파일 읽기 실패"
    check_sentence_gold()

    # 첫 실제 실행용 1건 시험: --limit 1이면 구체적 약속 1건만 판정
    out = run("judge", "--company", "demo", "--mock", "--limit", "1")
    one = json.load(open(os.path.join(TMP, "work", "demo", "judged.json"), encoding="utf-8"))["promises"]
    assert "시험 실행" in out and len(one) == 1 and one[0]["type"] == "specific", "--limit 1 시험 실패"
    run("card", "--company", "demo", "--mock")
    check_extract_filter()
    check_user_test_analysis()

    # 후보 기업 미리 보기: 약속 보고서 PDF 1개만 있어도 돌아가고(근거 PDF 없음), 기준 통과 여부를 알려 줘야 함
    out = run("scan", "--company", "demo_scan", "--mock")
    assert "구체적 약속 6개" in out and "→ 통과" in out, "scan 결과가 다름"
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "run.py"), "scan", "--company", "demo_scan", "--mock",
                        "--min", "7", "--config", os.path.join(TMP, "config.yaml")], capture_output=True, text=True, cwd=ENGINE)
    assert r.returncode == 2 and "→ 미달" in r.stdout, "scan 기준 미달 처리가 다름"
    print("시험 통과")


def check_sentence_gold():
    """서원님 방식: promise_id 없이 직접 찾은 약속 목록에 판정한 파일을 약속 문장으로 AI 약속과 맞추는지 시험합니다."""
    judged = json.load(open(os.path.join(TMP, "work", "demo", "judged.json"), encoding="utf-8"))["promises"]
    spec = [j for j in judged if j["type"] == "specific"]
    dire = [j for j in judged if j["type"] == "directional"]
    assert len(spec) >= 3 and dire, "시험용 약속이 모자랍니다"
    ko = {"evidence_found": "근거 확인", "partial": "일부 확인", "not_verifiable": "공시에서 확인 불가",
          "company_reported_not_pursued": "회사가 미추진으로 공시"}
    other = {"evidence_found": "일부 확인", "partial": "근거 확인", "not_verifiable": "근거 확인",
             "company_reported_not_pursued": "근거 확인"}  # AI와 다른 판정
    rows = [
        (spec[0]["sentence"], ko[spec[0]["verdict"]]),                        # AI와 같은 판정
        (spec[1]["sentence"].replace(" ", "  ", 1), ko[spec[1]["verdict"]]),  # 띄어쓰기가 달라도 맞춰야 함
        (spec[2]["sentence"], other[spec[2]["verdict"]]),                     # AI와 다른 판정
        (dire[0]["sentence"], "근거 확인"),                                    # 사람은 구체적, AI는 방향성
        ("당사는 2026년까지 사내 AI 교육을 전 직원으로 넓힐 계획입니다.", "공시에서 확인 불가"),  # AI가 못 찾은 약속
    ]
    gdir = os.path.join(TMP, "eval_s", "gold")
    os.makedirs(gdir, exist_ok=True)
    head = ["번호", "약속 문장 (원문 그대로)", "약속 위치 (보고서, 장)", "분류 (구체적/방향성)", "근거 문장 (원문 그대로)",
            "근거 위치 (보고서, 장)", "판정", "걸린 시간(분)"]
    for who in ("합의", "김성태", "서원"):
        with open(os.path.join(gdir, f"demo_{who}.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["서원님이 직접 찾은 약속 목록 (시험용, 가상 회사)"])
            w.writerow(head)
            for n, (s, lab) in enumerate(rows, 1):
                if who == "김성태" and n == 1:
                    lab = other[spec[0]["verdict"]]  # 일부러 한 건 다르게
                w.writerow([n, s, "2024 사업보고서", "구체적", "", "", lab, ""])
    out = os.path.join(TMP, "eval_s", "results")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "eval", "evaluate.py"), "--companies", "demo", "--dev",
                        "--gold-dir", gdir, "--work-root", os.path.join(TMP, "work"), "--out-dir", out],
                       capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit("평가 스크립트 실패 (약속 문장으로 맞추기)")
    res = json.load(open(os.path.join(out, "results.json"), encoding="utf-8"))[0]
    assert res["gold_by_sentence"] == {"rows": 5, "matched": 4, "ai_directional": 1, "unmatched": 1}, res["gold_by_sentence"]
    assert res["n"] == 3 and res["correct"] == 2, (res["n"], res["correct"])
    assert res["human_agreement"]["n"] == 5, res["human_agreement"]
    ex = res["extraction"]
    assert ex["source"] == "demo_서원.csv" and ex["human"] == 5 and ex["found"] == 4, ex
    errs = list(csv.DictReader(open(os.path.join(out, "errors_demo.csv"), encoding="utf-8-sig")))
    assert len(errs) == 2 and sum(1 for e in errs if e["원인"] == "분류가 다름") == 1, errs


def check_user_test_analysis():
    """사용자 테스트 기록지 요약: 시간 초과(정답 칸 빈칸)도 실패로 세고, 예행연습·미동의·빈 기록·의견 참여는 정량에서 빼는지 시험합니다."""
    tpl = os.path.join(ROOT, "eval", "user_test", "template.csv")
    with open(tpl, encoding="utf-8-sig") as f:
        head = next(csv.reader(f))
    rows = [
        {"번호": "R0", "구분": "예행연습", "동의": "예", "서비스 4분 안에 끝냄": "예", "서비스 정답": "예"},
        {"번호": "1", "구분": "본 테스트", "동의": "예", "서비스 걸린 시간(초)": "90", "서비스 4분 안에 끝냄": "예", "서비스 정답": "예",
         "직접 검색 4분 안에 끝냄": "아니오", "직접 검색 쓴 도구": "포털", "설문1 이해(1~5)": "5", "설문2 신뢰(1~5)": "4"},
        {"번호": "2", "구분": "본 테스트", "동의": "예", "서비스 걸린 시간(초)": "120", "서비스 4분 안에 끝냄": "예", "서비스 정답": "아니오",
         "직접 검색 걸린 시간(초)": "200", "직접 검색 4분 안에 끝냄": "예", "직접 검색 정답": "예", "설문1 이해(1~5)": "3"},
        {"번호": "3", "구분": "본 테스트", "동의": "아니오"},
        {"번호": "4", "구분": "본 테스트", "동의": "예", "서비스 정답": "예"},
        {"번호": "의견1", "구분": "의견 참여", "설문1 이해(1~5)": "1"},
    ]
    path = os.path.join(TMP, "user_test.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=head)
        w.writeheader()
        for r in rows:
            assert set(r) <= set(head), f"기록지 칸 이름이 템플릿과 다름: {set(r) - set(head)}"
            w.writerow(r)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "eval", "user_test", "analyze.py"), path],
                       capture_output=True, text=True)
    print(r.stdout)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "정량 분석 가능: 2명" in out, "시간 초과(정답 빈칸) 참가자가 빠지거나 다른 행이 섞임"
    assert "AI Promise: 50.0% (1/2)" in out and "직접 검색: 50.0% (1/2)" in out, out
    assert "직접검색 시간 초과: 1/2" in out, out
    assert "본 테스트 4.0/5, 의견 참여(참고) 1.0/5" in out, "설문 평균에 의견 참여가 섞임"


def check_extract_filter():
    """판정기준 v2: AI가 검색어(AI 관련 말)가 없는 앞뒤 문장을 골라도 약속에서 빠지는지 시험합니다."""
    sys.path.insert(0, ENGINE)
    from aipromise.extract import run_extract
    from aipromise.textutil import normalize

    work = os.path.join(TMP, "work_v2")
    os.makedirs(work, exist_ok=True)
    sents = [
        {"id": "y2024-II-0001", "text": "당사는 2025년 중 B공장에 AI 물류 로봇을 도입할 계획입니다.", "page": 1, "has_keyword": True},
        {"id": "y2024-II-0002", "text": "당사는 서버용 메모리 수요 대응에 집중할 계획입니다.", "page": 1, "has_keyword": False},
    ]
    rep = {"title": "2024 사업보고서", "url": "https://example.com/v2", "sections": {"II": {
        "name": "II. 사업의 내용", "sentences": sents, "norm_text": normalize(" ".join(s["text"] for s in sents))}}}
    with open(os.path.join(work, "collected_y2024.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False)

    class PickAll:  # 후보 문장을 모두 약속으로 고르는 가짜 모델
        def json(self, task, system, user, model_key):
            ids = re.findall(r"^(\S+-\S+-\d{4}): ", user.split("[후보 문장]")[-1], re.M)
            return {"promises": [{"id": i, "type": "specific", "title": "시험"} for i in ids]}

    cfg = {"paths": {"eval_dir": os.path.join(TMP, "eval_v2")}}
    company = {"name": "필터시험 (가상 회사)", "key": "v2", "promise_reports": [{"key": "y2024"}]}
    got = run_extract(cfg, company, PickAll(), work)
    dropped = json.load(open(os.path.join(work, "promises.json"), encoding="utf-8"))["dropped"]
    assert [p["sentence_id"] for p in got] == ["y2024-II-0001"], f"AI 관련 말이 없는 문장이 약속에 들어감: {got}"
    assert len(dropped) == 1 and dropped[0]["id"] == "y2024-II-0002" and "AI 관련 말 없음" in dropped[0]["why"], \
        f"버린 이유 기록이 다름: {dropped}"


if __name__ == "__main__":
    main()
