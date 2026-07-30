# Make 구현 가이드 — TRC-v1 (프로젝트 1)

> 모듈 7개. 계정 생성부터 첫 실행까지 **약 40분**.
> `01_WORKFLOW_SPEC.md`의 계약을 그대로 구현한다. 수식은 복사해서 붙여넣으면 된다.

---

## 0. 사전 준비 (양 도구 공통 — 1회만)

### 0-1. Google Sheets 준비
1. Google Sheets에서 새 스프레드시트 생성 → 이름 `TRC_Research_Log`
2. 시트 탭 2개를 만들고 이름을 정확히 `CORE`, `REF`로 지정
3. **두 시트 모두** 1행에 헤더 입력 (A1부터)

```
수집시각	도구	분류	점수	매칭키워드	제목	요약	발행일	링크
```

### 0-2. Discord Webhook 발급
1. 개인 서버 생성 → 텍스트 채널 `#research-core` 생성
2. 채널 우클릭 → `채널 편집` → `연동` → `웹후크` → `새 웹후크` → **웹후크 URL 복사**
3. 형식: `https://discord.com/api/webhooks/{ID}/{TOKEN}`

> 🔒 **제출물 보안 규칙 (평가 항목 1 마지막 문항)**
> 스크린샷에 이 URL이 절대 보이면 안 된다. 캡처 직후 이미지 편집기로 `{ID}/{TOKEN}` 구간을 검은 사각형으로 덮고 파일명을 `..._masked.png`로 저장하는 습관을 들일 것.
> 문서에 URL을 적을 때는 `https://discord.com/api/webhooks/***MASKED***` 로 표기한다.

### 0-3. Make 계정
- <https://www.make.com> 무료 가입 → 리전은 기본값 유지
- 좌측 `Scenarios` → `Create a new scenario`

---

## 1. 모듈 ① RSS › Watch RSS feed items (Trigger)

| 설정 | 값 |
|---|---|
| App | **RSS** |
| Module | **Watch RSS feed items** |
| URL | `https://rss.etnews.com/Section901.xml` |
| Maximum number of returned feeds | `5` |
| Include only feeds with the following words | (비움) |
| Choose where to start | **`From now on`** — 첫 검증 시에는 `All feed items`로 두고, 검증 후 `From now on`으로 변경 |

**⭐ 여기서 반드시 할 일 — 필드명 실측**
모듈 우클릭 → `Run this module only` → 출력 번들의 실제 키 이름을 확인한다.
아래 표에 실측값을 적어 넣고, 이후 수식의 필드명을 실측값으로 치환한다.

| 규격 필드 | 예상 키 | **실측 키 (직접 기입)** |
|---|---|---|
| 제목 | `title` | |
| 링크 | `url` | |
| 요약 | `summary` | |
| 발행일시 | `dateCreated` | |

📷 **캡처 1** — RSS 모듈 설정 화면
📷 **캡처 2** — `Run this module only` 출력 번들 (필드명이 보이게)

---

## 2. 모듈 ② Tools › Set multiple variables — "01_정규화"

`+` → 검색창에 `Tools` → **Set multiple variables** 선택. 모듈 이름을 `01_정규화`로 변경.
아래 6개 변수를 `Add item`으로 추가한다. (`1.` 은 모듈 ①을 가리킨다)

| Variable name | Variable value |
|---|---|
| `collected_at` | `{{formatDate(now; "YYYY-MM-DD HH:mm"; "Asia/Seoul")}}` |
| `tool` | `Make` |
| `title_clean` | `{{trim(replace(replace(replace(1.title; "/<[^>]*>/g"; " "); "/&[a-zA-Z#0-9]+;/g"; " "); "/\s+/g"; " "))}}` |
| `summary_clean` | `{{substring(trim(replace(replace(replace(1.summary; "/<[^>]*>/g"; " "); "/&[a-zA-Z#0-9]+;/g"; " "); "/\s+/g"; " ")); 0; 200)}}` |
| `title_safe` | `{{trim(replace(replace(replace(1.title; "/<[^>]*>/g"; " "); "/[\x22\x5C\x0A\x0D]/g"; " "); "/\s+/g"; " "))}}` |
| `published_kst` | `{{formatDate(1.dateCreated; "YYYY-MM-DD HH:mm"; "Asia/Seoul")}}` |
| `haystack` | `{{lower(2.title_clean)}} {{lower(2.summary_clean)}}` ← **주의: 아래 설명 참조** |

### ⚠️ `haystack` 처리 — Make의 구조적 제약

**Make의 `Set multiple variables` 모듈 안에서 정의한 변수는 같은 모듈 내의 다른 변수를 참조할 수 없다.** (후속 모듈에서만 참조 가능)
따라서 `haystack`은 모듈 ②에 넣을 수 없고, 두 가지 선택지가 있다.

**선택지 A (권장 — 모듈 수 유지)**: `haystack`을 모듈 ②에 넣되 값을 원본 필드로 직접 조립한다.

```
{{lower(replace(replace(1.title; "/<[^>]*>/g"; " "); "/&[a-zA-Z#0-9]+;/g"; " "))}} {{lower(replace(replace(1.summary; "/<[^>]*>/g"; " "); "/&[a-zA-Z#0-9]+;/g"; " "))}}
```

> 위 값은 **하나의 필드 안에 두 개의 `{{ }}` 표현식을 공백으로 띄워 나란히 넣은 것**이다. Make는 한 필드 안의 인접 표현식을 자동으로 문자열 결합하므로, `+` 연산자 없이 안전하게 연결된다. (Make에서 `+`는 숫자 덧셈으로 해석될 수 있어 문자열 결합에는 쓰지 않는다.)

**선택지 B**: 모듈을 하나 더 추가(`01b_haystack`)해서 `2.title_clean` / `2.summary_clean`을 참조. → 오퍼레이션이 건당 1개 늘어난다(월 +150). 예산상 비권장.

📷 **캡처 3** — 모듈 ② 변수 7개가 모두 보이는 설정 화면

---

## 3. 모듈 ③ Tools › Set multiple variables — "02_스코어링"

모듈 이름 `02_스코어링`. 변수 **2개**만 정의한다. (`2.haystack` = 모듈 ②의 haystack)

### 변수 `matched`
하나의 값 필드에 아래 12개 표현식을 **줄바꿈·공백 없이 연속으로** 붙여 넣는다.

```
{{if(contains(2.haystack; "투자"); "투자,"; "")}}{{if(contains(2.haystack; "인수"); "인수,"; "")}}{{if(contains(2.haystack; "합병"); "합병,"; "")}}{{if(contains(2.haystack; "지분"); "지분,"; "")}}{{if(contains(2.haystack; "상장"); "상장,"; "")}}{{if(contains(2.haystack; "특허"); "특허,"; "")}}{{if(contains(2.haystack; "양산"); "양산,"; "")}}{{if(contains(2.haystack; "출시"); "출시,"; "")}}{{if(contains(2.haystack; "규제"); "규제,"; "")}}{{if(contains(2.haystack; "계약"); "계약,"; "")}}{{if(contains(2.haystack; "수주"); "수주,"; "")}}{{if(contains(2.haystack; "협력"); "협력,"; "")}}
```

### 변수 `score`

```
{{sum(if(contains(2.haystack; "투자");1;0); if(contains(2.haystack; "인수");1;0); if(contains(2.haystack; "합병");1;0); if(contains(2.haystack; "지분");1;0); if(contains(2.haystack; "상장");1;0); if(contains(2.haystack; "특허");1;0); if(contains(2.haystack; "양산");1;0); if(contains(2.haystack; "출시");1;0); if(contains(2.haystack; "규제");1;0); if(contains(2.haystack; "계약");1;0); if(contains(2.haystack; "수주");1;0); if(contains(2.haystack; "협력");1;0))}}
```

> ⚠️ **`add()`가 아니라 `sum()`이다.** Make의 수학 함수 목록에는 `add()`가 없고, 개별 숫자를 나열해 합산하는 함수는 `sum(value1; value2; …)`이다. (공식 함수 목록 확인 결과) — 이 오타 하나로 수식 전체가 실패하므로 주의.

> **`tier` 변수를 만들지 않은 이유**: 같은 모듈 내에서 `score`를 참조할 수 없으므로 `tier` 계산에 `sum(...)` 전체를 한 번 더 써야 한다. 대신 **분기 이후 각 경로에서 `CORE`/`REF`를 리터럴로 기록**하도록 설계했다. 모듈 1개와 월 150 오퍼레이션을 절약하고, 분기 조건과 기록값이 구조적으로 어긋날 수 없게 만드는 효과도 있다.

📷 **캡처 4** — 모듈 ③ 설정 화면 (`score` 수식이 보이게)

---

## 4. 모듈 ④ Router (조건 분기)

모듈 ③ 우측 `+` → `Flow Control` → **Router**. 출력 경로 2개가 생긴다.

### Route A — 필터 이름 `CORE (score>=2)`
Router와 첫 모듈 사이의 렌치 아이콘 클릭 → `Set up a filter`

| 설정 | 값 |
|---|---|
| Label | `CORE (score>=2)` |
| Condition — 좌변 | `{{3.score}}` |
| Operator | **Numeric: Greater than or equal to** |
| 우변 | `2` |

### Route B — 폴백 경로
Route B의 필터 설정 화면에서 **`Fallback route` 체크박스를 켠다.** 조건식은 비워 둔다.

> 🔧 **체크박스가 보이지 않는 경우** (Make UI 버전 차이): 대신 명시적 필터를 쓴다.
> Label `REF (score<2)` / 좌변 `{{3.score}}` / **Numeric: Less than** / 우변 `2`
> 이 경우 유실 방지 효과가 약해지므로, 보고서·인터뷰에서는 **"명시적 필터로 구성했고 MECE는 논리적으로 보장되지만 Fallback route가 있으면 도구 차원의 이중 안전장치가 된다"** 고 정확히 말한다. 없는 기능을 있다고 말하는 것보다 낫다.

> **왜 Route B에 `score < 2` 필터를 쓰지 않고 Fallback을 쓰는가**
> `score >= 2` / `score < 2` 두 필터를 각각 쓰면 논리적으로는 전수이지만, 한쪽 수식에 오타가 나거나 `score`가 예상치 못하게 빈 값이 되면 **양쪽 모두 통과하지 못해 데이터가 조용히 사라진다.** Fallback route는 "앞선 모든 경로가 막혔을 때 반드시 실행"을 도구가 보장하므로 유실 가능성이 구조적으로 0이 된다. (심층 인터뷰 대비 포인트)

📷 **캡처 5** — Router 전체 구조 + Route A 필터 설정
📷 **캡처 6** — Route B의 Fallback route 체크 상태

---

## 5. 모듈 ⑤ (Route A) Google Sheets › Add a Row — CORE

| 설정 | 값 |
|---|---|
| Connection | Google 계정 연결 (`Add` → OAuth 동의) |
| Enter a Spreadsheet ID / Search Method | `Select from My Drive` |
| Spreadsheet | `TRC_Research_Log` |
| Sheet Name | **`CORE`** |
| Table contains headers | `Yes` |

값 매핑:

| 열 | 값 |
|---|---|
| A 수집시각 | `{{2.collected_at}}` |
| B 도구 | `{{2.tool}}` |
| C 분류 | `CORE` ← 리터럴 |
| D 점수 | `{{3.score}}` |
| E 매칭키워드 | `{{replace(3.matched; "/,$/"; "")}}` |
| F 제목 | `{{2.title_clean}}` |
| G 요약 | `{{2.summary_clean}}` |
| H 발행일 | `{{2.published_kst}}` |
| I 링크 | `{{1.url}}` |

📷 **캡처 7** — Sheets(CORE) 매핑 화면

---

## 6. 모듈 ⑥ (Route A) HTTP › Make a request — Discord 알림

모듈 ⑤ 뒤에 연결. App: `HTTP` → Module: **Make a request**

| 설정 | 값 |
|---|---|
| URL | Discord Webhook URL (📌 스크린샷에서 마스킹) |
| Method | `POST` |
| Headers | 추가하지 않음 |
| Body type | **`Raw`** |
| Content type | **`JSON (application/json)`** |
| Parse response | `No` |

Request content:

```
{"content":"🔎 [CORE] {{2.title_safe}}\n· 점수 {{3.score}} / 시그널 {{3.matched}}\n· 발행 {{2.published_kst}} · 수집 {{2.tool}}\n{{1.url}}"}
```

> **`title_clean`이 아니라 `title_safe`를 쓰는 이유** — 계약 N5.
> 제목에 ASCII 큰따옴표(`"`)가 들어오면 위 JSON이 깨져 400 에러가 난다. 실제로 언론사 제목은 큰따옴표 인용을 자주 쓴다. `title_safe`는 `[\x22\x5C\x0A\x0D]`(큰따옴표·백슬래시·개행)를 제거한 값이다. 정규식에 `\x22`(16진 이스케이프)를 쓴 것도 **수식 문자열 안에 큰따옴표를 중첩시키지 않기 위한 의도적 선택**이다.
>
> 🔧 **그래도 400 에러가 나면**: `JSON › Create JSON` 모듈을 앞에 끼워 넣고 `content` 필드를 데이터 구조로 정의한 뒤, HTTP 모듈의 Request content에 `{{6.json}}`을 매핑한다. Create JSON은 이스케이프를 자동 처리한다. (오퍼레이션 CORE 건수만큼 추가)

📷 **캡처 8** — HTTP 모듈 설정 (URL 마스킹 필수)
📷 **캡처 9** — Discord 채널에 도착한 실제 알림 메시지

---

## 7. 모듈 ⑦ (Route B) Google Sheets › Add a Row — REF

모듈 ⑤와 동일. **두 곳만 다르다.**

| 설정 | 값 |
|---|---|
| Sheet Name | **`REF`** |
| C 분류 | `REF` ← 리터럴 |

📷 **캡처 10** — Sheets(REF) 매핑 화면

---

## 8. 스케줄 설정 및 실행

### 8-1. 스케줄
좌측 하단 시계 아이콘 → `Every day` → `08:00`
(계약 ①: 1일 1회 08:00 KST. Make 무료 최소 인터벌은 15분이지만 오퍼레이션 예산상 1일 1회)

### 8-2. 검증 실행
1. 하단 `Run once` 클릭
2. 각 모듈 위 버블 숫자를 확인 — 처리된 번들 수가 보인다
3. **Route A와 Route B 양쪽 모두 번들이 1개 이상 지나갔는지 확인** (평가 항목 1의 필수 조건)
4. 좌측 `History` → 실행 레코드 클릭 → 모듈별 입출력 데이터 확인

📷 **캡처 11** — `Run once` 직후 전체 시나리오 (양쪽 경로에 번들 숫자가 보이는 상태) ← **가장 중요한 스크린샷**
📷 **캡처 12** — History 상세 (모듈 ③의 output에 `score`, `matched` 값이 보이게)
📷 **캡처 13** — Google Sheets `CORE` 시트에 적재된 행
📷 **캡처 14** — Google Sheets `REF` 시트에 적재된 행

### 8-3. 분기 커버리지가 한쪽만 나온 경우
평가 항목 1은 "각 분기 경로가 실제로 1회 이상 실행된 결과"를 요구한다. 아래 순서로 해결한다.

| 상황 | 조치 | 정당성 |
|---|---|---|
| REF만 나옴 (CORE 0건) | `Maximum number of returned feeds`를 5 → 10으로 올려 재실행 | 표본 확대. 계약 변경 아님 |
| CORE만 나옴 (REF 0건) | 동일하게 표본 확대 | 동일 |
| 여전히 한쪽 0건 | 시간대를 바꿔(예: 주말 오전) 재실행 | 피드 구성 변화 활용 |
| 그래도 안 되면 | **키워드 사전이나 θ를 바꾸지 말고**, 별도 테스트 피드(예: `https://techcrunch.com/feed/`)로 1회 실행한 결과를 보조 증빙으로 첨부 | 계약을 훼손하지 않고 분기 로직의 양방향 동작만 증명 |

> ❌ **하지 말 것**: θ를 임시로 1로 바꿨다가 되돌리기. 스크린샷의 임계값과 보고서의 임계값이 달라져 심사에서 즉시 지적된다.

### 8-4. 오퍼레이션 사용량 확인
좌측 하단 프로필 → `Organization` → 이번 달 사용량 확인.
📷 **캡처 15** — 오퍼레이션 사용량 (보고서 §5 정량 비교의 근거)

---

## 9. 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| RSS 모듈이 0 bundle 반환 | `From now on` 설정 + 신규 항목 없음 | `Choose where to start` → `All feed items`로 변경 후 재실행 |
| `formatDate` 결과가 9시간 어긋남 | 3번째 인자(타임존) 누락 | `; "Asia/Seoul"` 추가 |
| `score`가 항상 0 | `haystack`이 빈 값 / 모듈 번호 오참조 | History에서 모듈 ② output의 `haystack` 실제 값 확인 |
| `score`가 텍스트로 취급됨 | Router 필터에서 Text 연산자 선택 | Operator를 **Numeric: Greater than or equal to**로 변경 |
| Discord 400 Bad Request | JSON 페이로드 파손 | §6의 `JSON › Create JSON` 대안 적용 |
| Discord 204 인데 메시지 안 옴 | Webhook이 다른 채널을 가리킴 | Webhook URL 재발급 |
| `Add a Row`가 헤더 행을 덮어씀 | `Table contains headers` = No | `Yes`로 변경 |
