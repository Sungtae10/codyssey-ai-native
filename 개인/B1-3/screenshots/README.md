# 실행 증빙 스크린샷

> 이 폴더의 이미지는 **실제 구현·실행 화면**이다. 마스킹 처리 후 업로드했다.
> 확보하지 못한 캡처는 §3에 **없다고 명시**한다 — 있는 것처럼 링크만 걸어두면 심사에서 즉시 드러난다.

---

## 1. 수록 목록

### 프로젝트 1 (TRC-v2 · Make vs n8n)

| 파일 | 내용 | 문서 대응 |
|---|---|---|
| `make_01_canvas_masked.png` | Make 시나리오 전체 캔버스 — RSS 2 → 필터 `본문기사만` → `01_정규화` 3 → `02_스코어링` 6 → Router 10 → Sheets 11/12 → HTTP 13.<br/>**Router 양쪽이 `1st CORE (score>=2)` / `2nd REF (score<2)` 명시적 조건**으로 선언된 것이 보인다 (Fallback route 미사용 증빙) | `01_WORKFLOW_SPEC.md` §3.3 · §7 |
| `make_02_history_20260730_1252.png` | Make History — 실행 기록 `2026년 7월 30일 오후 12:52:55` 성공 | `04_comparison_report.md` §4.1 |
| `common_01_sheets_core_make_n8n.png` | Google Sheets `TRC_Research_Log` **CORE 탭** — `도구` 열에 **Make 행과 n8n 행이 함께** 적재됨.<br/>같은 기사(경동나비엔 3점 / 엡손 2점 / 한국엡손 3점 / 韓-브라질 4점 / 포유디지탈 3점 / LG전자 배당 2점 / 코웨이 2점)가 **두 도구에서 같은 점수**로 기록된 것이 행 단위로 확인된다 | **동일성 검증 핵심 증빙** — `04_comparison_report.md` §4.2 |
| `common_02_sheets_ref_make_n8n.png` | 같은 스프레드시트 **REF 탭** — Make 34행 + n8n 40행 | 검증 등식 `CORE + REF` |

### 프로젝트 2 (DSR-v1 · DART 공시 시그널 레이더)

| 파일 | 내용 | 문서 대응 |
|---|---|---|
| `p2_01_canvas_1_99_schedule_on.png` | ★ **가장 중요** — 전체 캔버스에 Router 양쪽 번들 수 **SIGNAL 1 / ROUTINE 99** 표시 + 하단에 **`Daily at 오전 8:00` 토글 ON** | 평가 1-4 (자동 실행) · 1-7 (양 분기 실행) |
| `p2_02_router_signal_routine.png` | Router 분기 확대 — `1st SIGNAL ✓1` / `2nd ROUTINE ✓99` → Google Sheets 8 / 9 | `05_project2_design.md` §6.1 |
| `p2_03_canvas_http_iterator_tools.png` | 상류 확대 — HTTP 2 `✓1` → Iterator 3 `✓1` → Tools 5 `✓100` | §3.2 단계별 출력 |
| `p2_04_iterator_array.png` | Iterator 설정 — `Array = 2.data.list` | §4-3 |
| `p2_05_sheets_mapping_signal.png` | Sheets(SIGNAL) A~H 매핑 — D열이 **리터럴 `SIGNAL`** 인 것이 보인다 | §4-6 (리터럴 사용 근거) |
| `p2_06_http_config.png` | HTTP 모듈 설정 — URL `opendart.fss.or.kr/api/list.json`, **Parse response = Yes** | §4-2 |
| `p2_07_sheet_schema.png` | Google Sheets `DSR_Disclosure_Log` — 8열 헤더 + `SIGNAL`/`ROUTINE` 탭 구조 | §4-0 |

### 참고 — 폐기한 설계의 증거 (설계 문서 §7)

| 파일 | 내용 |
|---|---|
| `p2_ref_tools_variables.png` | Tools 모듈의 `matched` 변수 설정 — `if(contains(3.report_nm; "유상증자"); ...)` |
| `p2_ref_tools_output_matched_empty.png` | 그 실행 출력 — `collected_at`·`dart_link`는 정상인데 **`matched: empty`**.<br/>→ 이 실측이 `05_project2_design.md` §7-①(중간 변수 제거, Router가 원본 필드를 직접 검사)의 근거다 |

---

## 2. 마스킹 처리

| 대상 | 처리 |
|---|---|
| Discord Webhook URL | `make_01_canvas_masked.png` 우하단 HTTP 모듈 라벨을 **검은 박스로 덮음** |
| OPENDART `crtfc_key` | 키가 보이는 캡처는 **이 폴더에 포함하지 않았다.** 해당 키는 노출 발견 즉시 **재발급하여 무효화** (`05_project2_design.md` §8) |
| Google 서비스 계정 Private Key | 캡처 없음 |
| 계정 이메일 · 스프레드시트 ID | 캡처 범위에 미포함 |

---

## 3. 확보하지 못한 캡처 (정직하게 명시)

| 파일명 | 내용 | 사유 |
|---|---|---|
| `make_09_run_once.png` | Make 캔버스에 번들 수 `8 / 34` 가 표시된 상태 | 실행 직후 캡처를 남기지 못했다. 대신 **결과물인 Sheets 적재 행**(`common_01`·`common_02`)과 History 실행 기록으로 대체한다 |
| `n8n_06_canvas.png` | n8n 캔버스 `9 / 40` | 동일. n8n 실행 결과는 `common_01`·`common_02`의 `도구 = n8n` 행으로 확인 가능하다 |
| `n8n_07_executions.png` | Executions ID#17 (12.424s) | 동일 |
| `make_10_history_detail.png` | Operations 135 / 190.5 KB 상세 | History 상세 로그 보존 기간 경과 |
| `common_03_discord.png` | Discord `#research-core` 알림 메시지 | 캡처 미보존 |

> **대체 증빙의 논리**: 캔버스의 번들 숫자는 *실행 중* 상태를 보여주고, 시트의 적재 행은 *실행 결과*를 보여준다. 후자가 더 강한 증거다 — 숫자는 화면에서 사라지지만 행은 남는다. `CORE` 탭에 Make 8행과 n8n 행이 **같은 기사·같은 점수**로 나란히 있는 것이 이 과제의 동일성 주장을 직접 뒷받침한다.

---

## 4. 재캡처 방법 (여력이 있다면)

| 캡처 | 경로 |
|---|---|
| Make 실행 이력 | Make → 시나리오 열기 → 좌측 `History` → 2026-07-30 12:52 실행 클릭 |
| n8n 실행 이력 | `npx.cmd n8n` 재기동 → <http://localhost:5678> → 워크플로우 → `Executions` 탭 |
| Discord 알림 | Discord `#research-core` 채널 스크롤 |

**촬영 규칙**: 전체 화면이 아니라 **브라우저 창 영역만** 캡처한다(`Alt+PrtSc`). 전체 화면은 북마크바·다른 탭 제목·바탕화면 파일명이 함께 찍힌다 — 가장 자주 나는 사고다.
