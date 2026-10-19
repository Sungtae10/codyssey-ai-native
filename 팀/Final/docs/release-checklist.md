# 최종 제출 Release Checklist

## P0: 제출 불가를 막는 항목
- [x] 공개 URL이 외부 브라우저에서 열린다 (10/20 01:16 김성태가 시크릿 창에서 확인, PR #41 화면 반영)
- [x] 실제 사용자 5명 이상 설문 응답이 있다 (설문 14명: 고치기 전 화면 12명, 고친 화면 배포 뒤 2명)
- [x] 실제 피드백 1건 이상 제품에 반영했다 (7건: FB-01~FB-05 PR #41, FB-08·FB-09 10/20 v2)
- [x] README에 공개 URL·사용자 수·반영 내용을 적었다
- [x] AI 생성 분석 고지가 화면에 보인다 (`tests/ui_check.py`가 모든 화면에서 확인)

## P1: 서비스 품질
- [x] Core 2 실제 데이터가 화면에 나온다 (운영 사이트 results.json 5개 기업, 10/19 23:40 확인)
- [x] 약속 상세에서 DART 원문 링크가 열린다 (10/20 01:16 김성태가 삼성전자 약속의 "원문 보기"로 확인)
- [x] citation_verified 표시가 실제 데이터와 일치한다 (`tests/check_citation_badges.py`: 약속 24개 화면의 "원문 존재 확인" 표시 수와 확인 단계 문구가 데이터와 같음, 근거 1개를 false로 바꾼 사본에서 표시가 빠짐, 10/20 확인. v2부터 확인 4단계는 접혀 있어 펼친 뒤 읽음)
- [x] 면접 카드가 비어 있거나 깨지지 않는다 (`tests/ui_check.py`: 기업 5곳 카드 화면)
- [x] 모바일 390px에서 가로 스크롤이 없다 (`tests/ui_check.py`: 390·320·1280px)
- [x] 다크/라이트 모드 주요 텍스트 대비 이상 없음 (`tests/ui_check.py`)

## P1: 코드·문서
- [x] python tests/test_config.py (CI)
- [x] python tests/test_mock.py (CI)
- [x] python tests/test_ui_static.py (CI)
- [x] python tests/ui_check.py (CI)
- [x] docs/requirements.md 존재
- [x] docs/official-requirements-matrix.md 최신화 (10/20)
- [x] docs/feedback-log.md 실제 값 기입
- [ ] 발표자료와 3분 시연 영상 (10/20 제작 예정. 저장소 동결(10/20 07:00) 뒤에 만들기 때문에 README에는 링크를 걸지 않고, 드라이브 폴더 `1020_발표자료_영상`에 올릴 예정. README 14장에는 피드백 증빙이 든 같은 폴더 링크만 있음)

## P1: v2 (10/20)
- [x] 이력서 기능 v2 시험 (`node tests/test_resume_api.js`, 가짜 OpenAI): 지원 직무 전달, 직무 없을 때 "선택하지 않음", 간접 연결 한계 문장, 준비할 것, 근거 없는 항목 제외 (CI)
- [x] 운영 주소에서 results.json을 못 읽으면 예시 데이터 대신 "분석 데이터를 불러오지 못했어요" 안내가 나오고, 이 컴퓨터에서 열 때(localhost, 파일)와 `?sample=1`에서만 예시 데이터가 나온다 (가짜 운영 주소로 브라우저 확인)
- [x] `meta.is_sample: false`, `meta.data_status: "real"`, `meta.show_validation_notice: true`로 실제 데이터와 상태값이 모순되지 않는다
- [x] 원문 존재 확인(코드)과 사람 원문 검토를 화면과 문서에서 다른 이름으로 쓴다 (배지, 분석 정보, 확인 4단계 요약 줄, `docs/architecture.md`)
- [x] 용어 칸, 확인 4단계, 분석 정보는 처음에 접혀 있고 접힌 줄에 상태가 보인다 (FB-09, `tests/ui_check.py`는 펼쳐서 검사)
- [x] v2 배포 뒤 운영 사이트 이력서 기능 점검은 GitHub Actions `Resume fit smoke test`(기업, 지원 직무 입력)로 하고 결과는 `smoke-results/<실행번호>` 브랜치에 남김

## P2: 시간이 남으면
- [x] 카카오 시연 데이터 (AI 엔진 결과, PR #39)
- [x] 현대자동차 시연 데이터 (NAVER 대신, AI 엔진 결과, PR #39)
- [x] 신한지주 시연 데이터 (신한은행 대신, AI 엔진 결과, PR #39)
- [ ] Human evaluation 보강
- [ ] 추가 사용자 테스트

## 제출 전 금지
- 실제로 하지 않은 테스트를 했다고 쓰기
- Demo 3를 Human blind evaluation 대상으로 표현하기
- '공시에서 확인 불가'를 '미이행'으로 표현하기
- 샘플 데이터를 실제 기업 데이터처럼 보여주기
