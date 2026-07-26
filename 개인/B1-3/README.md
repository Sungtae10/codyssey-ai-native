# B1-3 · 노코드 자동화 기초: 워크플로우 설계

**미션** 동일 워크플로우를 2개 이상의 자동화 도구로 구현·비교 + 자유 주제 자동화 설계·구현
**사용 도구** Make (클라우드 관리형) · n8n Community Edition (셀프호스팅) — **유료 결제 0원**
**제출자** 성태

---

## 📌 심사자용 바로가기

| 평가 대상 | 문서 | 비고 |
|---|---|---|
| **[프로젝트 1] 비교 분석 보고서** | [docs/04_비교분석보고서.md](docs/04_비교분석보고서.md) | 비교 항목 **8개** (요구 5개 초과) |
| **[프로젝트 2] 설계·구현 문서** | [docs/05_프로젝트2_설계문서.md](docs/05_프로젝트2_설계문서.md) | 반복 업무 정의·도구 선정 이유·흐름 설명·다이어그램 포함 |
| 도구 중립 워크플로우 명세서 | [docs/01_WORKFLOW_SPEC.md](docs/01_WORKFLOW_SPEC.md) | 두 구현체의 **동일성 증빙 근거** (5개 계약) |
| 구현 화면·실행 결과 스크린샷 | [screenshots/](screenshots/) | 파일명 규칙은 아래 표 참조 |
| 워크플로우 구조 다이어그램 | [assets/TRC-v1_workflow.mermaid](assets/TRC-v1_workflow.mermaid) | GitHub에서 자동 렌더링 |
| n8n 워크플로우 JSON | [workflows/n8n_TRC_v1.json](workflows/n8n_TRC_v1.json) | import용 (수동 구성이 정본) |
| 스코어링 로직 단위 테스트 | [workflows/_test_scoring.js](workflows/_test_scoring.js) | `node workflows/_test_scoring.js` |

---

## 프로젝트 1 — 자동화 도구 비교 구현 (Make vs n8n)

**워크플로우 TRC-v1**: 전자신문 RSS 신규 기사 감지 → 정규화 → 전략 시그널 키워드 12개 스코어링 → `score ≥ 2` 조건 분기 → CORE는 Google Sheets 적재 + Discord 알림 / REF는 Sheets 적재만

```
[Trigger] RSS 신규 기사 (1일 1회 08:00 KST, 최대 5건)
    → [Action 1] 정규화 (HTML 제거·200자 절단·KST 통일)
    → [Action 2] 스코어링 (키워드 12개 매칭, 0~12점)
    → [분기] score ≥ 2 ?
        ├ CORE → [Action 3] Sheets(CORE) → [Action 4] Discord 알림
        └ REF  → [Action 5] Sheets(REF)   ※ Fallback route — 유실 0 보장
```

- Trigger 1개 · **Action 5개** · 조건 분기 1개 — 요구사항 충족
- **양 분기 실행 증빙**: [screenshots/make_07_run_once.png](screenshots/make_07_run_once.png) · [screenshots/n8n_06_test_run.png](screenshots/n8n_06_test_run.png)
- **동일성 증빙**: 같은 스프레드시트·같은 9열 스키마에 `도구` 열만 달리해 적재 → [screenshots/common_01_sheets_both.png](screenshots/common_01_sheets_both.png)

## 프로젝트 2 — 자유 주제: 대학원 공고 메일 마감일 트리아지 (Make)

**반복 업무**: 대학원 모집요강·학회·장학 공고 메일에서 마감일을 찾아 잔여일을 계산하고 기록하는 작업 (주 약 25분 + 마감 누락 리스크)

```
[Trigger] Gmail 라벨 GradApp 메일 수신 (자동 실행)
    → 정규화 → [Text parser] 마감일 정규식 추출 → 마감일 조립
    → [분기] 마감일 존재 ∧ D-7 이내 ?
        ├ URGENT → Discord 알림 → Sheets(URGENT)
        └ NORMAL → Sheets(NORMAL)  ※ Fallback route
```

- **자동 실행 증빙**: 스케줄 설정 [p2_08_schedule_on.png](screenshots/p2_08_schedule_on.png) + 스케줄에 의한 자동 실행 기록 [p2_09_auto_history.png](screenshots/p2_09_auto_history.png)
- 도구 선정 이유는 비교 항목 3개(가동 지속성·인증 방식·실행 로그)와 연결 → [설계 문서 §2](docs/05_프로젝트2_설계문서.md)

---

## 스크린샷 목록

| 구분 | 파일 | 내용 |
|---|---|---|
| Make | `make_01`~`make_09` | 트리거·정규화·스코어링·Router·Sheets·HTTP(마스킹)·**실행 결과**·History·오퍼레이션 사용량 |
| n8n | `n8n_01`~`n8n_07` | 트리거·Code·Switch·Sheets·HTTP(마스킹)·**실행 결과**·Executions |
| 공통 | `common_01`~`common_02` | **동일 스키마 병렬 적재**·Discord 알림 |
| P2 | `p2_01`~`p2_09` | Gmail 트리거·Text parser·Router·실행 결과·알림·시트·**자동 실행 증빙 2장** |

## 🔒 보안

- Discord Webhook URL·Google 서비스 계정 키는 **모든 스크린샷에서 마스킹** 처리
- 서비스 계정 키 JSON은 `.gitignore`로 커밋 차단
- 자동화 범위를 Gmail 라벨로 한정해 민감 메일이 파이프라인에 진입하지 않도록 설계

## 문서 전체 구조

```
├── README.md                        ← 지금 이 문서 (심사자 진입점)
├── docs/
│   ├── 01_WORKFLOW_SPEC.md          도구 중립 명세서 (동일성 계약 5개)
│   ├── 02_MAKE_구현가이드.md         Make 모듈 7개 설정값
│   ├── 03_n8n_구현가이드.md          n8n 설치·노드 6개·Code 로직
│   ├── 04_비교분석보고서.md          ★ 프로젝트 1 제출물
│   ├── 05_프로젝트2_설계문서.md      ★ 프로젝트 2 제출물
│   ├── 06_심층인터뷰_QA스크립트.md   평가 항목 2·3·4 대비
│   └── 07_제출_체크리스트.md         평가표 1:1 매핑 + 보안 점검
├── screenshots/                     구현·실행 증빙
├── workflows/                       n8n JSON + 로직 단위 테스트
└── assets/                          다이어그램
```
