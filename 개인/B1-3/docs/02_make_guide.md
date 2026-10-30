# Make 구현 가이드 — TRC-v2 (프로젝트 1) · As-Built

> 모듈 7개 + 필터 2개. 계정 생성부터 첫 실행까지 **실측 약 30분**.
> `01_WORKFLOW_SPEC.md`의 계약을 그대로 구현한다. 수식은 복사해서 붙여넣으면 된다.
> ⚠️ 이 문서는 **실제로 만들어 돌린 설정값**이다. 초기 설계에서 틀렸던 부분은 그대로 두지 않고 교정된 값만 적었다(폐기 이력은 명세서 §8).

---

## 0. 사전 준비 (양 도구 공통 — 1회만)

### 0-1. Google Sheets

1. 새 스프레드시트 → 이름 `TRC_Research_Log`
2. 시트 탭 2개를 만들고 이름을 정확히 `CORE`, `REF` 로 지정
3. **두 시트 모두** 1행에 헤더 입력 (A1부터)

```
수집시각	도구	분류	점수	매칭키워드	제목	요약	발행일	링크
```

### 0-2. Discord Webhook

1. 개인 서버 → 텍스트 채널 `#research-core` 생성
2. 채널 우클릭 → `채널 편집` → `연동` → `웹후크` → `새 웹후크` → URL 복사
3. 형식: `https://discord.com/api/webhooks/{ID}/{TOKEN}`

> 🔒 **제출물 보안 규칙** — 캡처 직후 `{ID}/{TOKEN}` 구간을 검은 박스로 덮고 파일명을 `..._masked.png` 로 저장한다. 문서에는 `https://discord.com/api/webhooks/***MASKED***` 로 표기.

### 0-3. Make 계정

<https://www.make.com> 무료 가입 → `Scenarios` → `Create a new scenario`

---

## 1. 모듈 ② RSS › Watch RSS feed items (Trigger)

| 설정 | 값 |
|---|---|
| App / Module | **RSS** / **Watch RSS feed items** |
| URL | `https://rss.etnews.com/06.xml` ← **전자 섹션** |
| Maximum number of returned feeds | 검증 시 `50` / 운영 시 `5` |
| Choose where to start | 검증 시 `All feed items` → 검증 후 `From now on` |

**⭐ 실측 확정 필드명** (`Run this module only` 로 확인함)

| 규격 필드 | Make 실측 키 |
|---|---|
| 제목 | `title` |
| 링크 | **`url`** |
| 요약 | **`summary`** |
| 발행일시 | **`dateCreated`** |

> `Choose where to start = All feed items` 는 **가장 오래된 항목부터** 반환한다. 초기에 5건으로 두었더니 `[포토]` 사진 캡션만 5건 들어왔다. 검증 시에는 50건으로 넓힌다.

📷 **캡처 make_01** — RSS 모듈 설정 / **make_02** — 출력 번들(필드명이 보이게)

---

## 2. 필터 `본문기사만` (모듈 ② → ③ 사이)

트리거와 다음 모듈 사이 렌치 아이콘 → `Set up a filter`

| 설정 | 값 |
|---|---|
| Label | `본문기사만` |
| 좌변 | `{{2.title}}` |
| Operator | **Text: Does not contain** |
| 우변 | `[포토]` |

**실측: 50건 중 8건 차단(16%), 42건 통과.** 차단된 번들은 하위 모듈 오퍼레이션을 전혀 소모하지 않는다 → 회당 24 op(15%) 절감.

📷 **캡처 make_02b** — 필터 설정 + 실행 로그의 "did not pass through the filter" 라인

---

## 3. 모듈 ③ Tools › Set multiple variables — `01_정규화`

`+` → `Tools` → **Set multiple variables**. 모듈 이름 `01_정규화`. 변수 **7개**.

| Variable name | Variable value |
|---|---|
| `collected_at` | `{{formatDate(now; "YYYY-MM-DD HH:mm"; "Asia/Seoul")}}` |
| `tool` | `Make` |
| `title_clean` | `{{trim(replace(replace(replace(2.title; "/<[^>]*>/g"; " "); "/&[a-zA-Z#0-9]+;/g"; " "); "/\s+/g"; " "))}}` |
| `summary_clean` | `{{substring(trim(replace(replace(replace(2.summary; "/<[^>]*>/g"; " "); "/&[a-zA-Z#0-9]+;/g"; " "); "/\s+/g"; " ")); 0; 200)}}` |
| `title_safe` | `{{trim(replace(replace(replace(2.title; "/<[^>]*>/g"; " "); "/[\x22\x5C\x0A\x0D]/g"; " "); "/\s+/g"; " "))}}` |
| `published_kst` | `{{formatDate(2.dateCreated; "YYYY-MM-DD HH:mm"; "Asia/Seoul")}}` |
| `haystack` | 아래 참조 |

### ⚠️ `haystack` — Make의 구조적 제약

**같은 `Set multiple variables` 모듈 안에서 정의한 변수는 서로를 참조할 수 없다.** 그래서 `haystack` 은 `title_clean` 을 못 쓰고 원본 필드로 다시 조립한다.

```
{{lower(replace(replace(2.title; "/<[^>]*>/g"; " "); "/&[a-zA-Z#0-9]+;/g"; " "))}} {{lower(replace(replace(2.summary; "/<[^>]*>/g"; " "); "/&[a-zA-Z#0-9]+;/g"; " "))}}
```

> 위 값은 **하나의 필드 안에 `{{ }}` 표현식 2개를 공백으로 띄워 나란히** 넣은 것이다. Make는 인접 표현식을 자동 결합하므로 `+` 없이 안전하게 연결된다. (Make에서 `+`는 숫자 덧셈으로 해석될 수 있어 문자열 결합에 쓰지 않는다.)

📷 **캡처 make_03** — 변수 7개가 보이는 설정 화면

---

## 4. 모듈 ⑥ Tools › Set multiple variables — `02_스코어링`

모듈 이름 `02_스코어링`. 변수 **2개**. (`3.haystack` = 모듈 ③)

### 변수 `matched`

12개 표현식을 **줄바꿈·공백 없이 연속으로** 붙여 넣는다.

```
{{if(contains(3.haystack;"투자");"투자,";"")}}{{if(contains(3.haystack;"인수");"인수,";"")}}{{if(contains(3.haystack;"배당");"배당,";"")}}{{if(contains(3.haystack;"특허");"특허,";"")}}{{if(contains(3.haystack;"양산");"양산,";"")}}{{if(contains(3.haystack;"수주");"수주,";"")}}{{if(contains(3.haystack;"개발");"개발,";"")}}{{if(contains(3.haystack;"출시");"출시,";"")}}{{if(contains(3.haystack;"공급");"공급,";"")}}{{if(contains(3.haystack;"진출");"진출,";"")}}{{if(contains(3.haystack;"제휴");"제휴,";"")}}{{if(contains(3.haystack;"확대");"확대,";"")}}
```

### 변수 `score` — 가중 2단 (T1 = 2점 / T2 = 1점)

```
{{sum(if(contains(3.haystack;"투자");2;0); if(contains(3.haystack;"인수");2;0); if(contains(3.haystack;"배당");2;0); if(contains(3.haystack;"특허");2;0); if(contains(3.haystack;"양산");2;0); if(contains(3.haystack;"수주");2;0); if(contains(3.haystack;"개발");1;0); if(contains(3.haystack;"출시");1;0); if(contains(3.haystack;"공급");1;0); if(contains(3.haystack;"진출");1;0); if(contains(3.haystack;"제휴");1;0); if(contains(3.haystack;"확대");1;0))}}
```

> ⚠️ **`add()` 가 아니라 `sum()` 이다.** Make 수학 함수 목록에 `add()` 는 없다. 잘못된 함수명은 **에러 없이 빈 값**을 만들고, 그러면 분기가 항상 한쪽으로만 흐른다.
> **`tier` 변수를 만들지 않은 이유**: 같은 모듈에서 `score` 를 참조할 수 없어 `sum(...)` 전체를 한 번 더 써야 한다. 대신 **경로별로 `CORE`/`REF` 를 리터럴로 기록**한다 — 모듈 1개와 월 150 op 를 아끼고, 분기 조건과 기록값이 구조적으로 어긋날 수 없게 만든다.

📷 **캡처 make_04** — `score` 수식이 보이는 설정 화면

---

## 5. 모듈 ⑩ Router — 조건 분기 ★

`Flow Control` → **Router**. 출력 경로 2개.

### Route A — `CORE (score>=2)`

| 설정 | 값 |
|---|---|
| 좌변 | `{{6.score}}` |
| Operator | **Numeric: Greater than or equal to** |
| 우변 | `2` |

### Route B — `REF (score<2)`

| 설정 | 값 |
|---|---|
| 좌변 | `{{6.score}}` |
| Operator | **Numeric: Less than** |
| 우변 | `2` |

### ❌ `Fallback route` 를 쓰지 말 것 — 실측 사고 기록

처음에 Route B를 `Fallback route` 로 두었다. 결과는:

```
필터 통과 42건 → CORE 8건만 처리, 34건이 어느 시트에도 기록되지 않음
실행 상태: 오류 없음, "성공"
```

**조용한 유실이었다.** 명시적 조건 `score < 2` 로 교체하니 34건이 정상 흘렀다.
→ **분기를 만들면 반드시 `CORE + REF = 필터 통과 건수` 등식을 확인한다.**

📷 **캡처 make_05** — Router 구조 + 양쪽 필터 조건

---

## 6. 모듈 ⑪ (Route A) Google Sheets › Add a Row — CORE

| 설정 | 값 |
|---|---|
| Connection | Google 계정 OAuth 동의 |
| Search Method | `Select from My Drive` |
| Spreadsheet | `TRC_Research_Log` |
| Sheet Name | **`CORE`** |
| Table contains headers | `Yes` |

| 열 | 값 |
|---|---|
| A 수집시각 | `{{3.collected_at}}` |
| B 도구 | `{{3.tool}}` |
| C 분류 | `CORE` ← 리터럴 |
| D 점수 | `{{6.score}}` |
| E 매칭키워드 | `{{replace(6.matched; "/,$/"; "")}}` |
| F 제목 | `{{3.title_clean}}` |
| G 요약 | `{{3.summary_clean}}` |
| H 발행일 | `{{3.published_kst}}` |
| I 링크 | `{{2.url}}` |

> ⚠️ **E열의 `replace(...; "/,$/"; "")` 는 실측에서 동작하지 않았다.** 시트에는 `출시,확대,` 처럼 후행 쉼표가 남는다. n8n(`Array.join(',')`)과의 유일한 표기 불일치이며, 보고서 §4.3에 그대로 기록했다. 원인은 미규명.

📷 **캡처 make_06** — Sheets(CORE) 매핑

---

## 7. 모듈 ⑬ (Route A) HTTP › Make a request — Discord 알림

모듈 ⑪ 뒤에 연결.

| 설정 | 값 |
|---|---|
| URL | Discord Webhook URL (📌 마스킹) |
| Method | `POST` |
| **Body type** | **`Application/JSON`** |
| **Body input method** | **`Data structure`** ← Raw 옵션이 없는 UI 버전 |
| Parse response | `No` |

`Data structure` → `Add` → 필드 1개 정의: name `content`, type `Text`.
`content` 값:

```
[CORE] {{3.title_safe}}
· 점수 {{6.score}} / 시그널 {{6.matched}}
· 발행 {{3.published_kst}} · 수집 {{3.tool}}
{{2.url}}
```

> **`title_clean` 이 아니라 `title_safe` 를 쓰는 이유 — 계약 N5.** 언론사 제목은 큰따옴표 인용을 자주 쓰고, 그대로 JSON에 넣으면 페이로드가 깨져 400이 난다. `title_safe` 는 `[\x22\x5C\x0A\x0D]` 를 제거한 값이다. 정규식에 16진 이스케이프(`\x22`)를 쓴 것도 **수식 문자열 안에 큰따옴표를 중첩시키지 않기 위한 의도적 선택**이다.
> `Data structure` 방식은 직렬화를 Make가 처리하므로 이스케이프가 자동이다. 그럼에도 N5를 적용하는 것은 **두 도구의 알림 본문을 바이트 단위로 맞추기 위해서**다.

📷 **캡처 make_07** — HTTP 모듈 설정 (URL 마스킹) / **make_08** — Discord 채널 도착 메시지

---

## 8. 모듈 ⑫ (Route B) Google Sheets › Add a Row — REF

모듈 ⑪과 동일. **두 곳만 다르다.**

| 설정 | 값 |
|---|---|
| Sheet Name | **`REF`** |
| C 분류 | `REF` ← 리터럴 |

---

## 9. 스케줄 · 실행 · 검증

### 9-1. 스케줄
좌측 하단 시계 아이콘 → `Every day` → `08:00` → 시나리오 토글 `ON`

### 9-2. 검증 실행 (`Run once`)

실측 결과 (2026-07-30 12:52):

```
RSS 50 → 필터 42(8 차단) → 스코어링 42
Router → CORE 8 → Sheets 8 → Discord 8
       → REF  34 → Sheets 34
8 + 34 = 42 ✅
Operations 135 / Duration 18s / Data 190.5 KB
```

📷 **캡처 make_09** — `Run once` 직후 캔버스 (양쪽 경로 번들 수) ← **가장 중요**
📷 **캡처 make_10** — History 상세 (Operations 135 / Duration / Data size)
📷 **캡처 make_11** — Sheets `CORE` 적재 행 / **make_12** — `REF` 적재 행

### 9-3. 분기 한쪽이 0건일 때

| 상황 | 조치 | 정당성 |
|---|---|---|
| 한쪽 0건 | `Maximum number of returned feeds` 를 5 → 50으로 확대 후 재실행 | 표본 확대. 계약 변경 아님 |
| 여전히 0건 | 다른 시간대에 재실행 | 피드 구성 변화 활용 |

> ❌ **하지 말 것**: θ를 임시로 1로 바꿨다가 되돌리기. 캡처의 임계값과 보고서의 임계값이 달라져 즉시 지적된다.

### 9-4. 오퍼레이션 사용량
좌측 하단 프로필 → `Organization` → 이번 달 사용량. 실측 **427 / 1,000 (43%)**.

📷 **캡처 make_13** — 오퍼레이션 사용량

---

## 10. 트러블슈팅 (실제로 겪은 것만)

| 증상 | 원인 | 조치 |
|---|---|---|
| 트리거가 `[포토]` 기사만 반환 | `All feed items` 는 **가장 오래된 항목부터** 반환 | 반환 건수를 50으로 확대 + 노이즈 필터 |
| `score` 가 전부 빈 값 | `add()` 사용 | `sum()` 으로 교체 |
| 수식이 저장되는데 값이 안 나옴 | 같은 모듈 내 변수 상호 참조 | 모듈 분리 |
| 문자열 결합이 이상한 숫자가 됨 | `+` 사용 | 표현식 인접 배치 |
| Router 한쪽만 처리되고 나머지가 사라짐 | `Fallback route` | 명시적 조건으로 교체 + 검증 등식 확인 |
| 필터를 고쳤는데 캔버스 뱃지가 그대로 | 캔버스 뱃지는 **직전 실행의 잔상** | 저장 후 재실행하면 갱신됨 |
| Discord 400 | JSON 페이로드 파손 | `Data structure` 방식 + `title_safe` |
| `formatDate` 결과가 9시간 어긋남 | 타임존 인자 누락 | `; "Asia/Seoul"` 추가 |
| `Add a Row` 가 헤더를 덮어씀 | `Table contains headers = No` | `Yes` 로 변경 |
