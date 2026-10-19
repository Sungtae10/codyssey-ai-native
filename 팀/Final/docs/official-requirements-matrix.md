# 공식 Final Project 요구사항 ↔ 증빙 매트릭스

이 문서는 심사자가 요구사항 충족 여부를 빠르게 확인할 수 있도록 만든 제출용 인덱스입니다. 항목별 자세한 증빙과 담당은 [제출 증빙 체크리스트](submission-evidence-checklist.md)에 있습니다.

| 공식 요구사항 | AI Promise 대응 | 증빙 위치 | 상태 |
|---|---|---|---|
| 문제 정의 | 공시 속 AI 계획과 후속 실행 근거를 연결하는 조사 비용 문제 | README, docs/requirements.md | 완료 |
| 타겟 사용자 | 취업·이직 준비자 | README, docs/requirements.md | 완료 |
| 생성형 AI 핵심 기능 | 약속 추출, 판정, 면접 카드 생성 | engine/, docs/architecture.md | 완료 |
| 필수 기술요소 2개 이상 | RAG + 자동화 워크플로우, Agent-style retry 보조 | engine/, docs/architecture.md | 완료 |
| 서비스 아키텍처 | 7단계 파이프라인 | docs/architecture.md | 완료 |
| 기능/비기능 요구사항 | FR-01~FR-32(25개) / NFR-01~NFR-14 | docs/requirements.md | 완료 |
| GitHub 버전관리 | 브랜치/PR/CI/역할 기록 | Git history, CONTRIBUTING.md | 완료 |
| 팀 역할 분담 | PM·AI·Frontend·Validation·UX | README 8장 | 완료 |
| AI 윤리 | 비단정 표현, AI 고지, citation verification | docs/ai-ethics.md | 완료 |
| 개인정보 보호 | 사용자 테스트 실명·연락처 비수집 | docs/ai-ethics.md, 설문 | 완료 |
| 외부 배포 | 공개 URL https://ai-promise-six.vercel.app | README 14장 제출 링크 | 완료 (10/19 접속 확인). 지금 화면은 사람이 원문 대조한 검증용 시연 데이터(PR #19) |
| 실제 사용자 5명+ | 같은 Google Form에 작은 과제를 더해 혼자 써 보는 방식으로 최소 5명 (여유가 있으면 6~10명) | docs/user-test-quick.md | **필수 미완료** |
| 사용자 피드백 반영 | 반복 피드백 1~2건 → commit/PR | docs/feedback-log.md | **필수 미완료** |
| README 결과 정리 | 배포 URL·사용자 수·피드백·결과 | README | 테스트 후 업데이트 |
| 발표자료 | 문제→AI→데모→검증→피드백→한계 | docs/presentation-outline.md | 초안 완료 |

## 제출 직전 반드시 채울 3개
1. 공개 서비스 URL 최종 확인 (주소와 검증용 시연 데이터는 있음)
2. 실제 사용자 수 및 설문 집계
3. 실제 피드백 반영 commit/PR

위 3개가 채워지기 전에는 공식 필수요건이 완결되지 않습니다.
