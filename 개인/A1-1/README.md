# 나만의 프롬프트 관리 프로그램 (Prompt Manager)

이전 미션에서 만든 프롬프트를 한곳에 모아 관리하는 Python 콘솔 프로그램입니다.

Codyssey AI 네이티브 과정 **A1-1 미션(Python & Git 기초)** 결과물입니다.
터미널에서 메뉴 번호를 입력해 프롬프트를 추가하고, 목록·카테고리·검색으로 찾고, 자주 쓰는 프롬프트는 즐겨찾기로 모아 둡니다.
외부 라이브러리 없이 파이썬 기본 문법만으로 만들었습니다.

## 실행 방법

| 순서 | 할 일 | 명령어 |
|---|---|---|
| 1 | Python 3.10 이상인지 확인 | `python --version` |
| 2 | 저장소 내려받기 | `git clone https://github.com/Sungtae10/codyssey-a1-prompt-manager.git` |
| 3 | 폴더로 이동 | `cd codyssey-a1-prompt-manager` |
| 4 | 프로그램 실행 | `python prompt_manager.py` (Mac은 `python3 prompt_manager.py`) |

- 실행하면 메뉴가 나오고, 번호를 입력하면 그 기능이 실행됩니다.
- 기능이 끝나면 메뉴로 돌아오고, `0`을 입력하면 종료합니다.
- 메뉴에 없는 값(예: `abc`, `99`)을 입력하면 안내 메시지를 보여 주고 메뉴를 다시 출력합니다.
- 추가하거나 바꾼 내용은 **실행 중에만 유지**되고, 종료하면 처음 상태로 돌아갑니다.

## 기능 목록

| 메뉴 | 기능 | 동작 |
|---|---|---|
| 1 | 프롬프트 추가 | 제목, 내용, 카테고리를 입력받아 추가 (빈 값이면 다시 입력, 카테고리는 목록에서 고르거나 7번으로 직접 입력, 즐겨찾기 기본값 False) |
| 2 | 프롬프트 목록 | 전체 프롬프트를 `번호. [카테고리] 제목 ⭐` 형태로 출력, 없으면 안내 |
| 3 | 카테고리별 조회 | 카테고리 목록(개수 포함)에서 하나를 고르면 그 카테고리 프롬프트만 출력, 없으면 안내 |
| 4 | 프롬프트 검색 | 검색어가 제목 또는 내용에 들어간 프롬프트를 출력 (영문 대소문자 무시), 없으면 안내 |
| 5 | 프롬프트 상세 보기 | 번호를 입력하면 제목, 카테고리, 즐겨찾기 여부, 내용 전체를 출력, 잘못된 번호는 안내 |
| 6 | 즐겨찾기 관리 | 번호를 입력하면 즐겨찾기 추가, 같은 번호를 한 번 더 입력하면 해제 |
| 7 | 즐겨찾기 목록 | 즐겨찾기한 프롬프트만 모아서 출력, 없으면 안내 |
| 0 | 종료 | 프로그램 종료 |

> 카테고리, 검색, 즐겨찾기 결과 앞의 번호는 **전체 목록 번호**입니다. 이 번호를 5번(상세 보기)이나 6번(즐겨찾기 관리)에 그대로 입력하면 됩니다.

## 등록된 프롬프트 카테고리

| 카테고리 | 어떤 프롬프트인가 | 기본 등록 프롬프트 (출처 미션) |
|---|---|---|
| 텍스트 생성 | 요약, 글, 보고서처럼 문장 결과물을 만드는 지시문 | 논문 핵심 요약 입력 템플릿 (B1-1) |
| 이미지 생성 | 이미지 AI에 넣는 장면, 구도, 색감 묘사 | KARIOS 씬1 키비주얼 (B1-2, Gemini) |
| 영상 생성 | 영상 AI에 넣는 장면, 카메라, 조명, 소리 묘사 | KARIOS 씬1 알림 과부하 영상, KARIOS 씬3 AI 선제 추천 영상 (B1-2, Veo) |
| 페르소나 | AI에게 역할, 말투, 규칙을 정해 주는 시스템 프롬프트 | Paper Lens 논문 리뷰 연구원 v2 (B1-1) |
| 자동화 | Make 같은 노코드 도구에서 자동으로 실행되는 프롬프트 | FIFA 2026 뉴스 3줄 요약 (B2-2, Make + Gemini) |
| 기타 | 위 5개에 들어가지 않는 프롬프트 (예: 음악 생성) | 없음 (비어 있을 때의 안내를 바로 확인하도록 비워 둠) |
| 직접 입력 | 추가할 때 7번을 고르면 새 카테고리 이름을 직접 입력 | 입력한 카테고리는 3번 카테고리 목록에 자동으로 추가됨 |

- 기본 데이터는 **이전 미션(B1-1, B1-2, B2-2)에서 실제로 사용한 프롬프트 6개**입니다.

## 데이터 구조

프롬프트는 **리스트(list) 안에 딕셔너리(dict)** 를 담아 저장합니다.

```python
prompts = [
    {
        "title": "Paper Lens 논문 리뷰 연구원 v2 (B1-1)",
        "content": "당신은 기술경영 분야 논문 리뷰 보조 연구원 \"Paper Lens\"입니다. ...",
        "category": "페르소나",
        "favorite": True,
    },
    {
        "title": "FIFA 2026 뉴스 3줄 요약 (B2-2, Make+Gemini)",
        "content": "FIFA 2026 관련 뉴스를 한국어 3줄로만 요약해줘. ...",
        "category": "자동화",
        "favorite": False,
    },
]
```

## 코드 구조

`prompt_manager.py` 한 파일 안에서 기능별로 함수를 나눴습니다.

| 구분 | 함수 | 하는 일 |
|---|---|---|
| 기본 데이터 | `make_prompt()`, `create_default_prompts()` | 프롬프트 딕셔너리 만들기, 기본 6개 등록 |
| 입력 도우미 | `input_text()`, `to_number()`, `choose_category()`, `select_prompt()` | 빈 값 재입력, 숫자 변환, 카테고리 선택, 번호 검사 |
| 출력 도우미 | `print_title()`, `format_prompt_line()`, `print_all_lines()`, `print_prompt_lines()` | 제목 줄과 목록 한 줄 모양 통일 |
| 찾기 | `get_categories()`, `find_by_category()`, `find_by_keyword()`, `find_favorites()` | 조건에 맞는 프롬프트 모으기 |
| 기능 | `add_prompt()`, `show_list()`, `show_by_category()`, `search_prompt()`, `show_detail()`, `toggle_favorite()`, `show_favorites()` | 메뉴 1~7번 |
| 시작점 | `show_menu()`, `main()` | 메뉴 출력, 입력한 번호에 맞는 기능 호출 반복 |

## 프로젝트 구조

```
codyssey-a1-prompt-manager/
├── prompt_manager.py   # 프로그램 코드 전체
├── README.md           # 프로그램 설명서 (이 문서)
└── .gitignore          # Git에 올리지 않을 파일 목록
```

## Git 작업 방식

- 기능 하나를 완성할 때마다 커밋했고, 커밋 메시지 앞에 변경 종류를 표시했습니다.
  `feat` 새 기능 | `fix` 오류 수정 | `refactor` 동작은 같고 구조만 정리 | `docs` 문서 | `chore` 설정
- 프롬프트 목록 기능은 `feature/prompt-list` 브랜치에서 만든 뒤, `git checkout main` 후 `git merge --no-ff feature/prompt-list` 로 main에 병합했습니다. `--no-ff` 는 브랜치가 갈라졌다가 합쳐진 모양을 병합 커밋(merge commit)으로 남기는 옵션입니다.

| 명령어 | 이 프로젝트에서 한 일 |
|---|---|
| `git init` | 프로젝트 폴더를 Git 저장소로 시작 |
| `git add` | 커밋할 파일을 준비 영역(staging area)에 올림 |
| `git commit` | 준비된 변경 내용을 메시지와 함께 기록 |
| `git push` | 내 컴퓨터의 커밋을 GitHub 저장소에 올림 |
| `git pull` | GitHub 웹에서 수정한 README(작성자 항목)를 내 컴퓨터로 가져옴 |
| `git checkout` | `feature/prompt-list` 브랜치를 만들고 이동, 작업 후 main으로 복귀 |
| `git merge` | `feature/prompt-list` 브랜치를 main에 병합 |
| `git clone` | 공개 샘플 저장소(octocat/Hello-World)를 내려받아 폴더 구조와 로그를 확인한 뒤 삭제 |

## 미션 요구사항 체크리스트

| 요구사항 | 결과 | 확인 위치 |
|---|---|---|
| 메뉴 출력, 번호 선택, 잘못된 입력 안내 후 메뉴 재출력, 0번 종료, 기능 후 메뉴 복귀 | ✅ | `show_menu()`, `main()` |
| 이전 미션 프롬프트 3개 이상 기본 등록 | ✅ 6개 | `create_default_prompts()` |
| 리스트와 딕셔너리로 저장 (제목, 내용, 카테고리, 즐겨찾기) | ✅ | `make_prompt()` |
| 추가: 빈 값 재입력, 카테고리 선택 또는 직접 입력, 즐겨찾기 기본 False | ✅ | `add_prompt()`, `input_text()`, `choose_category()` |
| 목록: 번호, 카테고리, ⭐ 표시, 없으면 안내, 브랜치에서 작업 후 병합 | ✅ | `show_list()`, `feature/prompt-list` |
| 카테고리별 조회: 없으면 안내 | ✅ | `show_by_category()` |
| 검색: 제목 또는 내용, 없으면 안내 | ✅ | `search_prompt()` |
| 상세 보기: 전체 내용, 잘못된 번호 안내 | ✅ | `show_detail()` |
| 즐겨찾기 추가/해제, 즐겨찾기 목록 | ✅ | `toggle_favorite()`, `show_favorites()` |
| 기능별 함수 분리 | ✅ | 코드 구조 표 |
| 외부 라이브러리 없이 기본 문법만 사용 | ✅ | `import` 문 없음 |
| 의미 있는 커밋 10개 이상, 브랜치 생성·병합 기록 | ✅ | `git log --oneline --graph` |

## 작성자

- 김성태 (GitHub: Sungtae10)
