# AI Promise | 기업 AI 약속 검증

회사가 사업보고서에 "AI로 이것을 하겠다"고 쓴 약속을 찾고, 다음 보고서에 실행 근거가 있는지 찾아 4가지(근거 확인, 일부 확인, 공시에서 확인 불가, 회사가 미추진으로 공시)로 판정해 보여주는 웹 서비스입니다. Codyssey Final Project입니다.

- 서비스 주소: https://ai-promise-six.vercel.app (Vercel, `app/` 폴더. main에 올리면 자동으로 다시 배포됩니다)
- 사용자: 취업·이직 준비자 (면접 전 5분 안에 지원 회사의 AI 계획과 실행을 공시 원문으로 확인)
- 핵심 기업: 삼성전자(개발·시연용), SK하이닉스(평가용)
- 기업 추가: 관문 2를 통과하면 업종이 다른 시연용 기업을 최대 3곳 (후보: 현대자동차, NAVER, LG전자). 시연용 기업은 사람 정답과 비교하지 않고 화면에 시연용으로 표시합니다.
- 약속을 찾는 보고서: 2024 사업보고서 / 근거를 찾는 보고서: 2025 사업보고서, 2026 반기보고서

## 1. 핵심 AI 활용

미션의 필수 기술 요소 5개(AI Agent, RAG, 멀티모달 AI, 자동화 워크플로우, Long-term Memory) 중 3개를 씁니다. 자세한 내용은 [기능 요구 명세서](docs/requirements.md) 4장에 있습니다.

| 기술 요소 | AI Promise에서 하는 일 | 코드 |
| --- | --- | --- |
| RAG | 후속 보고서에서 키워드 검색(BM25)과 의미 검색(OpenAI 임베딩 + ChromaDB)으로 근거 후보를 찾고, 그 후보 문장만 근거로 LLM이 판정합니다 | `engine/aipromise/retrieve.py`, `engine/aipromise/judge.py` |
| AI Agent (정보 검색 Agent) | 근거를 못 찾으면 AI가 새 검색어를 정하고, 코드가 그 검색어로 다시 검색합니다. 근거를 찾거나, 처음 검색을 포함해 3번이 되거나, 더 쓸 검색어가 없으면 멈추고, 검색 기록을 남깁니다 | `engine/aipromise/judge.py` |
| 자동화 워크플로우 | `run.py all` 한 번으로 7단계(수집, 약속 추출, 분류, 근거 검색, 판정, 인용 검사, 면접 카드)가 차례로 돌고, 결과 파일을 내보내 main에 올리면 GitHub Actions 검사와 Vercel 배포가 자동으로 이어집니다 | `engine/run.py`, `.github/workflows/ci.yml` |

AI가 고른 근거는 원문에 그대로 있는지 코드로 다시 검사합니다(인용 검사). 통과하지 못한 근거는 빼고, 근거가 필요한 판정인데 통과한 근거가 하나도 없으면 "공시에서 확인 불가"로 낮춥니다.

## 2. 기술 스택과 선정 이유

| 영역 | 쓰는 것 | 고른 이유 |
| --- | --- | --- |
| 엔진 언어 | Python (CI는 3.11) | 팀에서 RAG를 만들어 본 사람이 김성태뿐이고, 그 경험(DART-Foresight AI)이 Python이라 그대로 이어 씁니다 |
| LLM | OpenAI gpt-4o-mini, temperature 0 | DART-Foresight AI와 같은 구성입니다. 같은 입력에 최대한 같은 답이 나오도록 temperature를 0으로 둡니다. 판정 정확도가 낮으면 `engine/config.yaml`의 `judge_model` 한 줄만 바꿔 다시 잴 수 있게 나눠 두었습니다 |
| AI 연결 | LangChain (langchain-openai, langchain-chroma) | DART-Foresight AI의 검색 구성을 출처를 밝히고 다시 씁니다 |
| 근거 검색 | BM25(직접 구현) + text-embedding-3-small + ChromaDB, RRF로 순위 합치기 | DART-Foresight AI 평가에서 의미 검색만으로는 Hit@4가 14/20으로 약했습니다(`engine/README.md` 9장). 제품명, 공장명처럼 글자가 같은 문장을 잘 찾는 키워드 검색을 더했습니다 |
| PDF 읽기 | pypdf | DART에서 받은 정기보고서 PDF를 장별 문장으로 나눕니다 |
| 화면 | HTML, CSS, JavaScript (빌드 없음) | 화면 담당이 React·Streamlit 경험이 없고 AI 도구로 Vercel에 배포해 본 경험이 있어 가장 단순한 정적 웹을 골랐습니다. 화면은 결과 파일 하나만 읽어 엔진과 따로 만들 수 있습니다 |
| 배포 | Vercel (Root Directory: `app`) | 빌드 없이 `app/` 폴더를 바로 배포하고, main에 올리면 자동으로 다시 배포됩니다. 저장소와 배포를 김성태 계정 하나로 모았습니다 (10/8 결정) |
| 자동 검사 | GitHub Actions, Playwright | Pull Request를 올리거나 main에 올릴 때마다 엔진 시험과 화면 검사(글자 대비, 가로 넘침)를 자동으로 돌립니다 |
| 사용자 테스트 설문 | Google Forms, Google Sheets (Apps Script로 생성) | 이름·연락처·이메일을 받지 않게 설정할 수 있고, 응답이 시트에 자동으로 쌓입니다 |
| 협업 | GitHub Issues·Pull Request, Google Drive | 팀원은 드라이브에 파일을 올리고 김성태가 저장소에 반영합니다. 기록은 커밋, PR, 이슈에 남깁니다 |

버전은 `engine/requirements.txt`에 고정했습니다.

## 3. 실행 방법

**화면만 내 컴퓨터에서 보기** (저장소 맨 위 폴더에서)

```bash
cd app
python -m http.server 8000
# 브라우저에서 http://localhost:8000 을 엽니다
```

`index.html`을 더블클릭해 열면(주소가 `file://`로 시작) 브라우저 보안 규칙 때문에 결과 파일을 읽지 못하고 예시 데이터가 보입니다. 위처럼 작은 서버로 여세요.

**엔진 돌리기** (준비 약 30분, 자세한 순서는 [engine/README.md](engine/README.md))

```bash
cd engine
pip install -r requirements.txt
cp .env.example .env        # .env에 OPENAI_API_KEY를 적습니다. 이 파일은 저장소에 올리지 않습니다
python run.py doctor --company samsung     # 설치, 키, PDF 점검 (판정 모델·임베딩 모델을 1번씩 실제 호출)
python run.py all --company samsung        # 1~7단계 실행
python run.py export --companies samsung skhynix --copy-to ../app/data/results.json
python run.py check --file ../app/data/results.json
```

PDF 6개는 `data/pdf/`에 둡니다 (저장소에 올리지 않습니다).

**코드 점검** (키 없이 가상 회사로 시험)

```bash
python tests/test_mock.py        # 엔진·평가: 마지막 줄에 "시험 통과"
python tests/test_ui_static.py   # 화면: app.js가 쓰는 class가 CSS에 모두 있는지 (브라우저 없이)
python tests/ui_check.py         # 화면: 모든 화면(예시 데이터 18개) x 다크/라이트의 글자 대비, 가로 넘침, 필수 부품 (Playwright 필요)
```

세 검사는 Pull Request를 올리거나 main에 올릴 때 CI에서도 자동으로 돌아갑니다.

## 4. 폴더

| 폴더 | 내용 | 만든 사람 |
| --- | --- | --- |
| `app/` | 웹 화면 4개 (HTML, CSS, JS). Vercel이 이 폴더를 배포합니다 | 화면: 박수민 (`1011_수민_화면.zip`) / 디자인: 서준용 (시안 v4, 10/12·10/13) / 엔진 결과 연결: 김성태 (`1012_김성태_화면_데이터연결.zip`) |
| `engine/` | 공시 PDF에서 약속을 찾고, 근거를 검색해 판정하고, 면접 카드를 만드는 AI 엔진 | 김성태 |
| `eval/` | 판정 기준(v1, v2)과 사람 정답으로 AI를 평가하는 코드 | 김성태 (정답: 김서원, 김성태) |
| `tests/` | 인터넷과 API 키 없이 가상 회사로 끝까지 도는 시험 | 김성태 |
| `data/` | 공시 PDF와 실행 결과 자리 (PDF는 저장소에 올리지 않습니다) | |
| `docs/` | 기능 요구 명세서, 아키텍처, 평가 계획, 진행 기록 등 문서 | 김성태 |

## 5. 화면

- `app/index.html`은 `app/data/results.json`(엔진 결과)을 먼저 읽고, 없으면 `app/data/sample-data.js`(가상 회사 2곳 예시 데이터)를 보여줍니다. 예시 데이터일 때는 화면 위에 "예시 데이터입니다" 띠가 나옵니다.
- 모든 화면에 "공시 범위 안에서 확인한 결과입니다.", "AI가 생성한 분석입니다." 두 문구가 항상 보입니다.
- 화면 고치는 규칙은 `app/README.md`에 있습니다. 디자인 변경은 CSS에서 합니다.

## 6. 작업 규칙

- main에 올라간 것은 바로 서비스 주소에 배포됩니다. main에 올리기 전에 `python tests/test_mock.py`가 "시험 통과"여야 합니다.
- 사용자 테스트 기간(R0 예행연습부터 마지막 테스트까지)에는 main의 화면을 바꾸지 않습니다. 테스트를 막는 오류만 바로 고치고, 나머지는 브랜치에서 만들어 테스트가 끝난 뒤 합칩니다.
- 디자인을 바꾸면 `tests/ui_check.py`로 글자 대비(작은 글자 4.5:1, 큰 글자 3:1 이상)와 화면 깨짐을 확인합니다.
- 다른 AI 도구에 저장소 접근을 주면 main에 직접 올리지 않고 브랜치와 Pull Request로만 작업하고, 김성태가 확인한 뒤 합칩니다. (두 도구가 main을 동시에 고치면 서로 덮어씁니다)

## 7. 지키는 것

- API 키(`engine/.env`), 사용자 테스트 참여자의 이름과 연락처는 저장소에 올리지 않습니다. (`.gitignore`로 막아 둠)
- 화면과 판정 이유에 "거짓", "AI 워싱" 같은 단정 표현을 쓰지 않습니다. 근거를 못 찾은 약속은 "공시에서 확인 불가"로 표시하며, 안 했다는 뜻이 아닙니다.
- SK하이닉스는 평가용 기업이라, 사람 정답을 먼저 만든 뒤 AI 결과와 비교합니다.
- 사용자 테스트는 참여 동의를 받은 뒤 진행하고, 참여자는 번호(P01 등)로만 기록합니다.

## 8. 역할

- 김성태: 총괄, AI 엔진, 평가 설계, 저장소와 배포
- 박수민: 화면 4개
- 김서원: 공시 직접 읽기와 정답 매기기, 사용자 테스트 진행
- 서준용: 화면 디자인, 사용자 테스트 진행 보조, 발표자료, 3분 시연 영상

## 9. 결과

사용자 테스트(10/16)와 SK하이닉스 정답 평가가 끝나면 10/17에 이 장을 채웁니다. 숫자는 실제로 잰 값만 씁니다.

| 결과 | 원자료 | 계산 |
| --- | --- | --- |
| AI 판정 평가 (사람 합의 정답 대비 정확도, macro-F1, 혼동표, 사람 간 kappa) | `eval/gold/`(사람 정답), `data/work/<기업>/judged.json`(엔진 판정) | `python eval/evaluate.py` |
| 사용자 테스트 (4분 안에 정답을 찾은 비율, 설문 점수) | `eval/user_test/results.csv` (이름 없이 번호만) | `python eval/user_test/analyze.py eval/user_test/results.csv` |
| 피드백 반영 (의견, 원인, 조치, 커밋, 재확인) | 반영 기록 표 | 10/17 작성 |

## 10. AI 사용

엔진 코드의 첫 버전, 화면의 엔진 결과 연결 수정, 디자인 시안 반영과 접근성 보정, 화면 자동 검사, 기능 요구 명세서와 진행 기록의 초안은 AI 도구(Claude)로 작성했습니다. 문서, CI, 평가 코드 일부(PR #1, #2)와 판정기준 v2 동결 및 엔진 검색어·지시문 동기화(PR #13)는 ChatGPT가 Pull Request로 올렸습니다. 실행, 점검, 수정은 김성태가 합니다. 엔진의 모든 LLM 호출 기록은 실행할 때 `data/work/<기업>/llm_log.jsonl`에 남습니다.

## 11. 프로젝트 문서

- [기능 요구 명세서](docs/requirements.md)
- [진행 기록](docs/progress-log.md)
- [아키텍처](docs/architecture.md)
- [평가 계획](docs/evaluation-plan.md)
- [10분 비대면 사용자 테스트](docs/user-test-protocol.md)
- [시연용 기업 확장 계획 (관문 2 통과 시)](docs/company-expansion-plan.md)
- [AI 윤리·신뢰성](docs/ai-ethics.md)
- [Vercel 배포](docs/deploy.md)
- [Google Drive ↔ GitHub 동기화](docs/drive-sync.md)
- [제출 증빙 체크리스트 (공식 미션 기준)](docs/submission-evidence-checklist.md)
- [후속 연구 계획](docs/follow-up-study-plan.md)
- [팀 협업 규칙](CONTRIBUTING.md)

## 12. 추가 평가

- 사용자 테스트: `eval/user_test/`
- 문장 분류 ML 실험 (`eval/ml/`): 이번 제출(10/18)에서는 하지 않고 다음 단계로 둡니다 (기획 보고서 8.3). 코드와 데이터 형식만 있습니다.
