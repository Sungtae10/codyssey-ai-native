# AI 활용 기록

팀원 각자 작업하면서 즉시 기록한다. 형식은 아래 예시를 따른다.

## 2026-09-15 | 김성태 (A) | 프로젝트 뼈대
- 프롬프트: "코디세이 A2-2 미션 요구사항(첨부)을 4명이 병렬로 개발할 수 있게 모듈 구조, SQLite 스키마, 함수 시그니처를 먼저 설계하고 Day 1 뼈대 코드를 만들어줘"
- 도구: Claude
- 결과: main.py(argparse 8개 서브커맨드), config.py, db.py(4개 테이블·CRUD), seed_sample.py, 샘플 데이터 20건, 각 모듈 초안 생성
- 검증: `python seed_sample.py` → raw/clean 20건 적재, `list`/`show`/`report`/`export csv·xlsx` 실행 확인. `summarize` 는 API 키 없이 실행 시 오류 로그 후 스킵되는 것 확인
