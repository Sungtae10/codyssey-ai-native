# START HERE — 이 저장소를 읽는 순서

**과제** Codyssey B1-3 · 노코드 자동화 기초: 워크플로우 설계
**제출 형식** GitHub 저장소 (`main` 브랜치)

---

## 1. 심사자라면 — 3분 경로

| 순서 | 문서 | 왜 |
|---|---|---|
| 1 | [README.md](README.md) | 실측 결과 요약 · 두 프로젝트 구조 |
| 2 | [docs/04_comparison_report.md](docs/04_comparison_report.md) | **프로젝트 1 필수 제출물** — 비교 항목 9개 |
| 3 | [docs/05_project2_design.md](docs/05_project2_design.md) | **프로젝트 2 필수 제출물** — As-Built 설계·구현 |
| 4 | [screenshots/](screenshots/) | 실행 증빙 (마스킹 완료본) |
| 5 | [docs/07_submission_checklist.md](docs/07_submission_checklist.md) | 평가표 1:1 자체 감사 결과 |

**핵심 3장만 보고 싶다면**: `screenshots/p2_01_canvas_1_99_schedule_on.png` (P2 분기 1/99 + 스케줄 ON) · `screenshots/common_01_sheets_core_make_n8n.png` (두 도구의 동일 기사·동일 점수) · `screenshots/make_01_canvas_masked.png` (Router 명시적 조건). 미확보 캡처는 `screenshots/README.md` §3에 사유와 함께 적어 두었다.

---

## 2. 문서 지도

| 파일 | 역할 | 평가 항목 대응 |
|---|---|---|
| `docs/01_WORKFLOW_SPEC.md` | 도구 중립 명세서 (계약 5개 + 실측 검증 기록) | **항목 2-1** 동일성 설계 기준 |
| `docs/02_make_guide.md` | Make As-Built 설정값·수식 전문 | 항목 1 재현성 |
| `docs/03_n8n_guide.md` | n8n As-Built 설정값·Code 노드 전문 | 항목 1 재현성 |
| `docs/04_comparison_report.md` | ★ 비교 분석 보고서 (9개 항목) | **항목 1-2·1-3**, 항목 3-2 |
| `docs/05_project2_design.md` | ★ 프로젝트 2 설계·구현 (As-Built) | **항목 1-4·1-5**, 항목 2-2·2-3, 3-3 |
| `docs/06_interview_qa.md` | Q1~Q14 + Q8-1 트러블슈팅 12건 | **항목 3·4 전 문항** |
| `docs/07_submission_checklist.md` | 평가표 자체 감사 + 보안 점검 | 전 항목 |
| `assets/TRC-v2_workflow.mermaid` | 프로젝트 1 구조 다이어그램 | GitHub 자동 렌더링 |
| `assets/DSR-v1_workflow.mermaid` | 프로젝트 2 구조 다이어그램 | GitHub 자동 렌더링 |
| `workflows/n8n_TRC_v2.json` | n8n import용 구조 파일 (자리표시자 포함) | 참고 |
| `workflows/_test_scoring.js` | 스코어링 로직 단위 테스트 | 항목 2 설계 방법론 |

---

## 3. 이 과제를 어떤 순서로 했는가

```
① 도구 중립 명세서 작성 (TRC-v1)          ← 도구를 열기 전에
② 스코어링 로직을 Node.js로 단위 테스트    ← v1 사전이 CORE 0건 → 폐기·재설계
③ Make 구현 · 실행                        ← Fallback route 34건 유실 발견 → 명시적 조건
④ n8n 구현 · 실행                         ← Switch 9건 유실 발견 → If 노드
⑤ 레코드 단위 동일성 대조 (7/7 일치)
⑥ 명세서를 실측으로 개정 (TRC-v2, §8 개정 로그)
⑦ 프로젝트 2 (DSR-v1) 구현 · 자동 실행
⑧ 비교 분석 보고서 · 인터뷰 대비 문서 정리
```

**①과 ⑥의 순환이 이 과제의 방법론이다.** 명세서를 먼저 쓴 것이 옳았던 이유는 처음부터 맞았기 때문이 아니라, **무엇이 왜 틀렸는지 항목 단위로 추적할 수 있었기** 때문이다.

---

## 4. 재현 방법

```bash
# 스코어링 로직 검증 (도구 없이)
node workflows/_test_scoring.js
```

Make·n8n 재현은 각각 `docs/02_make_guide.md` / `docs/03_n8n_guide.md` 의 설정값을 그대로 따르면 된다.
n8n JSON을 import할 경우 `YOUR_SPREADSHEET_URL_HERE` / `YOUR_DISCORD_WEBHOOK_URL_HERE` 두 자리표시자와 Google 자격증명만 채우면 동작한다.

---

## 5. 데이터 소스

- 프로젝트 1 — 전자신문 전자 섹션 RSS <https://rss.etnews.com/06.xml>
- 프로젝트 2 — 금융감독원 OPENDART 공시검색 API <https://opendart.fss.or.kr/api/list.json>

둘 다 무료이고 공개 데이터다. 유료 결제는 사용하지 않았다.
