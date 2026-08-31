# B1-3 · 노코드 자동화 기초: 워크플로우 설계

**미션** 동일 워크플로우를 2개 이상의 자동화 도구로 구현·비교 + 자유 주제 자동화 설계·구현
**사용 도구** Make (클라우드 관리형) · n8n Community Edition v2.32.6 (셀프호스팅) — **유료 결제 0원**
**구현·측정일** 2026-07-30

---

## 📋 진행 상태

| 단계 | 상태 |
|---|---|
| 도구 중립 명세서 (TRC-v2, 계약 5개) | ✅ 완료 |
| 스코어링 로직 단위 테스트 (Node.js, 도구 투입 전) | ✅ 완료 |
| **프로젝트 1 — Make 구현·실행** | ✅ 완료 (`8 + 34 = 42`, 135 op, 18.0s) |
| **프로젝트 1 — n8n 구현·실행** | ✅ 완료 (`9 + 40 = 49`, ID#17, 12.424s) |
| **프로젝트 1 — 동일성 검증** | ✅ 완료 (같은 기사 7건 점수 **7/7 일치**) |
| **프로젝트 2 — Make 구현·자동 실행** | ✅ 완료 (`1 + 99 = 100`, Daily 08:00 스케줄 ON) |
| 비교 분석 보고서 (비교 항목 **9개**) | ✅ 완료 |
| 실행 스크린샷 | 📷 `screenshots/` |

---

## 📌 심사자용 문서 바로가기

| 평가 대상 | 문서 | 비고 |
|---|---|---|
| **[프로젝트 1] 비교 분석 보고서** | [docs/04_comparison_report.md](docs/04_comparison_report.md) | 비교 항목 **9개** (요구 5개 초과) · 전 항목 실측 근거 |
| **[프로젝트 2] 설계·구현 문서** | [docs/05_project2_design.md](docs/05_project2_design.md) | 반복 업무 정의·도구 선정 근거·다이어그램·**As-Built** |
| 도구 중립 워크플로우 명세서 | [docs/01_WORKFLOW_SPEC.md](docs/01_WORKFLOW_SPEC.md) | 두 구현체의 **동일성 증빙 근거** (계약 5개 + 실측 §9) |
| Make 구현 가이드 | [docs/02_make_guide.md](docs/02_make_guide.md) | 모듈 7 + 필터 2, 수식 전문 |
| n8n 구현 가이드 | [docs/03_n8n_guide.md](docs/03_n8n_guide.md) | 노드 8, Code 노드 전문 |
| 심층 인터뷰 Q&A | [docs/06_interview_qa.md](docs/06_interview_qa.md) | 평가 항목 2·3·4 전 문항 + 트러블슈팅 12건 |
| 제출 체크리스트 | [docs/07_submission_checklist.md](docs/07_submission_checklist.md) | 평가표 1:1 자체 감사 + 보안 점검 |
| 워크플로우 다이어그램 | [assets/](assets/) | TRC-v2 (P1) · DSR-v1 (P2) |
| n8n 워크플로우 JSON | [workflows/n8n_TRC_v2.json](workflows/n8n_TRC_v2.json) | import용 — 아래 보안 원칙 참조 |
| 스코어링 단위 테스트 | [workflows/_test_scoring.js](workflows/_test_scoring.js) | `node workflows/_test_scoring.js` |

---

## 프로젝트 1 — 자동화 도구 비교 구현 (Make vs n8n)

**TRC-v2 · 기술경영 리서치 큐레이션 파이프라인**

```
[Trigger] 전자신문 전자 섹션 RSS (1일 1회 08:00 KST)
    ├ [노이즈 필터] 제목에 [포토] 포함 시 제외
    → [Action 1] 정규화 (HTML 제거·200자 절단·KST 통일·JSON 안전화)
    → [Action 2] 스코어링 (가중 2단 시그널 사전 — T1 2점 / T2 1점)
    → [분기] score >= 2 ?
        ├ CORE → [Action 3] Sheets(CORE) → [Action 4] Discord 알림
        └ REF  → [Action 5] Sheets(REF)     ※ 명시적 조건 (Fallback 금지)
```

**실측 결과**

| | Make | n8n |
|---|---|---|
| 수집 → 필터 통과 | 50 → **42** | 50 → **49** |
| CORE / REF | **8 / 34** (19%) | **9 / 40** (18%) |
| 검증 등식 | `8+34=42` ✅ | `9+40=49` ✅ |
| 실행 시간 · 데이터 | 18.0s · 190.5 KB | 12.424s · 127 KB |
| 자원 소모 | 135 오퍼레이션 | 0 (과금 없음) |

**동일성 증빙**: 같은 기사 7건에서 **점수 7/7 일치**. 표기 불일치 1건(후행 쉼표)은 원인과 함께 그대로 기록.

## 프로젝트 2 — 자유 주제: DART 공시 전략 시그널 레이더 (Make)

**DSR-v1** · 금융감독원 **OPENDART 오픈API**(무료 개인 인증키) 기반

```
[Trigger] Make Schedule — Daily 08:00 KST (토글 ON, 수동 개입 없음)
    → [Action 1] HTTP GET list.json (날짜 창 = 무상태 멱등성 설계)
    → [Action 2] Iterator — 공시 목록 100건 분해
    → [Action 3] Set variables — 수집시각 KST · DART 원문 링크
    → [분기] report_nm 이 전략 시그널 서식명을 포함하는가 ?
        ├ SIGNAL  → [Action 4] Sheets(SIGNAL)   1건
        └ ROUTINE → [Action 5] Sheets(ROUTINE) 99건
```

- **실측 `1 + 99 = 100`** — 양 분기 경로 모두 실제 실행, 유실 0
- P1과 의도적 구조 차별화: RSS/상태저장 트리거 ↔ **REST API/날짜 창 멱등성**, 점수 임계값 분기 ↔ **유형 매칭 분기**
- 도구 선정 근거는 P1 비교 항목 3개(⑧ 가동 지속성 · ⑤ 실행 로그 · ③ 무료 플랜)와 연결
- **구현 중 폐기한 설계를 §7에 그대로 기록** — 설계안과 구현물의 차이를 감추지 않는다

---

## 🔍 이 과제에서 얻은 것

두 도구에서 **각각 조용한 데이터 유실 사고**를 겪었다.

| | Make | n8n |
|---|---|---|
| 사고 | Fallback route가 **34건**을 삼킴 | Switch 규칙 모드 불일치로 **9건** 소실 |
| 표시 | 오류 없이 "성공" | 오류 없이 "executed successfully" |
| 해결 | 명시적 조건 `score < 2` | **If 노드** (MECE를 구조로 보장) |

둘 다 **오류가 나지 않았다.** 발견 수단은 하나였다 —

```
CORE 건수 + REF 건수 = 필터 통과 건수
```

도구 지식이 아니라 **검증 습관**이 이 과제의 산출물이다.

---

## 🔒 보안 원칙

- `workflows/n8n_TRC_v2.json` 의 `YOUR_SPREADSHEET_URL_HERE` / `YOUR_DISCORD_WEBHOOK_URL_HERE` 는 **의도된 자리표시자**다. 실제 Webhook URL·문서 ID를 공개 저장소에 커밋하는 것 자체가 민감정보 노출이므로, 실행 증빙은 JSON이 아니라 **마스킹된 스크린샷**으로 제출한다.
- Discord Webhook URL · Google 서비스 계정 Private Key · OPENDART `crtfc_key` 는 모든 스크린샷에서 마스킹하고 문서에는 `***MASKED***` 로 표기한다.
- 서비스 계정 키 JSON · `.env` 는 `.gitignore` 로 커밋을 차단한다.
- **DART 인증키가 캡처 중 1회 노출되어 즉시 재발급했다.** 이 사실을 숨기지 않는 이유는 `docs/05_project2_design.md` §8에 적었다.

## 저장소 구조

```
├── README.md                        심사자 진입점
├── 00_START_HERE.md                 작업 순서 가이드
├── .gitignore                       민감정보 커밋 차단
├── docs/
│   ├── 01_WORKFLOW_SPEC.md          도구 중립 명세서 (계약 5개 + 실측 검증)
│   ├── 02_make_guide.md             Make As-Built 설정값
│   ├── 03_n8n_guide.md              n8n As-Built 설정값
│   ├── 04_comparison_report.md      ★ 프로젝트 1 제출물
│   ├── 05_project2_design.md        ★ 프로젝트 2 제출물
│   ├── 06_interview_qa.md           심층 인터뷰 대비
│   └── 07_submission_checklist.md   평가표 1:1 자체 감사
├── screenshots/                     실행 증빙 (마스킹 완료본)
├── workflows/                       n8n JSON + 스코어링 단위 테스트
└── assets/                          다이어그램 (TRC-v2 · DSR-v1)
```
