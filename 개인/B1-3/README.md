# B1-3 · 노코드 자동화 기초: 워크플로우 설계

**미션** 동일 워크플로우를 2개 이상의 자동화 도구로 구현·비교 + 자유 주제 자동화 설계·구현
**사용 도구** Make (클라우드 관리형) · n8n Community Edition (셀프호스팅) — **유료 결제 0원**
**제출자** 성태

---

## 📋 진행 상태 (Status Board)

> 이 저장소는 진행 중인 작업물을 그대로 반영합니다. 아래 표가 실제 상태입니다.

| 단계 | 상태 |
|---|---|
| 워크플로우 설계 (도구 중립 명세서 · 5개 계약) | ✅ 완료 |
| 스코어링 로직 단위 테스트 (Node.js, CORE 2/REF 3 발화 확인) | ✅ 완료 |
| 구현 가이드·보고서 초안·인터뷰 대비 문서 | ✅ 완료 |
| **프로젝트 1 — Make 실제 구현·실행** | 🔄 진행 중 |
| **프로젝트 1 — n8n 실제 구현·실행** | 🔄 진행 중 |
| **프로젝트 2 — Make 구현·자동 실행 증빙** | 🔄 진행 중 |
| 실행 스크린샷 (`screenshots/`) | 🔄 구현 후 업로드 예정 |
| 보고서 실측값 기입 (§4.1·§4.2) 및 최종화 | 🔄 실행 후 완료 예정 |

---

## 📌 심사자용 문서 바로가기

| 평가 대상 | 문서 | 비고 |
|---|---|---|
| **[프로젝트 1] 비교 분석 보고서** | [docs/04_comparison_report.md](docs/04_comparison_report.md) | 비교 항목 **8개** (요구 5개 초과) · 실측 기입란은 실행 후 확정 |
| **[프로젝트 2] 설계·구현 문서** | [docs/05_project2_design.md](docs/05_project2_design.md) | 반복 업무 정의·도구 선정 이유·흐름·다이어그램 포함 |
| 도구 중립 워크플로우 명세서 | [docs/01_WORKFLOW_SPEC.md](docs/01_WORKFLOW_SPEC.md) | 두 구현체의 **동일성 증빙 근거** (5개 계약) |
| Make 구현 가이드 | [docs/02_make_guide.md](docs/02_make_guide.md) | 모듈 7개 설정값·수식 |
| n8n 구현 가이드 | [docs/03_n8n_guide.md](docs/03_n8n_guide.md) | 설치·노드 6개·Code 로직 |
| 심층 인터뷰 Q&A | [docs/06_interview_qa.md](docs/06_interview_qa.md) | 평가 항목 2·3·4 전 문항 대응 |
| 제출 체크리스트 | [docs/07_submission_checklist.md](docs/07_submission_checklist.md) | 평가표 1:1 매핑 + 보안 점검표 |
| 워크플로우 다이어그램 | [assets/TRC-v1_workflow.mermaid](assets/TRC-v1_workflow.mermaid) | GitHub 자동 렌더링 |
| n8n 워크플로우 JSON | [workflows/n8n_TRC_v1.json](workflows/n8n_TRC_v1.json) | import용 구조 파일 — 아래 보안 원칙 참조 |
| 스코어링 단위 테스트 | [workflows/_test_scoring.js](workflows/_test_scoring.js) | `node workflows/_test_scoring.js` |

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
- 동일성 설계: 구현 전에 5개 계약(입력 이벤트·정규화·분기·출력·멱등성)을 고정하고 두 도구를 같은 계약의 실행체로 구현 → [명세서](docs/01_WORKFLOW_SPEC.md)
- 분기 로직은 실제 피드 형태의 픽스처 5건으로 **사전 단위 테스트 완료** (CORE 2 / REF 3 — 양 경로 발화)

## 프로젝트 2 — 자유 주제: DART 공시 전략 시그널 레이더 (Make)

**반복 업무**: 관심 기업(대기업)의 전자공시를 수시로 확인해 전략 시그널 공시(투자·M&A·공급계약 등)를 눈으로 선별하는 작업 (주 약 25분 + 관측 공백 리스크). 데이터 소스는 금융감독원 **OPENDART 오픈API** (무료 개인 인증키).

```
[Trigger] Schedule 매일 08:00 KST (자동 실행)
    → [HTTP] DART list.json 조회 (전일 날짜 창 — 무상태 멱등성 설계)
    → [필터] status=000 (공시 없는 날은 조기 종료)
    → [Iterator] 공시 목록 분해 → [분류] 시그널 사전 12개 매칭
    → [분기] 전략 시그널 유형인가 ?
        ├ SIGNAL  → Discord 알림 → Sheets(SIGNAL)
        └ ROUTINE → Sheets(ROUTINE)  ※ Fallback route
```

- P1과 의도적으로 구조를 차별화: RSS/상태저장 트리거(P1) ↔ **REST API/날짜 창 멱등성**(P2), 점수 임계값 분기(P1) ↔ **유형 매칭 분기**(P2)
- 도구 선정 이유는 프로젝트 1의 비교 항목 3개(⑧ 가동 지속성 · ⑤ 실행 로그 · ③ 무료 플랜 예산)와 연결 → [설계 문서 §2](docs/05_project2_design.md)
- 자동 실행 증빙은 **스케줄 설정 화면 + 스케줄에 의한 자동 실행 History** 2장 세트로 제출 예정

---

## 🔒 보안 원칙

- `workflows/n8n_TRC_v1.json`의 `YOUR_SPREADSHEET_URL_HERE` / `YOUR_DISCORD_WEBHOOK_URL_HERE`는 **의도된 자리표시자**입니다. 실제 Webhook URL·문서 ID를 공개 저장소에 커밋하는 것 자체가 민감정보 노출이므로, 실행 증빙은 JSON이 아니라 **마스킹된 스크린샷**으로 제출합니다.
- Discord Webhook URL·Google 서비스 계정 키는 모든 스크린샷에서 마스킹 처리합니다.
- 서비스 계정 키 JSON·`.env`는 `.gitignore`로 커밋을 차단합니다.
- OPENDART API 키(`crtfc_key`)는 스크린샷·문서·저장소 어디에도 원문을 노출하지 않으며(`***MASKED***` 표기), 공시 조회 전용 키라 노출 시에도 재발급으로 즉시 무효화됩니다.

## 저장소 구조

```
├── README.md                        ← 심사자 진입점 (진행 상태 포함)
├── 00_START_HERE.md                 작업 순서 가이드
├── docs/
│   ├── 01_WORKFLOW_SPEC.md          도구 중립 명세서 (동일성 계약 5개)
│   ├── 02_make_guide.md             Make 모듈 7개 설정값
│   ├── 03_n8n_guide.md              n8n 설치·노드 6개·Code 로직
│   ├── 04_comparison_report.md      ★ 프로젝트 1 제출물 (실측 후 최종화)
│   ├── 05_project2_design.md        ★ 프로젝트 2 제출물
│   ├── 06_interview_qa.md           심층 인터뷰 대비
│   └── 07_submission_checklist.md   평가표 1:1 매핑 + 보안 점검
├── screenshots/                     실행 증빙 (구현 후 업로드)
├── workflows/                       n8n JSON + 로직 단위 테스트
└── assets/                          다이어그램
```
