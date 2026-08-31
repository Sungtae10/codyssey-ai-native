# 실행 증빙 스크린샷

> 파일명은 아래 목록을 따른다. 촬영 후 **반드시 마스킹**하고, 원본은 저장소에 올리지 않는다(`.gitignore` 가 `screenshots/_raw/` 를 차단).

## 🔒 마스킹 대상 (예외 없음)

| 대상 | 어디에 나타나는가 | 처리 |
|---|---|---|
| Discord Webhook URL | Make HTTP 모듈, n8n HTTP Request | `{ID}/{TOKEN}` 구간을 검은 박스로 |
| OPENDART `crtfc_key` | Make P2 HTTP 모듈 Query String | 값 전체를 검은 박스로 |
| Google 서비스 계정 Private Key | n8n Credentials | 필드 전체를 검은 박스로 |
| 계정 이메일 | 모든 도구 우상단 | `kks****@gmail.com` 형태로 일부 가림 |
| 스프레드시트 ID | Sheets URL 표시줄 | 가림 권장 |

**촬영 요령**: 전체 화면이 아니라 **브라우저 창 영역만** 캡처한다(`Alt+PrtSc`). 전체 화면을 찍으면 북마크바·다른 탭 제목·바탕화면 파일명이 함께 들어간다 — 가장 자주 나는 사고다.

---

## 필수 목록

### ★ 핵심 5장 — 이것만은 반드시

| 파일명 | 무엇이 보여야 하는가 |
|---|---|
| `make_09_run_once.png` | Make P1 캔버스 — Router 양쪽에 **8 / 34** 번들 수 |
| `n8n_06_canvas.png` | n8n 캔버스 — If 양쪽에 **9 / 40** item 수 |
| `p2_01_canvas.png` | P2 캔버스 — Router 양쪽에 **1 / 99** 번들 수 |
| `p2_07_schedule_on.png` | P2 스케줄 `Daily at 오전 8:00` + 토글 **ON** |
| `common_01_sheets.png` | Sheets — `도구` 열에 Make/n8n 행이 **함께** |

### 프로젝트 1 — Make

| 파일명 | 내용 |
|---|---|
| `make_01_rss_trigger.png` | RSS 트리거 설정 (URL `06.xml`, 반환 건수) |
| `make_02_rss_output.png` | 트리거 출력 번들 — 실측 필드명(`url`/`summary`/`dateCreated`)이 보이게 |
| `make_02b_filter.png` | 노이즈 필터 `본문기사만` 설정 |
| `make_03_normalize.png` | `01_정규화` 변수 7개 |
| `make_04_scoring.png` | `02_스코어링` — `score` 수식(가중 2단)이 보이게 |
| `make_05_router.png` | Router + 양쪽 필터 조건 (`>=2` / `<2`) |
| `make_06_sheets_core.png` | Sheets(CORE) 매핑 |
| `make_07_http_discord_masked.png` | HTTP 모듈 (**URL 마스킹**) |
| `make_08_discord_message.png` | Discord 채널 도착 알림 |
| `make_09_run_once.png` | ★ 캔버스 8 / 34 |
| `make_10_history.png` | History — Operations 135 / 18s / 190.5 KB |
| `make_11_sheets_core_rows.png` | Sheets `CORE` 적재 행 |
| `make_12_sheets_ref_rows.png` | Sheets `REF` 적재 행 |
| `make_13_operations.png` | 오퍼레이션 사용량 427/1,000 |

### 프로젝트 1 — n8n

| 파일명 | 내용 |
|---|---|
| `n8n_01_rss.png` | Schedule Trigger + RSS Read, OUTPUT 50 items |
| `n8n_02_filter.png` | Filter `본문기사만`, Kept 49 items |
| `n8n_03_code.png` | Code 노드 + OUTPUT (`score` 가 number 타입) |
| `n8n_04_if.png` | If 노드 설정 + true 9 / false 40 |
| `n8n_05_http_masked.png` | HTTP Request (**URL 마스킹**) + Batching/Retry 설정 |
| `n8n_06_canvas.png` | ★ 전체 캔버스, 커넥션 item 수 |
| `n8n_07_executions.png` | Executions — ID#17, Succeeded, 12.424s |
| `n8n_08_credentials_masked.png` | 서비스 계정 자격증명 (**Private Key 마스킹**) |

### 프로젝트 2 — Make (DSR-v1)

| 파일명 | 내용 |
|---|---|
| `p2_01_canvas.png` | ★ 캔버스 1 / 99 |
| `p2_02_http_masked.png` | HTTP 모듈 Query String (**`crtfc_key` 마스킹**) |
| `p2_03_iterator.png` | Iterator `{{2.data.list}}` + 출력 100 |
| `p2_04_router_signal.png` | Router 1st route 필터 (Contains OR 4행) |
| `p2_05_router_routine.png` | Router 2nd route 필터 (Does not contain AND 4행) |
| `p2_06_sheets_mapping.png` | Sheets A~H 매핑 |
| `p2_07_schedule_on.png` | ★ 스케줄 + 토글 ON |
| `p2_08_sheets_signal.png` | Sheets `SIGNAL` 적재 행 |
| `p2_09_sheets_routine.png` | Sheets `ROUTINE` 적재 행 |

---

## 없는 캡처는 없다고 쓴다

목록의 캡처를 못 구했으면 **빈칸으로 두거나 다른 화면으로 대체하지 말고**, 이 파일 하단에 "미확보: 파일명 — 사유"로 적는다. 있는 것처럼 링크만 걸어두면 심사에서 즉시 드러난다.
