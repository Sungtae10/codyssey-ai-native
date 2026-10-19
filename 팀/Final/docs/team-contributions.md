# 팀 기여 내역

## 김성태: PM / AI Engine / Evaluation / Integration
- 문제 정의와 서비스 범위 설계
- 판정기준 v2 확정·동결
- 공시 수집(OpenDART 자동 수집, GitHub Actions 엔진 실행)·약속 추출·검색·판정·원문 존재 확인(citation verification) pipeline
- Human evaluation 설계, SK하이닉스 공동 판정(김서원과 함께, 엔진을 돌리기 전에 고정)
- 내 경험 연결 서버 함수 (10/20 v2: 경험 → 지원 직무 → 회사 AI 약속)
- GitHub repository/PR/CI 관리
- Frontend 엔진 결과 연결
- 최종 요구사항·증빙·배포 관리

## 김서원: Human Validation / Research / User Test
- 삼성전자 연습 판정
- SK하이닉스 약속 목록 정리와 1차 판정(10/17), 김성태와 공동 검토로 정답 고정(10/19, 엔진을 돌리기 전. 평가 정답은 한 사람의 독립 판정이 아니라 공동 검토 결과)
- 사람 원문 검토: 삼성전자·SK하이닉스 판정을 DART 원문을 읽고 확인 (코드가 하는 원문 존재 확인과는 다른 일)
- 판정기준 경계 사례 검토
- 실제 사용자 테스트 진행
- 반복 사용자 피드백 정리

## 박수민: Frontend / QA
- 기업 선택 → 약속 목록 → 상세 → 면접 카드의 초기 4개 화면 구현
- Frontend 구조 및 상호작용 구현
- 실제 데이터 연결 후 모바일/PC QA
- 사용자 테스트에서 발견되는 UI 버그 수정

## 서준용: UX/UI / Demo / Presentation
- 최신 UX/UI 시안
- 판정 색상 및 visual hierarchy 개선
- 실제 데이터 화면 UX 검수
- 사용자 테스트 UX 관찰
- 발표자료 및 시연영상

## 협업 방식
- GitHub main 직접 수정 대신 branch → test → PR → merge
- Drive는 팀원 원본/리서치/사용자 테스트 원자료 보관
- GitHub는 실행 코드·고정 방법론·재현 가능한 평가의 source of truth