# n8n 구현 가이드 — TRC-v2 (프로젝트 1) · As-Built

> n8n **Community Edition v2.32.6**, `npx` 로컬 셀프호스팅. 노드 8개.
> 설치부터 첫 실행까지 **실측 약 90분** — 그중 약 55분이 런타임 설치와 Google 자격증명 발급이었다.

---

## 0. 설치

### 0-1. Node.js

```powershell
winget install OpenJS.NodeJS.LTS
```

> ⚠️ **MSI 설치 파일은 실패했다.** Windows Installer DLL 오류(VBScript 지원 제거 관련)로 진행되지 않았다. `winget` 으로 우회하면 정상 설치된다.

### 0-2. n8n 실행

```powershell
npx.cmd n8n
```

> ⚠️ **`npx n8n` 은 PowerShell 실행 정책에 막힌다** (`npx.ps1` 스크립트 차단). `npx.cmd` 를 쓰거나
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 로 정책을 완화한다.

브라우저에서 <http://localhost:5678> → 로컬 계정 생성.

### 0-3. 타임존 (중요)

n8n 인스턴스 기본 타임존은 **America/New_York** 이다.
워크플로우 우측 상단 `…` → `Settings` → `Timezone` → **`Asia/Seoul`**

> 다만 계약 N6에서 **Code 노드 안에 타임존을 하드코딩**해 두었기 때문에, 이 설정을 놓쳤더라도 시트에 적재된 값 자체는 무사했다. **"환경 설정에 의존하지 않는 값 생성"이 계약 N6의 실질적 효용**이다.

---

## 1. Google Sheets 자격증명 — 서비스 계정

Make의 OAuth 클릭 동의와 달리, n8n은 자격증명을 직접 발급해야 한다. **실측 약 30분.**

1. <https://console.cloud.google.com> → 새 프로젝트 생성
2. `API 및 서비스` → `라이브러리` → **Google Sheets API** 사용 설정
3. `사용자 인증 정보` → `사용자 인증 정보 만들기` → **서비스 계정**
4. 서비스 계정 생성 후 → `키` 탭 → `키 추가` → `새 키 만들기` → **JSON** → 파일 다운로드
5. JSON 파일에서 두 값을 꺼낸다
   - `client_email` → n8n `Service Account Email`
   - `private_key` → n8n `Private Key` (`-----BEGIN PRIVATE KEY-----` 부터 끝까지 전부)
6. **Google Sheets 문서를 `client_email` 주소와 공유** (편집자 권한) ← **이 단계를 빼면 403**

> 🔒 다운로드한 JSON 키 파일은 **저장소에 절대 커밋하지 않는다.** `.gitignore` 가 `*service-account*.json` / `*credentials*.json` / `*.pem` / `*.key` 를 차단한다.
> 📌 n8n Credentials 캡처 시 Private Key 필드는 반드시 마스킹.

### 서비스 계정 = 독립된 제3의 주체

| | Make (OAuth 위임) | n8n (서비스 계정) |
|---|---|---|
| 권한 모델 | 사용자를 대신해 행동 | **별도의 주체** |
| 리소스 접근 | 사용자 권한 그대로 | **리소스마다 개별 공유 필요** |
| 파일 목록 | 즉시 브라우징 | **403** — Drive 열람 권한 없음 |

→ Sheets 노드에서 `From list` 대신 **`By URL`** 을 쓴다. 시트 1개만 공유했으니 목록을 못 보는 것이 **정상 동작**이다(최소 권한의 대가).

---

## 2. 노드 구성 (8개)

```
① Schedule Trigger → ② RSS Read → ③ Filter → ④ Code → ⑤ If ┬ true  → ⑥ Sheets(CORE) → ⑦ HTTP(Discord)
                                                              └ false → ⑧ Sheets(REF)
```

### ① Schedule Trigger
`Trigger Interval` = `Days`, `Trigger at Hour` = `8`, `Minute` = `0`

### ② RSS Read
| 설정 | 값 |
|---|---|
| URL | `https://rss.etnews.com/06.xml` |

**실측 확정 필드명** — Make와 다르다.

| 규격 필드 | n8n 실측 키 |
|---|---|
| 제목 | `title` |
| 링크 | **`link`** |
| 요약 | **`contentSnippet`** (fallback `content`) |
| 발행일시 | **`isoDate`** (fallback `pubDate`) |

> `RSS Read` 는 **Action이라 상태가 없다.** 매 실행마다 전량(50건)을 반환한다. 운영에 넣으려면 `Remove Duplicates`(Compare to previous execution) 노드가 필요하다. 이번에는 채점용 증빙(49건) 확보가 목적이라 의도적으로 이 조합을 썼다. → 명세서 계약 ⑤

📷 **캡처 n8n_01** — Schedule + RSS Read, OUTPUT 50 items

### ③ Filter — `본문기사만`
| 설정 | 값 |
|---|---|
| 좌변 | `{{ $json.title }}` |
| Operator | String › **does not contain** |
| 우변 | `[포토]` |

**실측: 50 → 49 (1건 차단).** 커넥션에 `Kept 49 items` 로 표시된다.

📷 **캡처 n8n_02** — Filter 설정 + Kept 49 items

### ④ Code — 정규화 + 스코어링 + tier 판정 (통합)

`Mode` = **`Run Once for All Items`**

```javascript
const SIGNAL_T1 = ['투자', '인수', '배당', '특허', '양산', '수주']; // 2점
const SIGNAL_T2 = ['개발', '출시', '공급', '진출', '제휴', '확대']; // 1점
const THRESHOLD = 2;
const TOOL = 'n8n';

const stripTags = (s = '') =>
  String(s).replace(/<[^>]*>/g, ' ').replace(/&[a-zA-Z#0-9]+;/g, ' ').replace(/\s+/g, ' ').trim();

const jsonSafe = (s = '') =>
  String(s).replace(/["\\\r\n]/g, ' ').replace(/\s+/g, ' ').trim();

const kst = (d) => {
  const dt = d ? new Date(d) : new Date();
  if (isNaN(dt.getTime())) return '';
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(dt).replace('T', ' ');
};

const out = [];
for (const item of $input.all()) {
  const j = item.json;
  const title = stripTags(j.title);
  const summary = stripTags(j.contentSnippet || j.content || j.description || '').slice(0, 200);
  const hay = (title + ' ' + summary).toLowerCase();

  const hit1 = SIGNAL_T1.filter((w) => hay.includes(w));
  const hit2 = SIGNAL_T2.filter((w) => hay.includes(w));
  const score = hit1.length * 2 + hit2.length;

  out.push({ json: {
    collected_at: kst(),
    tool: TOOL,
    tier: score >= THRESHOLD ? 'CORE' : 'REF',
    score,
    matched_keywords: [...hit1, ...hit2].join(','),
    title,
    title_safe: jsonSafe(title),
    summary,
    published_at: kst(j.isoDate || j.pubDate),
    link: j.link || '',
  }});
}
return out;
```

> **Make는 이 로직에 400자 수식 2개와 모듈 2개가 필요했고, n8n은 배열 2개와 `filter()` 2줄이다.** 키워드 1개 추가 시 Make는 수식 2곳을 고쳐야 하고 n8n은 배열에 문자열 1개를 넣는다. → 비교 항목 ⑦
> **타임존을 `Asia/Seoul` 로 하드코딩**한 것이 계약 N6이다. 인스턴스 설정에 의존하지 않는다.

📷 **캡처 n8n_03** — Code 노드 + OUTPUT (`score` 가 `#`(number) 타입인지 Schema 뷰로 확인)

### ⑤ If — 조건 분기 ★

| 설정 | 값 |
|---|---|
| 좌변 | `{{ $json.score }}` |
| 타입 | **Number** |
| Operator | **is greater than or equal to** |
| 우변 | `2` |

### ❌ Switch 노드를 쓰지 말 것 — 실측 사고 기록

처음에 `Switch` 노드에 규칙 2개(`tier` 문자 비교)를 넣었다. 결과:

```
필터 통과 49건 → REF 40건만 처리, CORE 9건 소실
실행 상태: 오류 없음, "Workflow executed successfully"
```

원인은 **규칙 1의 우변만 `Expression` 모드였고 규칙 2는 `Fixed`** 였던 것. UI에서는 두 규칙이 똑같아 보였다.

**If 노드로 교체한 이유**는 출력이 `true`/`false` 2개뿐이라 **MECE가 선언이 아니라 구조로 보장**되기 때문이다. 규칙을 몇 개 쓰든 "어디에도 안 걸리는 아이템"이 원리적으로 존재할 수 없다.

📷 **캡처 n8n_04** — If 노드 설정 + true 9 / false 40 분기

### ⑥ Google Sheets › Append Row — CORE

| 설정 | 값 |
|---|---|
| Credential | 서비스 계정 |
| Resource / Operation | `Sheet Within Document` / `Append Row` |
| Document | **`By URL`** ← `From list` 는 403 |
| Sheet | `CORE` |
| Mapping Column Mode | `Map Each Column Manually` |

| 열 | 값 |
|---|---|
| 수집시각 | `{{ $json.collected_at }}` |
| 도구 | `{{ $json.tool }}` |
| 분류 | `CORE` |
| 점수 | `{{ $json.score }}` |
| 매칭키워드 | `{{ $json.matched_keywords }}` |
| 제목 | `{{ $json.title }}` |
| 요약 | `{{ $json.summary }}` |
| 발행일 | `{{ $json.published_at }}` |
| 링크 | `{{ $json.link }}` |

### ⑦ HTTP Request — Discord 알림

| 설정 | 값 |
|---|---|
| Method / URL | `POST` / Discord Webhook (📌 마스킹) |
| Send Body | `ON` |
| Body Content Type | `JSON` |
| Specify Body | **`Using Fields Below`** ← 직렬화를 도구에 위임 |
| Body Parameter — Name | `content` |
| Body Parameter — Value | 아래 |

```
[CORE] {{ $json.title_safe }}
· 점수 {{ $json.score }} / 시그널 {{ $json.matched_keywords }}
· 발행 {{ $json.published_at }} · 수집 {{ $json.tool }}
{{ $json.link }}
```

**노드 Settings 필수 설정 — 429 대응**

| 설정 | 값 |
|---|---|
| Batching → Items per Batch | `1` |
| Batching → Batch Interval (ms) | `1500` |
| Retry On Fail | `ON` |
| Max Tries / Wait Between Tries | `3` / `2000` |

> ⚠️ **n8n에서 Discord 429 Rate Limited 가 발생했다.** Make에서는 같은 알림 8건이 문제없었는데 n8n에서 9건이 막혔다. 원인은 **병렬성 차이** — n8n이 더 빠르게 몰아친다.
> **"같은 워크플로우인데 한쪽만 외부 API에 막힌다"** 는 것이 도구 특성의 실질적 차이다. 성능이 좋은 것이 항상 유리하지 않다.

📷 **캡처 n8n_05** — HTTP Request 설정 (URL 마스킹) + Settings의 Batching/Retry

### ⑧ Google Sheets › Append Row — REF

⑥과 동일. `Sheet` = `REF`, `분류` = `REF`.

---

## 3. 실행 및 검증

`Execute Workflow` → 우측 상단 `Executions` 탭에서 기록 확인.

실측 (2026-07-30 17:20:42, **Execution ID #17**):

```
RSS 50 → Filter 49 (1 차단) → Code 49
If → true(CORE)  9 → Sheets 9 → Discord 9
   → false(REF) 40 → Sheets 40
9 + 40 = 49 ✅ 유실 0
Duration 12.424s / Data 127 KB / 실행 과금 0
```

📷 **캡처 n8n_06** — 전체 캔버스 + 각 커넥션의 item 수 ← **가장 중요**
📷 **캡처 n8n_07** — Executions 목록 (ID#17, Succeeded, 12.424s)

---

## 4. 트러블슈팅 (실제로 겪은 것만)

| # | 증상 | 원인 | 조치 |
|---|---|---|---|
| 1 | Node.js MSI 설치 실패 | Windows Installer DLL / VBScript 지원 제거 | `winget install OpenJS.NodeJS.LTS` |
| 2 | `npx n8n` 실행 거부 | PowerShell 실행 정책이 `npx.ps1` 차단 | `npx.cmd n8n` |
| 3 | 시각이 미국 시간 | 인스턴스 타임존 `America/New_York` | 워크플로우 Settings → `Asia/Seoul` (+ Code 내 하드코딩) |
| 4 | Sheets 문서 목록 403 | Drive API 미활성 + 서비스 계정에 Drive 권한 없음 | `From list` → **`By URL`** |
| 5 | Sheets 쓰기 403 | 시트를 서비스 계정 이메일과 공유하지 않음 | 시트 공유(편집자) |
| 6 | Switch가 9건을 삼킴 | 규칙 우변의 Fixed/Expression 모드 불일치 | **If 노드로 교체** |
| 7 | `score` 비교가 항상 false | `score` 가 문자열로 전달 | Code OUTPUT Schema에서 `#`(number) 확인 |
| 8 | Discord 429 Rate Limited | 병렬 전송 | Batching 1건/1.5초 + Retry On Fail |
| 9 | 매 실행마다 시트 중복 적재 | `RSS Read` 는 상태가 없음 | 운영 시 `Remove Duplicates` 추가 |

> **환경 문제(1·2·3·4·5)는 시끄럽고, 로직 문제(6·7)는 조용하다.** 환경 오류는 즉시 빨간 에러로 멈추지만, 분기 유실은 "성공"으로 표시된다. **디버깅 시간을 어디에 배분해야 하는지를 이 대비가 알려준다.**

---

## 5. 저장소의 `workflows/n8n_TRC_v2.json` 에 대하여

import 가능한 구조 파일이지만 `YOUR_SPREADSHEET_URL_HERE` / `YOUR_DISCORD_WEBHOOK_URL_HERE` 는 **의도된 자리표시자**다. 실제 Webhook URL과 문서 ID를 공개 저장소에 커밋하는 것 자체가 민감정보 노출이므로, 실행 증빙은 JSON이 아니라 **마스킹된 스크린샷**으로 제출한다.
import 후 두 값과 Google 자격증명만 채우면 동작한다.
