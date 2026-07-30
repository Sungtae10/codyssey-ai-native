# n8n 구현 가이드 — TRC-v1 (프로젝트 1)

> 노드 6개. n8n 설치부터 첫 실행까지 **약 50분** (Google 인증 설정이 대부분).
> `01_WORKFLOW_SPEC.md`의 동일 계약을 구현한다. Make 구현체와 결과가 바이트 단위로 같아야 한다.

---

## 0. n8n 설치 — 3가지 경로 비교

| 방식 | 명령 | 비용 | 장점 | 단점 |
|---|---|---|---|---|
| **A. npx (권장)** | `npx n8n` | 무료·무제한 | 설치 1줄, Node.js만 있으면 됨 | 터미널을 닫으면 정지 |
| B. Docker | `docker run -it --rm -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n` | 무료·무제한 | 데이터 볼륨 영속, 환경 격리 | Docker Desktop 설치 필요 |
| C. n8n Cloud | 가입만 | **14일 무료 트라이얼 후 유료** | 24/7 가동, 설치 불필요 | 트라이얼 종료 후 과금 |

**A 또는 B를 선택한다.** 과제 제약("무료 플랜으로 완수 가능한 조합을 우선 고려")을 충족하는 것은 **셀프호스팅(Community Edition)** 이고, Community Edition은 워크플로우·실행 횟수 제한이 없다. (제외되는 것은 SSO / 로그 스트리밍 / 외부 시크릿 / Git 버전관리 / 프로젝트·RBAC 등 엔터프라이즈 기능이며, 이번 과제 요구사항과는 무관하다.)

### 0-1. npx 설치 절차

```bash
node -v          # v20 이상이어야 한다 (권장 v22)
npx n8n
```

첫 실행 시 패키지를 내려받아 5분 정도 걸린다. 완료되면 아래가 출력된다.

```
Editor is now accessible via: http://localhost:5678/
```

브라우저에서 `http://localhost:5678` 접속 → 로컬 소유자 계정(이메일/비밀번호) 생성.

> 💡 **선택**: 인스턴스를 이메일로 등록하면 Community Edition에서 폴더·디버그 도구·실행 데이터 커스텀 기능이 추가로 해금된다. 과제 필수는 아니다.

📷 **캡처 1** — n8n 버전 정보 화면 (`Settings` → 하단 버전 표기) + 실행 중인 터미널

---

## 1. Google Sheets 자격증명 — 서비스 계정 방식 (권장)

셀프호스팅 n8n에서 Google OAuth를 쓰려면 GCP 프로젝트 + OAuth 동의화면 + 리디렉트 URI 등록이 필요하다.
**Google Sheets만 쓴다면 서비스 계정이 훨씬 짧다.** (Gmail은 서비스 계정으로 불가 — 도메인 전체 위임이 필요하고 개인 Gmail에는 적용할 수 없다. 이것이 프로젝트 2에서 Make를 선택하는 근거가 된다.)

1. <https://console.cloud.google.com> → 프로젝트 생성 (예: `trc-n8n`)
2. `API 및 서비스` → `라이브러리` → **Google Sheets API** 검색 → `사용`
3. `API 및 서비스` → `사용자 인증 정보` → `사용자 인증 정보 만들기` → **서비스 계정**
   - 이름: `n8n-sheets` → 만들기 → 역할 없이 완료
4. 생성된 서비스 계정 클릭 → `키` 탭 → `키 추가` → `새 키 만들기` → **JSON** → 다운로드
5. JSON 안의 `client_email` 값(`n8n-sheets@....iam.gserviceaccount.com`)을 복사
6. **`TRC_Research_Log` 스프레드시트 → `공유` → 위 이메일 추가 → 권한 `편집자`**
7. n8n → `Credentials` → `Create Credential` → **Google Service Account API**
   - `Service Account Email`: 5번의 `client_email`
   - `Private Key`: JSON의 `private_key` 값 전체 (`-----BEGIN PRIVATE KEY-----` 포함, `\n` 그대로)

> 🔒 다운로드한 JSON 키 파일은 제출물에 절대 포함하지 않는다. 스크린샷에서도 `Private Key` 필드는 마스킹 처리한다.

📷 **캡처 2** — n8n Credentials 목록 (Google Service Account 항목, 키 값은 마스킹)

---

## 2. 노드 ① RSS Feed Trigger

`+` → `RSS Feed Trigger` 검색 → 추가.

| 설정 | 값 |
|---|---|
| Poll Times — Mode | `Every Day` |
| Trigger at Hour | `8am` |
| Trigger at Minute | `0` |
| Feed URL | `https://rss.etnews.com/Section901.xml` |

**⭐ 필드명 실측** — 노드 상단 `Fetch Test Event` 클릭 → OUTPUT 패널에서 실제 키 확인 후 아래 표 기입.

| 규격 필드 | 예상 키 | **실측 키 (직접 기입)** |
|---|---|---|
| 제목 | `title` | |
| 링크 | `link` | |
| 요약 | `contentSnippet` | |
| 발행일시 | `isoDate` | |

> **왜 `Schedule Trigger + RSS Read`가 아니라 `RSS Feed Trigger`인가 — 계약 ⑤ 때문이다.**
> `RSS Read`는 상태를 저장하지 않으므로 매 실행마다 25건 전량을 다시 내보낸다. 시트에 같은 기사가 매일 쌓이면 멱등성 계약 위반이다. `RSS Feed Trigger`는 마지막 처리 지점을 인스턴스에 저장해 Make의 `Watch RSS feed items`와 의미가 1:1로 대응한다.
> (`Schedule + RSS Read` 조합을 쓴다면 `Remove Duplicates` 노드의 `Remove Items Seen in Previous Executions` 옵션을 `link` 기준으로 추가해야 한다.)

📷 **캡처 3** — RSS Feed Trigger 설정 + OUTPUT 패널 (필드명이 보이게)

### 2-1. 재현 가능한 테스트를 위한 데이터 고정
`Fetch Test Event` 후 OUTPUT 패널 우상단 **핀 아이콘(Pin Data)** 을 누르면 이후 테스트 실행에서 같은 데이터가 재사용된다.
분기 양쪽을 확인하고 스크린샷을 다시 찍을 때 매우 유용하다. **단, 최종 제출용 실행 증빙은 핀을 해제한 상태의 실제 실행 기록이어야 한다.**

---

## 3. 노드 ② Code — 정규화 + 스코어링

`Code` 노드 추가. 노드 이름 `정규화+스코어링`.

| 설정 | 값 |
|---|---|
| Mode | **`Run Once for All Items`** |
| Language | `JavaScript` |

```javascript
// ── TRC-v1 계약 ②③ 구현 (01_WORKFLOW_SPEC.md 참조) ──────────────
const SIGNAL = {
  '자본시장': ['투자', '인수', '합병', '지분', '상장'],
  '기술자산': ['특허', '양산', '출시'],
  '제도정책': ['규제'],
  '사업화':   ['계약', '수주', '협력'],
};
const THRESHOLD = 2;   // θ
const MAX_ITEMS = 5;   // 계약 ①
const TOOL = 'n8n';

// N1~N3: HTML 태그·엔티티 제거 + 공백 정리
const stripTags = (s = '') =>
  String(s).replace(/<[^>]*>/g, ' ').replace(/&[a-zA-Z#0-9]+;/g, ' ').replace(/\s+/g, ' ').trim();

// N5: JSON 페이로드 안전화 (ASCII 큰따옴표·백슬래시·개행 제거)
const jsonSafe = (s = '') =>
  String(s).replace(/[\x22\x5C\r\n]/g, ' ').replace(/\s+/g, ' ').trim();

// N6: Asia/Seoul 고정, YYYY-MM-DD HH:mm
const kst = (d) => {
  const dt = d ? new Date(d) : new Date();
  if (isNaN(dt.getTime())) return '';
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(dt).replace('T', ' ');
};

const out = [];
for (const item of $input.all().slice(0, MAX_ITEMS)) {
  const j = item.json;
  const title = stripTags(j.title);
  const summary = stripTags(j.contentSnippet || j.content || j.description || '').slice(0, 200); // N4
  const hay = (title + ' ' + summary).toLowerCase();

  const matched = [];
  for (const words of Object.values(SIGNAL)) {
    for (const w of words) {
      if (hay.includes(w.toLowerCase()) && !matched.includes(w)) matched.push(w); // 중복 카운트 금지
    }
  }
  const score = matched.length;

  out.push({ json: {
    collected_at: kst(),
    tool: TOOL,
    tier: score >= THRESHOLD ? 'CORE' : 'REF',
    score,
    matched_keywords: matched.join(',') || '-',
    title,
    title_safe: jsonSafe(title),
    summary,
    published_at: kst(j.isoDate || j.pubDate),
    link: j.link || '',
  }});
}
return out;
```

> ✅ 이 로직은 실제 etnews 피드 형태의 픽스처 5건으로 Node.js에서 사전 검증했다 (`workflows/_test_scoring.js`, 결과: CORE 2 / REF 3 — 양쪽 분기 발화). 실행 방법: `node workflows/_test_scoring.js`

📷 **캡처 4** — Code 노드 코드 + OUTPUT 패널 (`score` / `tier` / `matched_keywords`가 보이게)

---

## 4. 노드 ③ Switch — 조건 분기

`Switch` 노드 추가. 노드 이름 `중요도 분기`.

| 설정 | 값 |
|---|---|
| Mode | `Rules` |

**Routing Rule 1**
| 항목 | 값 |
|---|---|
| Left Value | `{{ $json.score }}` |
| Type | `Number` |
| Operation | `is greater than or equal to` |
| Right Value | `2` |
| Rename Output | ON → Output Name `CORE` |

**Routing Rule 2**
| 항목 | 값 |
|---|---|
| Left Value | `{{ $json.score }}` |
| Type | `Number` |
| Operation | `is less than` |
| Right Value | `2` |
| Rename Output | ON → Output Name `REF` |

**Options → `Add Option` → `Fallback Output` → `REF`(또는 Extra Output)**
→ 어느 규칙에도 걸리지 않는 항목의 유실을 구조적으로 차단한다 (Make의 Fallback route와 동일한 안전장치).

📷 **캡처 5** — Switch 규칙 2개 + Fallback Output 설정

---

## 5. 노드 ④ (CORE) Google Sheets — Append Row

| 설정 | 값 |
|---|---|
| Credential | 1절에서 만든 Google Service Account |
| Resource | `Sheet Within Document` |
| Operation | **`Append Row`** |
| Document | `By URL` 또는 `From list` → `TRC_Research_Log` |
| Sheet | **`CORE`** |
| Mapping Column Mode | `Map Each Column Manually` |

| 시트 열 | 값 |
|---|---|
| 수집시각 | `{{ $json.collected_at }}` |
| 도구 | `{{ $json.tool }}` |
| 분류 | `{{ $json.tier }}` |
| 점수 | `{{ $json.score }}` |
| 매칭키워드 | `{{ $json.matched_keywords }}` |
| 제목 | `{{ $json.title }}` |
| 요약 | `{{ $json.summary }}` |
| 발행일 | `{{ $json.published_at }}` |
| 링크 | `{{ $json.link }}` |

📷 **캡처 6** — Sheets(CORE) 노드 매핑 화면

---

## 6. 노드 ⑤ (CORE) HTTP Request — Discord 알림

Make 구현체와 **동일하게 HTTP 노드를 쓴다.** (n8n에는 Discord 전용 노드가 있지만, 두 도구의 알림 전송 계층을 같은 추상화 수준으로 맞추기 위해 의도적으로 HTTP를 선택했다. → 평가 항목 2의 "동일성 설계 기준" 답변 소재)

| 설정 | 값 |
|---|---|
| Method | `POST` |
| URL | Discord Webhook URL (📌 마스킹) |
| Send Body | ON |
| Body Content Type | `JSON` |
| Specify Body | **`Using Fields Below`** |
| Body Parameter — Name | `content` |
| Body Parameter — Value | 아래 표현식 |

```
=🔎 [CORE] {{ $json.title_safe }}
· 점수 {{ $json.score }} / 시그널 {{ $json.matched_keywords }}
· 발행 {{ $json.published_at }} · 수집 {{ $json.tool }}
{{ $json.link }}
```

> **`Using Fields Below`를 선택하는 이유**: n8n이 필드값을 JSON으로 직렬화할 때 이스케이프를 자동 처리한다. `Using JSON` 모드로 원문 JSON을 직접 쓰면 Make와 똑같은 이스케이프 문제를 다시 만나게 된다.
> 그럼에도 `title_safe`를 쓰는 이유는 **계약 N5를 두 도구가 동일하게 지켜야** 하기 때문이다 — 알림 본문 문자열이 바이트 단위로 같아야 "동일 워크플로우"가 성립한다.

📷 **캡처 7** — HTTP Request 노드 설정 (URL 마스킹)
📷 **캡처 8** — Discord 채널에 도착한 알림 (Make 알림과 나란히 보이면 최상)

---

## 7. 노드 ⑥ (REF) Google Sheets — Append Row

노드 ④와 동일. **`Sheet` 만 `REF`로 변경.** (`분류` 열은 `{{ $json.tier }}` 그대로 두면 자동으로 `REF`가 들어간다)

📷 **캡처 9** — Sheets(REF) 노드 매핑 화면

---

## 8. 실행 및 검증

### 8-1. 테스트 실행
1. 우상단 `Test workflow` 클릭
2. 각 커넥션 위에 흐른 item 수가 표시된다 → **CORE·REF 양쪽 모두 1건 이상 확인**
3. 좌측 `Executions` → 실행 레코드 클릭 → 노드별 입출력 확인

### 8-2. 운영 활성화
우상단 토글 `Inactive` → **`Active`** 로 전환. 이후 매일 08:00에 자동 실행된다.

> ⚠️ **셀프호스팅의 구조적 한계** — 노트북을 끄거나 절전 상태가 되면 n8n 프로세스가 정지하고 트리거가 발화하지 않는다.
> 이것은 버그가 아니라 배포 형태의 결과이며, **프로젝트 2에서 Make를 선택한 1순위 근거**가 된다. 보고서에 반드시 정량 기술할 것.

📷 **캡처 10** — `Test workflow` 직후 전체 캔버스 (양쪽 경로에 item 수가 보이는 상태) ← **가장 중요한 스크린샷**
📷 **캡처 11** — Executions 목록 (성공 실행 기록 + 실행 시각)
📷 **캡처 12** — Google Sheets에 `도구=Make` 행과 `도구=n8n` 행이 같은 스키마로 나란히 쌓인 상태 ← **동일성 증빙 핵심 자료**

---

## 9. 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| `npx n8n` 실행 실패 | Node.js 20 미만 | Node.js 22 LTS 설치 후 재시도 |
| RSS Feed Trigger가 0건 반환 | 이미 마지막 지점까지 처리됨 | `Fetch Test Event`로 테스트, 또는 다른 피드 URL로 검증 |
| Sheets 403 / `caller does not have permission` | 스프레드시트를 서비스 계정과 공유하지 않음 | 1절 6번 — 서비스 계정 이메일을 `편집자`로 공유 |
| Sheets `Unable to parse range` | Sheet 탭 이름 불일치 | 탭 이름이 정확히 `CORE` / `REF` 인지 확인 |
| Private Key 인증 실패 | 붙여넣기 시 `\n`이 실제 개행으로 변환됨 | JSON 원문의 `private_key` 값을 그대로(따옴표 제외) 복사 |
| Switch가 항상 한쪽으로만 감 | `score`가 문자열로 전달됨 | Code 노드에서 `score`가 number인지 OUTPUT에서 확인 (`"3"` 아니라 `3`) |
| Discord 400 | Body를 `Using JSON`으로 직접 작성 | `Using Fields Below`로 변경 |
| Active 전환 후 실행 안 됨 | 프로세스 종료 / PC 절전 | 터미널 유지 또는 Docker로 백그라운드 상시 구동 |

---

## 10. 참고 — 워크플로우 JSON

`workflows/n8n_TRC_v1.json` 을 `Workflows` → `⋯` → `Import from File` 로 불러오면 노드 구조가 한 번에 생성된다.

> ⚠️ **이 JSON은 검증되지 않았다.** 본 작업 환경의 네트워크 정책(`cdn.sheetjs.com` 차단)으로 n8n을 로컬 설치해 임포트 테스트를 할 수 없었다.
> **정본은 위 2~7절의 수동 구성 절차다.** JSON은 노드 배치 편의용으로만 쓰고, 임포트 후 반드시 다음을 UI에서 확인·설정할 것:
> ① Google Sheets 자격증명 선택 ② Document / Sheet 선택 ③ Switch 규칙 2개 ④ HTTP Request URL
> 또한 임포트 산출물은 스크린샷 증빙으로 쓰기 어렵다 — 심사자는 "직접 구성했는가"를 본다. **수동 구성을 권장한다.**
