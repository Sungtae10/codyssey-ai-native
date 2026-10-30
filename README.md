# 코디세이 AI 네이티브 과정 프로젝트 모음

이노베이션아카데미 코디세이 AI 네이티브 과정(2026.6 ~ 2026.10)에서 김성태가 수행한 미션과 팀 프로젝트를 한 저장소에 모았습니다. 미션마다 따로 만들었던 GitHub 저장소 10개를 개인 미션 8개(`개인/`)와 팀 프로젝트 2개(`팀/`)로 나눠 넣었고, 폴더 안의 파일과 커밋 기록은 원본 저장소와 같습니다.

**과정 흐름:** 프롬프트 설계 → 멀티모달 생성 → 노코드 자동화 → Python CLI → 웹 서비스 배포 → 팀 데이터 파이프라인 → 시계열 데이터 분석 → AI 에이전트 → 공시 기반 RAG 서비스(Final Project)

## 폴더 구조

```
codyssey-ai-native/
├── 개인/
│   ├── A1-1/     프롬프트 관리 프로그램
│   ├── A1-2/     국내 여행 추천 CLI
│   ├── A1-3/     AX 레이더
│   ├── B1-1/     논문 요약 프롬프트 시스템
│   ├── B1-2/     KARIOS 10초 AI 광고
│   ├── B1-3/     노코드 자동화 비교
│   ├── M1-1/     삼성전자 주가 트렌드 분석
│   └── M1-2/     원/달러 환율 AI 비서
├── 팀/
│   ├── A2-2/     뉴스 데이터 파이프라인 CLI
│   └── Final/    AI Promise: 기업 AI 약속 검증 (발표자료 포함)
└── README.md
```

## 개인 미션 (8개)

과정 순서대로 적었습니다. 이름을 누르면 해당 폴더로 이동하고, 자세한 내용과 실행 방법은 폴더마다 있는 README에 있습니다.

- **B1-1** [논문 요약 프롬프트 시스템](개인/B1-1): 기술경영·CFM 논문 요약 프롬프트 설계, 모델 3개 비교 후 GPT-5.5 선정, 환각 검증. 사용 기술: GPT-5.5, Claude Opus 4.8, Gemini 3.1 Pro
- **B1-2** [KARIOS 10초 AI 광고](개인/B1-2): 가상 AI 비서 앱 브랜드 기획과 스토리보드, 생성형 AI로 만든 10초 광고 영상. 사용 기술: Gemini(이미지), Google Veo(영상), Suno(음악), CapCut(편집)
- **B1-3** [노코드 자동화 비교](개인/B1-3): 같은 워크플로우를 Make와 n8n으로 구현해 9개 항목으로 비교, OpenDART 공시 분류 자동화 구현. 사용 기술: Make, n8n, OpenDART API, Google Sheets
- **A1-1** [프롬프트 관리 프로그램](개인/A1-1): 프롬프트 추가·검색·즐겨찾기 콘솔 프로그램, 기능 단위 커밋과 브랜치 병합. 사용 기술: Python(표준 라이브러리), Git
- **A1-2** [국내 여행 추천 CLI](개인/A1-2): 날짜를 넣으면 LLM이 지역을 추천하고, 지도 API로 맛집을 찾아 여행 리포트 작성. 사용 기술: Python, OpenAI·Gemini API, 카카오·네이버 지역 검색 API
- **A1-3** [AX 레이더](개인/A1-3): 제조기업 AI 전환(AX) 준비도 5개 영역 자가진단, AI가 12개월 로드맵과 KPI 제안. 사용 기술: HTML·CSS·JS, Vercel 서버리스 함수(Python), Gemini API
- **M1-1** [삼성전자 주가 트렌드 분석](개인/M1-1): KRX 927거래일 데이터로 삼성전자·SK하이닉스·KOSPI 비교, 시계열 분해와 예측, 웹 대시보드. 사용 기술: pandas, statsmodels, matplotlib, Plotly
- **M1-2** [원/달러 환율 AI 비서](개인/M1-2): 저장한 원/달러 환율 일별 데이터 251개의 요약을 GPT에 넣어 답하고, 요약에 없는 값은 도구 호출로 조회. 사용 기술: FastAPI, Firestore, OpenAI Function Calling, MCP, Render, Vercel

## 팀 프로젝트 (2개)

- **A2-2** [뉴스 데이터 파이프라인 CLI](팀/A2-2): 수집, 정제, AI 요약, 분석, 리포트, 내보내기를 명령 6개로 실행. 사용 기술: Python, SQLite, OpenAI API, pandas, matplotlib
  - 팀 4명: 김성태(팀장: 뼈대·저장소·통합·문서), 박수민(데이터 수집·정제), 한다혜(AI 요약·분석·감성), 김범근(시각화·리포트·내보내기·조회)
- **Final** [AI Promise: 기업 AI 약속 검증](팀/Final): 사업보고서의 AI 약속과 후속 공시의 실행 근거를 찾아 4가지로 판정하고 면접 준비에 연결. 사용 기술: OpenDART, RAG(BM25 + 의미 검색), LLM 판정, GitHub Actions, Vercel
  - 팀 4명: 김성태(총괄, AI 엔진, 평가 설계, 저장소와 배포, 최종 발표), 박수민(화면 4개), 김서원(공시 직접 읽기와 정답 매기기, 사용자 테스트 진행), 서준용(화면 디자인, 사용자 테스트 진행 보조, 발표자료, 시연 영상)

팀원 역할은 각 프로젝트 README에 적힌 내용입니다. B2-2 팀 과제(뉴스 요약 자동화, 24팀)는 팀장 정민규 계정의 저장소에 있어서 이 저장소에는 넣지 않았습니다: <https://github.com/reinvent21c-oss/term-mission-projectb>

## 결과물 바로 보기

- **B1-2:** [최종 광고 영상 (10초, mp4)](개인/B1-2/assets/final/karios_ad_10s.mp4), [스토리보드 PDF](개인/B1-2/docs/KARIOS_Storyboard_SungtaeKim.pdf)
- **A1-3:** 배포 사이트 <https://codyssey-a1-3-ax-radar-ofpt.vercel.app>
- **M1-1:** [분석 리포트](개인/M1-1/REPORT.md), 웹 대시보드 <https://sungtae10.github.io/codyssey-semiconductor-trend-analysis-M1-1/>
- **M1-2:** 웹 화면 <https://usdkrw-ai-assistant.vercel.app>, API 문서 <https://usdkrw-ai-assistant-api.onrender.com/docs>
- **Final:** 서비스 <https://ai-promise-six.vercel.app>, [최종 발표자료 PDF](팀/Final/presentation/AI_Promise_Final_Presentation.pdf), [시연 영상 (mp4)](팀/Final/presentation/AI_Promise_Demo_Video.mp4)

배포 사이트는 각 원본 저장소에 연결되어 있고, 주소는 폴더 README에 적힌 주소입니다. M1-2 API는 무료 서버라서 한동안 요청이 없으면 잠들고, 첫 요청에 1분 정도 걸릴 수 있습니다.

## 원본 저장소

| 폴더 | 원본 저장소 | 원본 마지막 커밋 | 커밋 수 |
|---|---|---|---|
| 개인/B1-1 | [Codyssey-ai-tools-B1-1](https://github.com/Sungtae10/Codyssey-ai-tools-B1-1) | `e9138b6` | 7 |
| 개인/B1-2 | [Codyssey-ai-tools-B1-2](https://github.com/Sungtae10/Codyssey-ai-tools-B1-2) | `f55a4af` | 1 |
| 개인/B1-3 | [codyssey-b1-3-nocode-automation](https://github.com/Sungtae10/codyssey-b1-3-nocode-automation) | `377df14` | 16 |
| 개인/A1-1 | [codyssey-a1-prompt-manager](https://github.com/Sungtae10/codyssey-a1-prompt-manager) | `fd5c3fe` | 23 |
| 개인/A1-2 | [codyssey-a1-2-travel-planner](https://github.com/Sungtae10/codyssey-a1-2-travel-planner) | `6a98564` | 6 |
| 개인/A1-3 | [codyssey-a1-3-ax-radar](https://github.com/Sungtae10/codyssey-a1-3-ax-radar) | `aea9f0b` | 25 |
| 개인/M1-1 | [codyssey-semiconductor-trend-analysis-M1-1](https://github.com/Sungtae10/codyssey-semiconductor-trend-analysis-M1-1) | `0d87f86` | 19 |
| 개인/M1-2 | [codyssey-ai-assistant-M1-2](https://github.com/Sungtae10/codyssey-ai-assistant-M1-2) | `cc98273` | 9 |
| 팀/A2-2 | [codyssey-a2-news-pipeline](https://github.com/Sungtae10/codyssey-a2-news-pipeline) | `3d10864` | 20 |
| 팀/Final | [ai-promise](https://github.com/Sungtae10/ai-promise) | `169b065` | 104 |

- 원본 저장소마다 main 브랜치를 가져왔고, Final만 final-presentation 브랜치를 가져왔습니다.
- 폴더마다 파일 내용은 원본 저장소의 위 커밋과 같습니다. 폴더의 Git 트리 해시가 원본과 일치하는 것으로 확인했습니다.
- 커밋의 작성자, 날짜, 메시지는 그대로 두고 파일 위치만 폴더 아래로 옮겼습니다. 그래서 커밋 해시는 원본과 다릅니다. 김성태 본인 커밋의 이메일은 GitHub 비공개 주소로 통일했고, 팀원과 Claude가 만든 커밋은 바꾸지 않았습니다.
- `팀/Final/presentation/`은 최종 발표일(10.21)에 올린 발표자료와 시연 영상입니다. 원본 저장소에서는 제출본(main, `3960081`)과 나눠 final-presentation 브랜치에 두었고, 이 저장소에는 그 브랜치를 가져왔습니다. presentation 폴더 밖의 파일은 main 제출본과 같습니다.
- 원본 저장소가 없어져도 이 저장소만으로 각 프로젝트 제출본의 파일과 커밋 기록을 확인할 수 있습니다.

## 실행 방법

```bash
git clone https://github.com/Sungtae10/codyssey-ai-native.git
cd codyssey-ai-native/개인/M1-1   # 실행할 프로젝트 폴더
```

그다음은 폴더 README의 실행 방법을 따릅니다. 폴더 README에 적힌 `git clone` 주소와 `cd` 폴더 이름은 원본 저장소 기준이라서, 이 저장소에서는 위 두 줄로 바꿔 실행합니다.

- API 키가 필요한 프로젝트(A1-2, A1-3, M1-2, A2-2, Final)는 `.env.example` 파일을 복사해 직접 발급한 키를 넣어야 합니다. M1-2는 `backend/`와 `frontend/`, Final은 `engine/` 폴더 안에 이 파일이 있습니다.
- `팀/Final/.github/workflows/`의 GitHub Actions 설정은 이 저장소에서 실행되지 않습니다. GitHub는 저장소 맨 위의 `.github` 폴더만 읽기 때문입니다.

## AI 사용 고지

각 프로젝트에서 어떤 AI 도구를 어디에 썼는지는 폴더마다 README나 AI 사용 로그에 적혀 있습니다. 미션별 저장소를 이 저장소 하나로 모으는 작업(폴더 이동, 원본 대조, 이 안내 문서 작성)은 Claude(Anthropic의 AI)로 했습니다.
