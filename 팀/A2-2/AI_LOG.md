# AI 활용 기록

팀원 각자 작업하면서 즉시 기록한다. 형식: 날짜 | 이름 | 파일 → 프롬프트 / 도구 / 결과 / 검증

## 2026-09-15 | 김성태 (A, 팀장) | 프로젝트 뼈대
- 프롬프트: "코디세이 A2-2 미션 요구사항을 4명이 병렬로 개발할 수 있게 모듈 구조, SQLite 스키마, 함수 시그니처를 먼저 설계하고 Day 1 뼈대 코드를 만들어줘"
- 도구: Claude
- 결과: main.py(argparse 8개 서브커맨드), config.py, db.py(4개 테이블·CRUD), seed_sample.py, 샘플 데이터 20건, 각 모듈 초안, 실행계획서(Word)
- 검증: `python seed_sample.py` → raw/clean 20건 적재, `list`/`show`/`report`/`export csv·xlsx` 실행 확인. `summarize` 는 API 키 없이 실행 시 오류 로그 후 스킵되는 것 확인

## 2026-09-16 | 박수민 (B) | fetcher.py
- 프롬프트: "feedparser로 RSS entries를 dict 목록으로 바꾸는 함수(fetch_rss)와 Google News 리다이렉트 URL 처리 및 재시도(3회) 로직이 포함된 본문 크롤링 함수(fetch_body, fetch_crawl)를 작성해줘. 키는 url, title, body, source, method, category, published_raw, collected_at으로 구성."
- 도구: Antigravity / Gemini
- 결과: RSS 파싱 및 BeautifulSoup lxml 기반 본문 추출 함수 초안 생성. 대상 언론사 robots.txt 정책 확인(https://www.hani.co.kr/robots.txt, https://zdnet.co.kr/robots.txt) 후 허용 경로 확인 및 CodysseyNewsBot/1.0 User-Agent와 요청 딜레이(request_delay_sec=1.0) 적용.
- 검증: Google News IT/경제 RSS 및 ZDNet 섹션 크롤링 테스트 수행, 20건 정상 수집 확인.

## 2026-09-16 | 박수민 (B) | cleaner.py
- 프롬프트: "수집된 raw 기사의 HTML 태그 제거, 연속 공백 정리, RFC 2822 및 ISO 날짜를 YYYY-MM-DD로 변환하는 정규화 함수(normalize_text, normalize_date)와 필수 필드 검증 및 본문 길이 100자 미만 제외 로직이 포함된 clean_article 함수 작성해줘."
- 도구: Antigravity / Gemini
- 결과: email.utils와 정규식을 결합한 다양한 날짜 포맷 파싱 및 텍스트 정제 파이프라인 구현.
- 검증: RSS 수집 기사 및 결측치/짧은 기사에 대해 단위 테스트 실행. 본문 100자 미만 기사 필터링 및 YYYY-MM-DD 정규화 검증 완료.

## 2026-09-16 | 박수민 (B) | main.py & db.py (fetch/clean 연동)
- 프롬프트: "argparse를 이용해 fetch(--source, --category, --limit) 및 clean(--limit) 서브커맨드를 구현하고 SQLite DB의 raw_articles, clean_articles 테이블에 중복 정책(skip/upsert)을 적용하여 저장하는 CLI 및 DB 핸들러 작성해줘."
- 도구: Antigravity / Gemini
- 결과: CLI 서브커맨드 라우팅 및 DB 커넥션/CRUD 연동 완료. 실행 시 신규, 중복스킵, 갱신, 정제 성공/제외 건수 요약 로깅 지원.
- 검증: `python main.py fetch --limit 10` 및 `python main.py clean` 실행 후 중복 방지 및 SQLite 저장 확인.

## 2026-09-16 | 김범근 (D) | report.py
- 도구: ChatGPT
- 작업: matplotlib 차트 2종, Markdown 리포트, CSV/Excel/JSONL 내보내기 기능 구현
- 검증: 샘플 뉴스 데이터로 report/export 명령 실행
- 결과: chart_category.png, chart_daily.png, report.md, news.csv, news.xlsx 생성 확인

## 2026-09-17 | 한다혜 (C) | ai_client.py, analyzer.py, tests/test_analyzer.py
- 도구: (본인이 기입)
- 작업: OpenAI 호출 래퍼(call_json, JSON 추출·재시도), 요약(summarize_one)·인사이트(analyze_range) 구현, 응답 형식 검증, 단위 테스트 작성
- 검증: `python -m unittest discover -s tests -t .` 통과
- (프롬프트와 세부 검증 내용은 한다혜가 추가 기입)

## 2026-09-18 | 김성태 (A, 팀장) | 통합
- 프롬프트: "팀원 3명이 개인 폴더에 올린 코드를 계획서의 함수 시그니처 계약에 맞춰 루트 모듈 파일로 통합해줘"
- 도구: Claude
- 결과: fetcher/cleaner(박수민), ai_client/analyzer(한다혜), report(김범근)를 루트로 통합. fetch_rss/fetch_crawl에 timeout 인자 추가, analyzer에 format_analysis 추가, report 함수 인자를 main.py 계약(build_report(conn, cfg), export_data(rows, fmt, out_path))에 맞춤. 개인 폴더 삭제, AI 로그 통합, .gitignore/.env.example 복구.
- 검증: seed → list → show → summarize(키 없이 스킵) → report → export csv/xlsx/jsonl → 단위테스트 통과
