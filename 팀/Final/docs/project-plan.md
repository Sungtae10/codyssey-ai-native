# AI Promise 프로젝트 기획서

## 1. 문제 정의
취업·이직 준비자가 기업의 AI 전략을 확인하려면 여러 연도의 사업보고서와 반기보고서를 직접 읽고, 과거의 계획과 이후 실행 근거를 수작업으로 연결해야 합니다. 단순 검색이나 요약만으로는 '회사가 과거에 무엇을 약속했고 이후 공시에서 어떤 실행 근거가 확인되는가'를 빠르게 파악하기 어렵습니다.

## 2. 타겟 사용자
1순위: 취업·이직 준비자  
2순위: 기업의 AI 전략을 공시 근거로 확인하려는 일반 사용자

## 3. 서비스 정의
AI Promise는 DART 정기공시에서 기업의 AI 관련 미래 계획을 추출하고, 후속 공시에서 관련 실행 근거를 검색해 아래 4개 상태로 보여주는 서비스입니다.

- 근거 확인
- 일부 확인
- 공시에서 확인 불가
- 회사가 미추진으로 공시

'공시에서 확인 불가'는 실제 미이행을 뜻하지 않습니다.

## 4. AI 활용 방식
### 4.1 생성형 AI
- AI 약속 후보 추출
- 구체적/방향성 분류
- 약속과 근거의 판정
- 면접 카드 생성

### 4.2 RAG
후속 정기공시에서 약속과 관련된 근거 후보를 검색해 LLM의 판정 컨텍스트로 제공합니다.

### 4.3 자동화 워크플로우
Collect → Extract → Retrieve → Judge → Citation Verify → Interview Card → Export 단계가 Python pipeline으로 연결됩니다.

### 4.4 Agent-style retry
근거가 약할 때 제한된 횟수만큼 검색어를 바꿔 재검색합니다. 완전 자율 Agent라고 과장하지 않고 구현된 상태 기반 재검색만 설명합니다.

## 5. 기술적 접근
- 데이터: DART 정기공시
- AI: OpenAI API 기반 LLM/Embedding
- 검색: 키워드 + vector retrieval
- 검증: 근거 인용 exact-match 검사
- Frontend: HTML/CSS/JavaScript
- 배포: 정적 웹 배포
- 품질관리: GitHub Actions + mock test + UI test

## 6. 핵심 사용자 흐름
1. 기업 선택
2. AI 약속 목록 확인
3. 약속별 후속 공시 근거와 판정 확인
4. DART 원문으로 검증
5. 면접 카드 확인

## 7. 데이터 범위
### Core
- 삼성전자
- SK하이닉스

### Demo
- 카카오
- 신한은행
- NAVER

Core 기업은 방법론과 검증 중심, Demo 기업은 확장 가능성 시연 중심으로 구분합니다.

## 8. 팀 역할
- 김성태: PM, AI Engine, Evaluation, GitHub/Integration/Deployment
- 김서원: Human Validation, 공시 리서치, 사용자 테스트
- 박수민: Frontend 구현 및 QA
- 서준용: UX/UI, 사용자 테스트 보조, 발표/영상

## 9. 일정
- 기획/기준 확정: 완료
- Core 엔진/화면 통합: 진행
- 사용자 테스트: 최소 5명
- 피드백 반영: 테스트 후 1~2건
- 최종 README/발표/영상: 제출 전 마무리

## 10. 성공 기준
필수:
- 외부 접근 가능한 서비스 URL
- 실제 사용자 5명 이상
- 사용자 피드백 수집 및 실제 반영
- GitHub 버전 관리
- AI 생성 고지 및 개인정보 보호
- RAG 포함 필수 기술요소 2개 이상

품질:
- 원문 링크 제공
- citation verification
- 비단정 표현
- Core 기업 실제 데이터 end-to-end