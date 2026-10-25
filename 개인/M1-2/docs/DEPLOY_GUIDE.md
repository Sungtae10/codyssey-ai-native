# 배포 가이드 (김성태 실행용)

코드는 모두 준비되어 있고, 아래 단계는 **본인 계정과 비밀 키가 필요한 일**이라 직접 해야 합니다.
처음부터 끝까지 약 1시간 30분이 걸립니다. 명령어는 Windows PowerShell 기준이고, Mac은 괄호 안에 적었습니다.

| 단계 | 누가 | 언제 | 무엇을 | 걸리는 시간 |
|---|---|---|---|---|
| 0 | 김성태 | 시작 전 | 계정 5개 확인 | 5분 |
| 1 | 김성태 | 0단계 뒤 | Firebase 프로젝트, Firestore, 서비스 계정 키 | 15분 |
| 2 | 김성태 | 1단계 뒤 | 내 컴퓨터에서 실행, Firestore에 데이터 251개 올리기 | 15분 |
| 3 | 김성태 | 2단계 성공 뒤 | GitHub에 올리기 | 10분 |
| 4 | 김성태 | 3단계 뒤 | Render에 백엔드 배포 | 15분 |
| 5 | 김성태 | 4단계 주소가 나온 뒤 | Vercel에 프론트엔드 배포 | 10분 |
| 6 | 김성태 | 5단계 뒤 | 연결 확인 | 5분 |
| 7 | 김성태 | 6단계 뒤 | 제출 스크린샷 3장 | 10분 |
| 8 | 김성태 | 마지막 | README 주소 바꾸고 다시 올리기, 제출 | 5분 |

---

## 0단계: 준비물 확인

- [ ] GitHub 계정 (Sungtae10)
- [ ] Google 계정 (Firebase용)
- [ ] OpenAI API 키와 결제 크레딧 (platform.openai.com > Billing에서 잔액 확인)
- [ ] Render 계정 (render.com, GitHub로 로그인하면 편함)
- [ ] Vercel 계정 (vercel.com, GitHub로 로그인)
- [ ] 내 컴퓨터에 Python 3.10 이상, Git, Node.js (Node.js가 없으면 2-B의 config 생성은 건너뛰어도 됨)

## 1단계: Firebase 준비 (Firestore와 서비스 계정 키)

쉽게 말하면: 데이터를 넣을 **창고(Firestore)** 를 만들고, 서버만 그 창고에 들어갈 수 있게 **열쇠(서비스 계정 키)** 를 받는 단계입니다.

1. https://console.firebase.google.com 에서 **프로젝트 만들기** → 이름 `usdkrw-ai-assistant` → Google 애널리틱스는 꺼도 됨 → 만들기
2. 왼쪽 메뉴에서 **Firestore**(Databases & Storage 아래) → **데이터베이스 만들기**
   - 버전을 고르는 화면이 나오면 **Standard**
   - 위치: **asia-northeast3 (Seoul)** (한 번 정하면 바꿀 수 없음)
   - 보안 규칙: **프로덕션 모드** (브라우저에서 직접 읽고 쓰는 것을 막음. 우리 서버는 열쇠로 들어가므로 괜찮음)
3. 왼쪽 위 톱니바퀴 → **프로젝트 설정** → **서비스 계정** 탭 → **새 비공개 키 생성** → JSON 파일이 내려받아짐
4. 내려받은 파일 이름을 `firebase-key.json` 으로 바꾸고 `backend` 폴더 안에 넣기

> **주의**: 이 키 파일은 비밀번호와 같습니다. 카톡, 메일, 디스코드, GitHub에 올리지 마세요.
> `.gitignore`가 `firebase-key*.json`과 `*-firebase-adminsdk-*.json` 이름을 막아 두었지만, 3단계에서 한 번 더 확인합니다.

## 2단계: 내 컴퓨터에서 실행

### 2-A. 백엔드

```powershell
cd 내려받은위치\codyssey-m1-2-ai-assistant\backend
py -m venv .venv                       # (Mac: python3 -m venv .venv)
.venv\Scripts\Activate.ps1             # (Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env                 # (Mac: cp .env.example .env)
notepad .env                           # (Mac: open -e .env)
```

`.env` 파일에서 두 줄만 확인하고 저장합니다.

```
OPENAI_API_KEY=sk-로 시작하는 본인 키
FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-key.json
```

> `Activate.ps1`에서 "스크립트를 실행할 수 없습니다" 오류가 나면 먼저 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` 를 입력하고 다시 실행합니다.

Firestore에 데이터 251개를 올리고 서버를 켭니다.

```powershell
python scripts\seed_firestore.py       # 마지막 줄 "완료: 251개 추가, 현재 'data' 문서 251개" 확인
uvicorn main:app --reload
```

- http://localhost:8000/health → `"status":"ok"`, `"ready":true`, `"configured":true` 인지 확인
- http://localhost:8000/docs → Swagger에서 `GET /api/data/summary` 실행 → 기간 2025-10-16 ~ 2026-10-16, 251개 확인
- Firebase 콘솔의 Firestore 화면에 `data` 컬렉션이 생긴 것도 확인

### 2-B. 프론트엔드 (새 PowerShell 창)

```powershell
cd 내려받은위치\codyssey-m1-2-ai-assistant\frontend
node scripts\generate-config.mjs       # "API_BASE_URL=http://localhost:8000" 출력
py -m http.server 5500 --directory public   # (Mac: python3 -m http.server 5500 --directory public)
```

http://localhost:5500 을 열고 "이번 달 환율 흐름 어때?"를 눌러 답이 오면 성공입니다.
답 아래에 `gpt-6-luna`가 보이면 기본 모델이 동작한 것이고, `gpt-4o-mini`가 보이면 기본 모델을 쓸 수 없어 대체 모델로 답한 것입니다 (둘 다 정상 동작).

## 3단계: GitHub에 올리기

1. github.com → **New repository** → 이름 `codyssey-ai-assistant-M1-2` → Public → 아무것도 추가하지 않고 Create (zip을 푼 내 컴퓨터 폴더 이름은 `codyssey-m1-2-ai-assistant` 그대로 둬도 됩니다)
2. 프로젝트 맨 위 폴더에서:

```powershell
cd 내려받은위치\codyssey-m1-2-ai-assistant
git init
git config user.name "김성태"
git config user.email "232972598+Sungtae10@users.noreply.github.com"
git add .
git status
```

3. **`git status` 목록에 `.env`, `firebase-key.json`, `.venv`가 없는지 꼭 확인합니다.** 하나라도 보이면 멈추고 `.gitignore`를 확인합니다.
4. 이상이 없으면:

```powershell
git commit -m "M1-2 나만의 AI 비서: FastAPI, Firestore, GPT 컨텍스트 주입, 바닐라 프론트엔드"
git branch -M main
git remote add origin https://github.com/Sungtae10/codyssey-ai-assistant-M1-2.git
git push -u origin main
```

## 4단계: Render에 백엔드 배포

쉽게 말하면: 내 컴퓨터에서 켰던 서버를 **인터넷에 항상 켜 둔 컴퓨터(Render)** 에 옮기는 단계입니다.

1. https://dashboard.render.com → **New** → **Blueprint** → GitHub 저장소 `codyssey-ai-assistant-M1-2` 선택
2. `render.yaml`을 읽어 서비스 `usdkrw-ai-assistant-api`(무료, 싱가포르)를 보여 줍니다. 값을 넣으라는 칸 2개를 채웁니다.
   - `OPENAI_API_KEY`: 본인 키
   - `FIREBASE_SERVICE_ACCOUNT_JSON`: `firebase-key.json`을 메모장으로 열어 **전체 선택(Ctrl+A) → 복사 → 붙여 넣기**
3. **Apply** → 빌드 로그에 `Your service is live` 가 나올 때까지 기다림 (5~10분)
4. 서비스 화면 위쪽의 주소를 복사합니다. 예: `https://usdkrw-ai-assistant-api.onrender.com` (이름이 겹치면 뒤에 글자가 붙음)
5. 확인
   - `주소/health` → `"status":"ok"`, `"storage":{"ready":true}`, `"openai":{"configured":true}`
   - `주소/docs` → Swagger 화면이 열리면 성공

> 처음 열 때나 15분 동안 아무도 안 쓴 뒤에는 1분 정도 걸릴 수 있습니다 (무료 서버가 잠들었다 깨는 시간).

## 5단계: Vercel에 프론트엔드 배포

1. https://vercel.com → **Add New** → **Project** → GitHub 저장소 **Import**
2. 설정 화면에서:
   - **Project Name**: 칸에 미리 들어 있는 이름을 지우고 `usdkrw-ai-assistant` 입력 (Render의 허용 주소 `ALLOWED_ORIGINS`에 `https://usdkrw-ai-assistant.vercel.app`을 미리 넣어 두었기 때문)
   - **Framework Preset**: Other
   - **Root Directory**: Edit → `frontend` 선택
   - Build Command, Output Directory는 `frontend/vercel.json`이 자동으로 정합니다 (건드리지 않기)
   - **Environment Variables**: Key `API_BASE_URL`, Value = 4단계에서 복사한 Render 주소 (끝에 `/` 없이)
3. **Deploy** → 완료되면 주소가 나옵니다. 예: `https://usdkrw-ai-assistant.vercel.app`

> 빌드 로그에 `API_BASE_URL 환경 변수가 없습니다`가 보이면 2번의 환경 변수를 넣고 **Redeploy** 합니다.

## 6단계: 연결 확인

1. Vercel 주소를 엽니다.
2. 오른쪽 위에 **초록 점 + "서버 연결됨"**, 위쪽 요약판에 **1,334.03원, 251개** 가 보이면 정상입니다.
3. 질문 하나를 보내 답이 오는지 확인합니다.

연결이 안 될 때

| 화면에 보이는 것 | 원인 | 해결 |
|---|---|---|
| "서버에 연결하지 못했어요" + 브라우저 콘솔(F12)에 CORS 오류 | Vercel 주소가 허용 목록에 없음 (이름이 겹쳐 Vercel이 다른 주소를 준 경우) | Render > 서비스 > Environment > `ALLOWED_ORIGINS`의 첫 주소를 실제 Vercel 주소로 바꾸기 → Save (자동 재배포). Vercel의 미리보기(Preview) 주소는 허용하지 않으므로 운영(Production) 주소로 접속 |
| "데이터베이스 연결에 문제" | 서비스 계정 키 붙여 넣기 실수 | Render의 `FIREBASE_SERVICE_ACCOUNT_JSON`을 `{`부터 `}`까지 다시 붙여 넣기 |
| "OPENAI_API_KEY가 없어" | 키를 안 넣음 | Render에 `OPENAI_API_KEY` 추가 |
| "OpenAI 사용 한도에 걸렸습니다" | 크레딧 부족 또는 요청 많음 | platform.openai.com > Billing 확인 |
| 요약판에 "아직 데이터가 없어요" | 2단계 업로드를 안 함 | `python scripts\seed_firestore.py` 실행 |
| 1분 넘게 "서버 깨우는 중" | 무료 서버 첫 실행이거나 배포 실패 | Render 로그 확인, 배포 상태가 Live인지 확인 |

## 7단계: 제출 스크린샷 3장 찍기

Windows 캡처: `Win + Shift + S`. 저장 위치는 `docs\screenshots\` 이고, **파일 이름을 정확히** 맞춥니다.

| 파일 이름 | 찍는 장면 | 방법 |
|---|---|---|
| `01_chat_summary.png` | 데이터 요약이 보이는 채팅 (질문 + 답변) | AI 채팅 탭에서 "이번 달 환율 흐름 어때?" 질문 → 위쪽 요약판과 답변이 한 화면에 보일 때 |
| `02_data_crud.png` | 데이터 관리 (CRUD 1개 동작) | 데이터 관리 탭 → 2026-10-16 줄의 **수정** → 메모를 `메모 수정 예시`로 바꾸고 저장 → 노란 줄과 "수정했어요" 알림이 보일 때 |
| `03_history_load.png` | 대화 기록 불러오기 | **새 대화** 클릭 → 왼쪽 목록에서 앞서 나눈 대화 클릭 → 이전 메시지가 다시 나타난 화면 |

> 데이터 화면에서는 실제로 확인한 값만 넣으세요. 시연용으로 숫자를 지어 넣으면 AI 요약도 그 숫자로 바뀝니다. 그래서 위에서는 숫자 대신 **메모 수정**을 권했습니다. 다 찍은 뒤 메모를 `FRED H.10`으로 되돌려도 됩니다.

## 8단계: README 마무리와 제출

1. `README.md` 1장 표의 주소 3개를 실제 주소로 바꿉니다.
2. 스크린샷 3장이 `docs\screenshots\`에 있는지 확인합니다.
3. 올리기:

```powershell
git add README.md docs/screenshots
git commit -m "배포 주소와 제출 스크린샷 추가"
git push
```

4. GitHub에서 README의 스크린샷과 다이어그램이 보이는지 확인하고, 저장소 주소를 코디세이에 제출합니다.

## 제출 전 최종 점검표

- [ ] Vercel 주소 접속 → "서버 연결됨"과 요약판 숫자 표시
- [ ] Render 주소 `/docs` → Swagger 열림
- [ ] 질문 → 답변과 "내 데이터 요약 반영" 문구 표시
- [ ] 데이터 추가·수정·삭제 중 하나 이상 화면에서 동작
- [ ] 새 대화 → 대화 목록에서 불러오기 동작
- [ ] README에 주소 3개, 스크린샷 3장, 환경 변수 표 있음
- [ ] GitHub 저장소에 `.env`, `firebase-key.json`이 없음 (저장소 파일 목록에서 직접 확인)
- [ ] [평가 대비 노트](DEFENSE_QA.md)의 6개 질문을 내 말로 설명 가능
