# AI Promise 엔진

사업보고서에서 AI 약속 문장을 찾고, 이후 보고서에서 실행 근거를 찾아 4가지로 판정하는 코드입니다.
결과는 화면이 읽는 `sample_data.json`과 같은 모양의 파일로 나옵니다.

## 1. 한눈에 보기

| 단계 | 명령 | 하는 일 | 만드는 파일 |
| --- | --- | --- | --- |
| 0 점검 | `doctor` | 설치, 키, PDF, 원문 링크, 실제 API 1번 호출 확인 | 없음 |
| 1 수집 | `collect` | PDF에서 읽는 장 3곳을 문장으로 저장 | `data/work/<기업>/collected_*.json` |
| 2~3 추출·분류 | `extract` | AI 약속 문장 고르기, 구체적/방향성 나누기 | `promises.json`, `eval/gold/<기업>_정답매길목록.csv` |
| 4~6 검색·판정·인용 검사 | `judge` | 근거 찾기(최대 3번), 4가지 판정, 원문 대조 | `judged.json` |
| 7 면접 카드 | `card` | 핵심 이슈 3, 답변 소재 3, 역질문 2 | `card.json` |
| 내보내기 | `export` | 화면용 결과 파일 만들기, 화면 규칙 점검 | `data/results/ai_promise_data.json` |
| 평가 | `eval/evaluate.py` | 사람이 만든 정답과 비교 | `eval/results/results.md` |

읽는 장 3곳: I. 회사의 개요 > 5. 정관에 관한 사항 / II. 사업의 내용 / IV. 이사의 경영진단 및 분석의견

## 2. 준비 (약 30분)

1. 이 압축 파일의 `engine`, `eval`, `tests` 폴더와 `.gitignore`를 저장소 맨 위에 넣습니다. (`data` 폴더는 처음 실행할 때 생깁니다)
2. 설치
   ```bash
   cd engine
   pip install -r requirements.txt
   ```
   DART-Foresight AI와 같은 버전입니다.
3. 키: `engine/.env.example`을 `engine/.env`로 복사하고 OpenAI 키를 넣습니다. `.env`는 GitHub에 올리지 않습니다.
4. PDF 6개: DART에서 받아 `data/pdf` 폴더에 아래 이름으로 저장합니다.

   | 파일 이름 | 보고서 |
   | --- | --- |
   | samsung_2024.pdf | 삼성전자 사업보고서 (2024.12) |
   | samsung_2025.pdf | 삼성전자 사업보고서 (2025.12) |
   | samsung_2026h1.pdf | 삼성전자 반기보고서 (2026.06) |
   | skhynix_2024.pdf | SK하이닉스 사업보고서 (2024.12) |
   | skhynix_2025.pdf | SK하이닉스 사업보고서 (2025.12) |
   | skhynix_2026h1.pdf | SK하이닉스 반기보고서 (2026.06) |

5. `engine/config.yaml`의 `url` 6곳에, DART에서 각 보고서를 열었을 때 주소창의 주소를 붙여 넣습니다. 화면의 "원문 링크"가 됩니다.
6. 코드 점검 (인터넷과 키 없이 가상 회사로 끝까지 돌려 봄)
   ```bash
   cd ..            # 저장소 맨 위
   python tests/test_mock.py
   ```
   마지막 줄에 "시험 통과"가 나오면 됩니다.
7. 시작 전 점검 (설치, 키, PDF 6개, 원문 링크, 실제 API 1번 호출)
   ```bash
   cd engine
   python run.py doctor --company samsung
   ```
   마지막 줄에 "준비 완료"가 나오면 됩니다. "고칠 것"이 나오면 적힌 대로 고친 뒤 다시 실행합니다.

## 3. 실행 순서 (팀 일정과 맞춤)

명령은 모두 `engine` 폴더에서 실행합니다.

| 날짜 | 명령 | 확인할 것 |
| --- | --- | --- |
| 10/10 | `python run.py doctor --company samsung` | "준비 완료" |
| 10/10 | `python run.py collect --company samsung` (skhynix도) | 장의 시작 쪽과 끝 쪽이 PDF 목차와 맞는지. 관문 1에서 손으로 찾은 약속 문장이 `collected_y2024.json`에 있는지 |
| 10/10 | `python run.py extract --company samsung` (skhynix도) | 화면에 찍힌 약속 목록. `eval/gold/skhynix_정답매길목록.csv`는 10/11 밤까지 서원님에게 전달 |
| 10/10 | **1건 완주:** `python run.py judge --company samsung --limit 1` 다음 `card`, `export --companies samsung` | 구체적 약속 1건이 근거 검색, 판정, 인용 검사, 면접 카드까지 실제 API로 끝남. 1건이라 화면 점검에서 개수 부족 문제가 나오는 것은 정상 |
| 10/10 밤~10/11 | `python run.py judge --company samsung` (전체) | 판정 개수와 ※ 표시가 붙은 약속 |
| 10/12 | `python run.py card --company samsung` 다음 `python run.py export --companies samsung --copy-to <화면의 데이터 파일 경로>` | "화면 점검 통과" |
| 10/12 | 내 SK하이닉스 판정을 `eval/gold/skhynix_김성태.csv`로 저장하고 저장소에 먼저 올리기 | AI를 돌리기 전에 판정했다는 기록 |
| 10/13 | `python run.py judge --company skhynix`, `python run.py card --company skhynix`, `python run.py export --companies samsung skhynix --copy-to <경로>` | "화면 점검 통과" |
| 10/14 | `python ../eval/evaluate.py` | `eval/results/results.md` |

한 번에 돌릴 때: `python run.py all --company samsung` (1~7단계)

배포 전 점검만 할 때: `python run.py check --file <결과 파일>` ("문제 없음"이 나와야 합니다)

## 4. 정답 파일 만드는 법 (eval/gold)

판정은 `eval/판정기준_v2.md`(10/12 초안, 김서원과 확인 후 확정)를 따릅니다. 엔진의 추출 지시문(`aipromise/prompts.py`의 `EXTRACT_SYSTEM`)과 판정 지시문(`JUDGE_SYSTEM`)도 같은 규칙을 써서, 사람과 AI가 같은 기준으로 약속을 고르고 판정합니다. v1(`eval/판정기준_v1.md`)은 바뀐 과정을 남기려고 그대로 둡니다.

- v2에서 바뀐 3가지: 문장 안에 AI 관련 말이 있어야 약속, 특정 대상이 있어야 구체적 약속, 한 문장의 여러 대상 중 일부만 확인되면 일부 확인
- `extract.py`는 AI가 고른 문장 중 검색어(AI, 인공지능 등)가 없는 문장을 약속에서 빼고, `promises.json`의 `dropped`에 이유를 남깁니다.
- `evaluate.py`도 같은 검색어로, 사람 약속 목록에서 AI 관련 말이 없는 문장은 "약속을 찾은 비율"에서 빼고 뺀 개수를 결과표에 적습니다. (예: 연습 5번)

| 파일 | 내용 |
| --- | --- |
| `skhynix_김성태.csv`, `skhynix_서원.csv` | `skhynix_정답매길목록.csv`를 복사해 각자 판정을 채운 파일 (일치도 계산용) |
| `skhynix_합의.csv` | 판정이 다른 건을 원문을 보며 정한 최종 정답 |
| `samsung_합의.csv` | 삼성전자 정답 ("개발에 쓴 기업"으로 따로 표시됨) |
| `skhynix_사람약속목록.csv`, `samsung_사람약속목록.csv` | 사람이 직접 찾은 약속 문장 ("약속 문장" 칸). AI가 약속을 빠뜨렸는지 재는 데 씁니다 |

- 판정 칸에는 `근거 확인`, `일부 확인`, `공시에서 확인 불가`, `회사가 미추진으로 공시` 중 하나를 그대로 씁니다.
- 판정은 분류가 "구체적"인 줄만 매깁니다. 분류가 틀렸다고 보면 "메모" 칸에 적습니다.
- 엑셀에서 저장할 때는 "CSV UTF-8" 형식으로 저장합니다. (그냥 "CSV"로 저장했거나 구글 시트에서 CSV로 받은 파일도 읽습니다)
- 공유 폴더의 시트를 CSV로 받으면 맨 위 안내 줄, "예" 줄, "약속 문장 (원문 그대로)" 같은 칸 이름이 그대로 남는데, 평가 코드가 알아서 건너뛰고 읽습니다. 연습5건 시트는 `samsung_사람약속목록.csv`, 서원님 약속 목록은 `skhynix_사람약속목록.csv`로 저장합니다.

## 5. 화면에 넣기

- `export --copy-to <경로>`는 결과 파일을 화면의 데이터 파일 자리에 같은 이름으로 복사합니다. 수민님 화면이 읽는 `sample_data.json`의 위치를 적으면 됩니다.
- 결과 파일은 `meta.is_sample`이 false라서 "예시 데이터입니다" 띠가 사라집니다.
- 수민님 압축본을 새로 받아 app 폴더를 바꿀 때마다 이 복사를 다시 합니다.

## 6. 문제가 생기면

| 증상 | 할 일 |
| --- | --- |
| "장을 못 찾음" | 보고서에 원래 없는 장이면 그대로 둡니다. 있는데 못 찾았으면 `config.yaml`의 `section_pages`에 쪽 번호를 적습니다 |
| 약속 문장에 띄어쓰기가 하나 더 들어감 (예: "외 관") | PDF에서 단어 중간에 줄이 바뀐 자리입니다. 인용 검사는 띄어쓰기를 무시하므로 판정에는 영향이 없습니다. 화면에서 많이 보이면 DART 화면에서 장별 글을 복사해 `.txt`로 저장하고, `config.yaml`의 `pdf` 이름을 그 `.txt`로 바꿔 `collect`부터 다시 돌립니다 |
| JSON을 읽지 못했다는 오류 | 한 번 더 실행합니다. `data/work/<기업>/llm_log.jsonl`에서 모델 응답을 확인합니다 |
| `429` 오류 | 사용량 제한입니다. 1분 쉬고 다시 실행합니다 |
| 근거를 너무 못 찾음 | `config.yaml`의 `max_candidates`를 24 → 36, `top_windows`를 8 → 12로 늘립니다 |
| 정확도가 80%에 못 미침 | `eval/results/errors_<기업>.csv`의 "원인" 칸을 채웁니다 (근거를 못 찾음 / 판정이 다름 / 분류가 다름). 가장 많은 원인부터 고칩니다. 판정이 문제면 `judge_model`만 더 좋은 모델로 바꿔 `judge`, `card`, `evaluate`를 다시 돌립니다. 보고서에는 "같은 정답으로 고친 뒤 다시 잰 값"이라고 적습니다 |

## 7. 코드에 들어 있는 규칙

- AI는 문장을 고쳐 쓰지 않고 문장 번호만 고릅니다. 화면에 나가는 약속 문장과 근거 문장은 원문 그대로입니다.
- 인용 검사: 근거 문장이 읽은 장의 원문에 그대로 있는지(띄어쓰기 무시) 코드로 확인하고, 통과한 근거만 화면에 내보냅니다.
- 근거가 필요한 판정(근거 확인, 일부 확인, 미추진 공시)인데 통과한 근거가 없으면 "공시에서 확인 불가"로 낮추고 기록을 남깁니다.
- "공시에서 확인 불가"의 판정 이유는 정해진 문장으로 씁니다. ("읽은 공시 범위(…)에서 관련 내용을 찾지 못했습니다.")
- 판정 이유와 면접 카드에서 단정 표현("거짓", "AI 워싱" 등)을 막습니다.
- 답변 소재는 "근거 확인"과 "일부 확인" 약속만 쓰고, 근거 링크는 데이터에서 붙입니다.
- 모든 AI 호출의 입력과 출력을 `data/work/<기업>/llm_log.jsonl`에 남깁니다. "AI Agent 실행 기록" 증빙으로 씁니다.
- 검색 기록은 `data/results/search_log.json`에 따로 남깁니다. 보고서와 발표의 예시 1건으로 씁니다.

## 8. 출처와 AI 사용

- 검색 구성(LangChain, ChromaDB, OpenAI 임베딩)은 DART-Foresight AI(https://github.com/Sungtae10/dart-foresight-ai)를 바탕으로 했습니다. 그 평가에서 검색이 약점(Hit@4 14/20)이어서, 이번에는 의미 검색에 키워드 검색을 더했습니다.
- 이 엔진 코드의 첫 버전은 AI 도구(Claude)로 작성했습니다. 실행과 점검, 수정은 김성태가 합니다.
