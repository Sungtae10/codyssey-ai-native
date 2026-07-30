# Codyssey B1-3 · 노코드 자동화 기초 — 작업 패키지

> **선택된 구성** Make + n8n Community(셀프호스팅) · 주제: 기술경영 리서치 큐레이션 · 보너스 제외 · 유료 결제 0원
> 이 폴더의 문서를 순서대로 따라가면 **스크린샷 캡처만 직접 하고** 나머지는 완성된다.

---

## 왜 이 조합인가 (사실 확인 결과)

| 후보 | 필수 요구사항(Action 2개+ / 분기 1개+) 무료 충족 | 판정 |
|---|---|---|
| **Make Free** | ✅ Router·Filter·Webhook 모두 무료 플랜 포함 (월 1,000 크레딧 / 활성 시나리오 2개 / 최소 15분) | **채택** |
| **n8n Community 셀프호스팅** | ✅ 실행 횟수·워크플로우 수 제한 없음 (제외 항목은 SSO·RBAC 등 엔터프라이즈 기능) | **채택** |
| Zapier Free | ❌ **월 100 태스크 + 2단계 Zap(트리거 1 + 액션 1)만 허용.** 멀티스텝·Filter·Paths는 유료 | 제외 |

Zapier는 14일 Pro 트라이얼로 가능하지만 종료 후 워크플로우가 정지해 재현 검증이 불가능하고, 과제의 "과금 리스크 완화 가이드"에 어긋난다. → 이 판단 근거는 보고서 §5-③에 각주로 실려 있다.

---

## 문서 지도

| 파일 | 용도 | 제출 여부 |
|---|---|---|
| `00_START_HERE.md` | 지금 이 문서. 진행 순서 | — |
| `docs/01_WORKFLOW_SPEC.md` | **도구 중립 명세서 (5개 계약)** — 동일성 증빙의 근거 | 첨부 권장 (가점) |
| `docs/02_make_guide.md` | Make 모듈 7개 클릭 순서 + 수식 복붙용 | 작업용 |
| `docs/03_n8n_guide.md` | n8n 설치 + 노드 6개 + Code 로직 | 작업용 |
| `docs/04_comparison_report.md` | **프로젝트 1 필수 제출물** (비교 항목 8개) | ✅ 필수 |
| `docs/05_project2_design.md` | **프로젝트 2 필수 제출물** | ✅ 필수 |
| `docs/06_interview_qa.md` | 평가 항목 2·3·4 전 문항 답변 스크립트 (Q1~Q14) | 개인용 |
| `docs/07_submission_checklist.md` | 평가표 1:1 매핑 + 보안 점검표 | 개인용 |
| `assets/TRC-v1_workflow.mermaid` | 프로젝트 1 구조 다이어그램 | 첨부 |
| `workflows/n8n_TRC_v1.json` | n8n 임포트용 (⚠️ 미검증 — 수동 구성이 정본) | 참고 |
| `workflows/_test_scoring.js` | 스코어링 로직 단위 테스트 (`node _test_scoring.js`) | 참고 (가점) |
| `workflows/_build_n8n_json.js` | 위 JSON 생성·검증 스크립트 | 참고 |

---

## 진행 순서 (총 예상 3.5~4시간)

### STEP 0 · 공통 준비 (20분)
- [ ] Google Sheets `TRC_Research_Log` 생성 → 탭 `CORE` / `REF` → 두 탭에 9열 헤더
      `수집시각 도구 분류 점수 매칭키워드 제목 요약 발행일 링크`
- [ ] Discord 서버 + 채널 `#research-core` → **Webhook URL 발급**
- [ ] Make 무료 가입
- [ ] `node workflows/_test_scoring.js` 실행해 스코어링 로직 확인 (선택, 1분)

### STEP 1 · Make 구현 (40분) → `docs/02_make_guide.md`
- [ ] 모듈 ①~⑦ 구성
- [ ] `Run once` 실행 → **Router 양쪽에 번들이 지나갔는지 확인**
- [ ] 캡처 1~8, 15

### STEP 2 · n8n 구현 (55분) → `docs/03_n8n_guide.md`
- [ ] `npx n8n` 설치 (Node 20+ 필요)
- [ ] GCP 서비스 계정 발급 + **스프레드시트를 서비스 계정 이메일과 공유** ← 여기서 403 자주 발생
- [ ] 노드 ①~⑥ 구성
- [ ] `Test workflow` → **양쪽 경로 확인**
- [ ] 캡처 1~12

### STEP 3 · 프로젝트 2 구현 (50분) → `docs/05_project2_design.md` §4
- [ ] OPENDART 인증키 발급 (opendart.fss.or.kr — 무료, 개인)
- [ ] 관심 기업 고유번호(corp_code) 확인 — corpCode.xml 다운로드 후 검색
- [ ] Sheets `DSR_Disclosure_Log` (탭 `SIGNAL`/`ROUTINE`, 8열)
- [ ] Discord 채널 `#dart-signal` + Webhook
- [ ] Make 모듈 구성: HTTP(list.json) → status 필터 → Iterator → 분류 Set → Router → Discord+Sheets
- [ ] **검증 T1~T4 실행** — 날짜 창을 과거로 넓혀 SIGNAL·ROUTINE 양쪽 발화 확인 후 **수식 복원** (§6 검증 시나리오)
- [ ] 스케줄 `Every day 08:00` + 토글 ON
- [ ] **스케줄에 의한 자동 실행 기록 1건 확보** ← 평가 항목 1-4의 핵심

### STEP 4 · 문서 마감 (30분)
- [ ] `04_comparison_report.md` §4.1 실행 결과 표 · §4.2 동일성 검증 표 **빈칸 채우기**
- [ ] `05_project2_design.md` §1.2 확인 주기 실측값 기입
- [ ] 두 문서를 PDF로 변환 (또는 Markdown 그대로 제출)
- [ ] 스크린샷 파일명 정리

### STEP 5 · 최종 검증 (15분) → `docs/07_submission_checklist.md`
- [ ] 평가표 1:1 매핑 표 전항 체크
- [ ] **🔒 보안 점검표 S1~S8 전항 확인** ← Webhook URL·Private Key 마스킹
- [ ] 자기 점검 3문항 소리 내어 답하기

---

## ⚠️ 가장 흔히 놓치는 3가지

1. **분기 양쪽 실행 증빙** — 평가 항목 1이 명시적으로 요구한다. Router 한쪽만 번들이 흐른 스크린샷은 FAIL 사유다. 해결 순서는 `02_make_guide.md` §8-3에 있다. **θ나 키워드 사전을 임시로 바꿔 맞추지 말 것** — 스크린샷과 보고서의 임계값이 어긋나면 즉시 지적된다.

2. **P2의 "자동 실행" 증빙 2장 세트** — 스케줄 설정 화면 **+** 그 스케줄로 자동 실행된 History 기록. `Run once` 기록만 내면 "수동 실행 아닌가"를 반드시 묻는다. 하루 기다리기 어렵다면 스케줄을 임시로 `Every 15 minutes`로 두고 자동 실행 1건을 확보한 뒤 되돌린다.

3. **Webhook URL 마스킹** — 캡처 직후 바로 마스킹하고 파일명에 `_masked`를 붙이는 습관. 나중에 하려면 반드시 한 장을 빠뜨린다. 전체 화면 대신 **브라우저 창만** 캡처할 것(북마크바·다른 탭 제목 노출 방지).

---

## 이 패키지에서 사전 검증된 것 / 직접 해야 하는 것

| | 상태 |
|---|---|
| ✅ 검증됨 | 전자신문 RSS 피드 유효성 (RSS 2.0, `<item>` 25건, 필드 구성) |
| ✅ 검증됨 | 스코어링 로직 — Node.js 실행 결과 CORE 2 / REF 3 (양 분기 발화) |
| ✅ 검증됨 | JSON 안전화(N5) — ASCII 큰따옴표 포함 제목이 Discord 페이로드를 깨뜨리지 않음 |
| ✅ 검증됨 | Make 무료 플랜 한도 / 오퍼레이션 계상 규칙 / 텍스트 함수 존재 여부 (공식 문서 기준) |
| ✅ 검증됨 | n8n Community 제외 기능 목록 / Google 서비스 계정 자격증명 지원 (공식 문서 기준) |
| ✅ 검증됨 | Zapier 무료 플랜 2단계 제한 (공식 문서 기준) |
| ✅ 검증됨 | `n8n_TRC_v1.json` 의 JSON 파싱 + Code 노드 문법·실행 결과 |
| ⚠️ 미검증 | `n8n_TRC_v1.json` **전체 임포트** — 작업 환경 네트워크 정책으로 n8n 로컬 설치가 차단되어 실제 임포트 테스트 불가. **수동 구성이 정본** |
| ⚠️ 실측 필요 | Make RSS 모듈 / n8n RSS 노드의 **실제 출력 필드명** (도구 버전에 따라 다름 — 각 가이드에 실측 절차 명시) |
| ⚠️ 실측 필요 | Make 수식의 정규식 이스케이프 동작 (`\x22` 형태) — 오류 시 대안 절차를 §6에 병기 |
| ❌ 직접 수행 | 모든 스크린샷 캡처, Google·Discord 계정 연결, 실행 결과 표 기입 |

---

## 참고 출처

- Make 요금제·무료 한도 — <https://www.make.com/en/pricing>
- Make 텍스트 함수 — <https://help.make.com/text-and-binary-functions>
- 오퍼레이션 계상 규칙 (동일 엔진 Adobe Workfront Fusion 문서) — <https://experienceleague.adobe.com/en/docs/workfront-fusion/using/set-up-and-manage-fusion/licensing-and-operations-overviews/operations-in-workfront-fusion>
- n8n Community Edition 제외 기능 — <https://docs.n8n.io/deploy/host-n8n/community-edition-features/>
- n8n Google 서비스 계정 — <https://docs.n8n.io/integrations/builtin/credentials/google/service-account>
- Zapier 무료 플랜 범위 — <https://help.zapier.com/hc/en-us/articles/32337438839565-What-s-included-in-Zapier-s-Free-plan>
- 데이터 소스 — <https://rss.etnews.com/Section901.xml>
