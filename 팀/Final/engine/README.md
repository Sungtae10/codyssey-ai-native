# AI Promise 엔진

사업보고서에서 AI 약속 문장을 찾고, 이후 보고서에서 실행 근거를 찾아 4가지로 판정하는 코드입니다.
결과는 화면이 읽는 `sample_data.json`과 같은 모양의 파일로 나옵니다.

## 1. 한눈에 보기

| 단계 | 명령 | 하는 일 | 만드는 파일 |
| --- | --- | --- | --- |
| 0 자동 수집 (10/19) | `fetch_dart.py` | OpenDART에서 보고서 3개를 찾아 받고 글로 바꿈, DART 원문 주소 기록 (PDF 대신) | `data/dart/<기업>_<보고서>.txt`, `data/dart/manifest.json` |
| 0 점검 | `doctor` | 설치, 키, PDF(또는 자동 수집 글), 원문 링크, 실제 API 1번 호출 확인 | 없음 |
| 1 수집 | `collect` | PDF에서 읽는 장 3곳을 문장으로 저장 | `data/work/<기업>/collected_*.json` |
| 2~3 추출·분류 | `extract` | AI 약속 문장 고르기, 구체적/방향성 나누기 | `promises.json`, `eval/gold/<기업>_정답매길목록.csv` |
| 4~6 검색·판정·인용 검사 | `judge` | 근거 찾기(최대 3번), 4가지 판정, 원문 대조 | `judged.json` |
| 7 면접 카드 | `card` | 핵심 이슈 3, 답변 소재 3, 역질문 2 | `card.json` |
| 내보내기 | `export` | 화면용 결과 파일 만들기, 화면 규칙 점검 | `data/results/ai_promise_data.json` |
| 평가 | `eval/evaluate.py` | 사람이 만든 정답과 비교, 약속 찾기는 키워드 규칙과도 비교 | `eval/results/results.md` |
| 후보 미리 보기 | `scan` | 후보 기업의 2024 사업보고서 PDF 1개로 수집과 약속 추출만 하고, 구체적 약속이 기준(기본 3개) 이상인지 알려 줌 | `promises.json` |
| 여러 기업 한 번에 (10/19) | `analyze_companies.py` | 자동 수집 → 1~7단계 → 결과 파일 → 화면 미리 보기. 핵심 기업은 화면에 넣지 않고 사람 정답과 비교 | 위 파일 모두, `eval/results/` |

### OpenDART 자동 수집 (10/19 추가, 사람이 PDF를 받는 단계를 대신)

| 누가 | 언제 | 무엇을 | 어떻게 |
| --- | --- | --- | --- |
| 저장소 관리자(김성태) | 처음 한 번 | 키 2개 등록 | GitHub 저장소 Settings > Secrets and variables > Actions에 `OPENDART_API_KEY`(opendart.fss.or.kr에서 개인 즉시 발급, 40자), `OPENAI_API_KEY`. 내 컴퓨터에서 돌릴 때는 `engine/.env`에 같은 이름으로 적습니다. 채팅, 단톡, 드라이브에는 붙이지 않습니다 |
| 팀원 누구나 | 기업을 새로 분석할 때 | GitHub에서 자동 실행 | Actions 탭 > `Engine run` > Run workflow (기업 목록 예: `["kakao","naver"]`). 기업별로 따로 돌고, 결과는 `engine-results/<실행번호>-<기업>` 브랜치에 올라갑니다 (main은 그대로) |
| 팀원 누구나 | 내 컴퓨터에서 | 같은 일을 명령 1줄로 | `python analyze_companies.py kakao naver` (`engine` 폴더에서) |
| 김성태 | 결과 확인 뒤 | 화면에 더하기 | 결과 브랜치의 `data/work/<기업>`과 `data/dart/manifest.json`을 가져와 `python run.py export --companies ...` → `python merge_screen.py ... --write` → Pull Request |

하는 일 (`engine/aipromise/dart.py`)
1. 기업 고유번호: `config.yaml`의 `stock_code`(KRX 목록과 같은 종목코드)로 찾고, 종목코드가 없으면 이름이 정확히 같은 법인만 씁니다. 같은 이름 법인이 여럿이면 필요한 보고서를 실제로 낸 법인만 남기고, 그래도 여럿이면 멈춥니다 (예: 신한은행과 신한지주는 다른 법인).
2. 보고서 고르기: 정기공시 목록에서 `y2024` → `사업보고서 (2024.12)`, `y2025` → `사업보고서 (2025.12)`, `h2026` → `반기보고서 (2026.06)`. 정정 보고서가 있으면 가장 늦게 낸 본문 정정을 쓰고, 첨부서류만 고친 정정은 뒤로 미룹니다.
3. 원문 받기: `document.xml`(ZIP) 안의 본문 XML(`접수번호.xml`)을 글로 바꿉니다. 장 제목은 한 줄로, 큰 장마다 쪽 구분을 넣어 1단계가 PDF와 같은 방법으로 장을 찾습니다. 화면의 원문 링크는 `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=<접수번호>`로 자동으로 채웁니다.
4. 쪽 번호: DART 글의 쪽은 PDF 쪽과 다르므로 결과에 쪽 번호를 남기지 않습니다 (화면에 `p.` 표시 없음).
5. 기록: 수집 기록에 장별 글자 수와 XML 태그 수를 남기고, II장이 3,000자보다 짧으면 (주의)를 찍습니다.

읽는 장 3곳: I. 회사의 개요 > 5. 정관에 관한 사항 / II. 사업의 내용 / IV. 이사의 경영진단 및 분석의견

## 2. 준비 (약 30분)

1. 코드 받기: GitHub의 [ai-promise](https://github.com/Sungtae10/ai-promise) 저장소에서 `Code` → `Download ZIP`으로 받아 풀거나, `git clone https://github.com/Sungtae10/ai-promise`로 받습니다. (`data` 폴더 안의 `pdf` 폴더에 PDF를 넣습니다)
2. 설치
   ```bash
   cd engine
   pip install -r requirements.txt
   ```
   DART-Foresight AI와 같은 버전입니다.
3. 키: `engine/.env.example`을 `engine/.env`로 복사하고 OpenAI 키를 넣습니다. `.env`는 GitHub에 올리지 않고, 채팅과 단톡에도 붙여 넣지 않습니다.
4. PDF: 핵심 2곳의 6개를 DART에서 받아 `data/pdf` 폴더에 아래 이름으로 저장합니다. 시연용 3곳의 9개는 6장의 표를 봅니다.

   | 파일 이름 | 보고서 |
   | --- | --- |
   | samsung_2024.pdf | 삼성전자 사업보고서 (2024.12) |
   | samsung_2025.pdf | 삼성전자 사업보고서 (2025.12) |
   | samsung_2026h1.pdf | 삼성전자 반기보고서 (2026.06) |
   | skhynix_2024.pdf | SK하이닉스 사업보고서 (2024.12) |
   | skhynix_2025.pdf | SK하이닉스 사업보고서 (2025.12) |
   | skhynix_2026h1.pdf | SK하이닉스 반기보고서 (2026.06) |

5. `engine/config.yaml`의 `url` 칸(핵심 6곳, 시연용 9곳)에, DART에서 각 보고서를 열었을 때 주소창의 주소를 붙여 넣습니다. 화면의 "원문 링크"가 됩니다.
6. 코드 점검 (인터넷과 키 없이 가상 회사로 끝까지 돌려 봄)
   ```bash
   cd ..            # 저장소 맨 위
   python tests/test_mock.py
   ```
   마지막 줄에 "시험 통과"가 나오면 됩니다.
7. 시작 전 점검 (설치, 키, PDF, 원문 링크, 실제 API 1번 호출)
   ```bash
   cd engine
   python run.py doctor --company samsung
   ```
   마지막 줄에 "준비 완료"가 나오면 됩니다. "고칠 것"이 나오면 적힌 대로 고친 뒤 다시 실행합니다.
   PDF마다 "장 찾기" 줄에서 읽는 장 3곳이 OK인지 봅니다. "글자가 깨져 보임"이 나오면 7장의 .txt 방법을 씁니다.

## 3. 실행 순서 (팀 일정과 맞춤)

명령은 모두 `engine` 폴더에서 실행합니다. 단계 번호 순서대로 합니다.

> 10/19부터 화면에는 사람이 원문 대조한 검증용 시연 데이터가 있습니다(PR #19). 사용자 테스트가 끝날 때까지 `export`에 `--copy-to`를 붙이지 않습니다. 붙이면 화면 데이터(`app/data/results.json`)를 덮어씁니다.

| 단계 | 명령 | 확인할 것 |
| --- | --- | --- |
| 1. 시작 전 점검 | `python run.py doctor --company samsung` | "준비 완료", 장 찾기 3곳 OK |
| 2. 1건 완주 | `python run.py collect --company samsung`, `extract`, `judge --limit 1`, `card` | 구체적 약속 1건이 근거 검색, 판정, 인용 검사, 면접 카드까지 실제 API로 끝남 |
| 3. 삼성전자 전체 | `python run.py judge --company samsung` (전체), `card`, `export --companies samsung` | "화면 점검 통과". 결과는 `data/results/ai_promise_data.json`에만 남음. 화면에 올리기(`--copy-to`)는 사용자 테스트가 끝난 뒤 |
| 4. SK하이닉스 준비 | `python run.py doctor --company skhynix`, `collect`, `extract` | SK하이닉스 AI 판정 결과와 결과 화면은 Human Validator에게 공유하지 않습니다 |
| 5. SK하이닉스 사람 판정 | 서원님이 올린 SK하이닉스 약속 목록(약속 문장·위치·분류)을 복사해 내 판정을 v2로 매기고 `eval/gold/skhynix_김성태.csv`로 먼저 올리기 | AI 판정을 돌리기 전에 판정했다는 기록. 주의: 판정을 올리기 전에는 서비스의 SK하이닉스 화면과 `app/data/results.json`의 SK하이닉스 부분을 열지 않습니다 (10/19 PR #19로 서원님 판정 1차가 화면에 있음) |
| 6. 합의와 정답 고정 | 서원님 SK하이닉스 정답 표를 `eval/gold/skhynix_서원.csv`로 저장, 판정이 다른 건은 원문을 보며 합의해 `skhynix_합의.csv` | Human Gold 고정 전까지 AI 결과를 보지 않음 |
| 7. SK하이닉스 AI 판정 | `python run.py judge --company skhynix`, `card`, `export --companies samsung skhynix` | "화면 점검 통과". 화면에 올리기는 사용자 테스트가 끝난 뒤 |
| 8. 평가 | `python ../eval/evaluate.py` | `eval/results/results.md` |
| 9. 시간이 남으면 | 시연용 기업 3곳(카카오, 신한은행, NAVER) 실행 (6장) | 기업마다 구체적 약속 3개 이상인지, 원문 대조 |

**결과 올리기** (둘 중 하나)
- git을 쓰면: `app/data/results.json`, `data/work`, `data/results`, `eval/gold`를 커밋하고 main에 올립니다. 올리면 Vercel이 서비스 주소를 다시 배포합니다.
- git이 어려우면: `app/data/results.json`과 `data/work` 폴더를 압축해 Claude와의 채팅에 첨부합니다. 저장소에 대신 올립니다. (`.env`와 PDF는 넣지 않습니다)

한 번에 돌릴 때: `python run.py all --company samsung` (1~7단계)

배포 전 점검만 할 때: `python run.py check --file <결과 파일>` ("문제 없음"이 나와야 합니다)

## 4. 정답 파일 만드는 법 (eval/gold)

판정은 `eval/판정기준_v2.md`(2026-10-15 확정·동결)를 따릅니다. 엔진의 추출 지시문(`aipromise/prompts.py`의 `EXTRACT_SYSTEM`)과 판정 지시문(`JUDGE_SYSTEM`)도 같은 규칙을 써서, 사람과 AI가 같은 기준으로 약속을 고르고 판정합니다. v1(`eval/판정기준_v1.md`)은 바뀐 과정을 남기려고 그대로 둡니다.

- v2에서 바뀐 3가지: 문장 안에 AI 관련 말이 있어야 약속, 특정 대상이 있어야 구체적 약속, 한 문장의 여러 대상 중 일부만 확인되면 일부 확인
- `extract.py`는 AI가 고른 문장 중 검색어(AI, 인공지능 등)가 없는 문장을 약속에서 빼고, `promises.json`의 `dropped`에 이유를 남깁니다.
- `evaluate.py`도 같은 검색어로, 사람 약속 목록에서 AI 관련 말이 없는 문장은 "약속을 찾은 비율"에서 빼고 뺀 개수를 결과표에 적습니다. (예: 연습 5번)

| 파일 | 내용 |
| --- | --- |
| `skhynix_김성태.csv`, `skhynix_서원.csv` | 서원님이 직접 찾은 SK하이닉스 약속 목록에 각자 따로 판정을 채운 파일 (일치도 계산용). promise_id 칸은 없어도 됩니다 |
| `skhynix_합의.csv` | 판정이 다른 건을 원문을 보며 정한 최종 정답 |
| `samsung_합의.csv` | 삼성전자 정답 ("개발에 쓴 기업"으로 따로 표시됨) |
| `skhynix_사람약속목록.csv`, `samsung_사람약속목록.csv` | 사람이 직접 찾은 약속 문장 ("약속 문장" 칸). AI가 약속을 빠뜨렸는지 재는 데 씁니다. SK하이닉스는 이 파일이 없으면 promise_id 칸이 빈 `skhynix_서원.csv`를 대신 씁니다 |

- 판정 칸에는 `근거 확인`, `일부 확인`, `공시에서 확인 불가`, `회사가 미추진으로 공시` 중 하나를 그대로 씁니다.
- 판정은 분류가 "구체적"인 줄만 매깁니다. 분류가 틀렸다고 보면 "메모" 칸에 적습니다.
- 정답 파일에 promise_id가 있으면 번호로, 없으면 "약속 문장"으로 AI 약속과 맞춥니다 (띄어쓰기 무시, 한쪽이 다른 쪽을 포함하거나 비슷한 정도 0.6 이상). 사람은 구체적으로 봤는데 AI가 방향성으로 둔 약속은 판정 비교에서 빼고 `errors_<기업>.csv`에 원인 "분류가 다름"으로 적습니다.
- 엑셀에서 저장할 때는 "CSV UTF-8" 형식으로 저장합니다. (그냥 "CSV"로 저장했거나 구글 시트에서 CSV로 받은 파일도 읽습니다)
- 공유 폴더의 시트를 CSV로 받으면 맨 위 안내 줄, "예" 줄, "약속 문장 (원문 그대로)" 같은 칸 이름이 그대로 남는데, 평가 코드가 알아서 건너뛰고 읽습니다. 연습5건 시트는 `samsung_사람약속목록.csv`, 서원님 약속 목록은 `skhynix_사람약속목록.csv`로 저장합니다.

## 5. 화면에 넣기

- `export --copy-to ../app/data/results.json`은 화면 데이터를 통째로 덮어씁니다. 사용자 테스트가 끝나기 전에는 쓰지 않습니다 (3장).
- 10/19부터 엔진 결과 기업만 더할 때는 `python merge_screen.py --engine ../data/results/ai_promise_data.json --companies kakao shinhanbank naver --write`를 씁니다. 사람 대조 기업(삼성·SK)은 그대로 두고, 더한 기업에는 `data_mode: engine`이 붙어 화면이 기업별로 "AI 엔진 결과(사람 검토 전)"라고 보여줍니다. 섞이면 맨 위 안내 띠와 안내 문구도 기업 이름으로 나눠 고치고, 화면 점검에서 막는 문제가 있으면 쓰지 않습니다.
- 화면 점검에서 문제가 나오면(`(주의)` 항목 제외) 복사하지 않고 그 사실을 알려 줍니다.
- 엔진 결과 파일은 `meta.is_sample`이 false라서, 화면에 올리면 맨 위 안내 띠가 사라집니다.

## 6. 시연용 기업 (카카오, 신한은행, NAVER)

핵심 2곳과 사용자 5명 테스트를 먼저 끝내고, 시간이 남을 때만 합니다 (`docs/final-sprint.md`). 엔진 코드에는 회사마다 다른 부분이 없습니다. `config.yaml`의 `candidates`에 3곳이 적혀 있고, `--company`나 `--companies`에 이름(`kakao`, `shinhanbank`, `naver`)을 적으면 핵심 기업과 같은 순서로 돕니다. PDF는 서원님이 드라이브 공통 폴더의 `1019_추가기업_PDF`에 올립니다.

| 파일 이름 | 보고서 |
| --- | --- |
| kakao_2024.pdf | 카카오 사업보고서 (2024.12) |
| kakao_2025.pdf | 카카오 사업보고서 (2025.12) |
| kakao_2026h1.pdf | 카카오 반기보고서 (2026.06) |
| shinhan_2024.pdf | 신한은행 사업보고서 (2024.12) |
| shinhan_2025.pdf | 신한은행 사업보고서 (2025.12) |
| shinhan_2026h1.pdf | 신한은행 반기보고서 (2026.06) |
| naver_2024.pdf | NAVER 사업보고서 (2024.12) |
| naver_2025.pdf | NAVER 사업보고서 (2025.12) |
| naver_2026h1.pdf | NAVER 반기보고서 (2026.06) |

| 순서 | 할 일 | 확인할 것 |
| --- | --- | --- |
| 1 | PDF 9개를 `data/pdf`에 넣고, `config.yaml`의 시연용 `url` 9곳에 DART 주소를 붙여 넣기 | 파일 이름이 설정과 같은지 |
| 2 | `python run.py all --company kakao` (`shinhanbank`, `naver`도 같게). 미리 보기만 하려면 `python run.py scan --company kakao` (2024 사업보고서 1개로 약속 추출까지) | 구체적 약속 3개 이상인지, 판정과 근거 문장 |
| 3 | 브랜치에서 `python run.py export --companies kakao shinhanbank naver` 뒤 `python merge_screen.py --engine ../data/results/ai_promise_data.json --companies kakao shinhanbank naver --write` 하고 Pull Request를 올림 (10/19 바뀜: 삼성·SK를 덮어쓰지 않음) (Vercel 미리보기 주소가 생기고 main은 그대로) | "화면 점검 통과" |
| 4 | 서원님이 미리보기 주소에서 시연 기업의 약속을 원문과 대조해 확인 표에 적음 | 화면 안내 문구가 "팀이 원문과 대조해 확인했어요"라서, 확인을 먼저 끝냄 |
| 5 | 확인이 끝난 기업만 남기고(빠질 기업은 목록에서 빼고 다시 `export`) main에 합침 | "화면 점검 통과", 사람 정답과 비교하지 않은 기업이라는 표시(`check_note`) |

- 구체적 약속이 3개보다 적은 기업은 `export` 목록에서 빼고 단톡에 알립니다.
- SK하이닉스(`skhynix`)는 사람 정답 합의가 끝난 뒤에 `export` 목록에 넣습니다.
- 사용자 테스트 링크를 보내는 중에는 화면을 바꾸지 않습니다 (저장소 README 6장). 시연용 기업은 테스트 응답을 다 받은 뒤에 올립니다.
- 시연용 기업은 평가 숫자(정확도, 일치도)에 넣지 않습니다.

## 7. 문제가 생기면

| 증상 | 할 일 |
| --- | --- |
| "장을 못 찾음" | 보고서에 원래 없는 장이면 그대로 둡니다. 있는데 못 찾았으면 `config.yaml`의 `section_pages`에 쪽 번호를 적습니다 |
| 약속 문장에 띄어쓰기가 하나 더 들어감 (예: "외 관") | PDF에서 단어 중간에 줄이 바뀐 자리입니다. 인용 검사는 띄어쓰기를 무시하므로 판정에는 영향이 없습니다. 화면에서 많이 보이면 DART 화면에서 장별 글을 복사해 `.txt`로 저장하고, `config.yaml`의 `pdf` 이름을 그 `.txt`로 바꿔 `collect`부터 다시 돌립니다 |
| JSON을 읽지 못했다는 오류 | 한 번 더 실행합니다. `data/work/<기업>/llm_log.jsonl`에서 모델 응답을 확인합니다 |
| `429` 오류 | 사용량 제한입니다. 1분 쉬고 다시 실행합니다 |
| 근거를 너무 못 찾음 | `config.yaml`의 `max_candidates`를 24 → 36, `top_windows`를 8 → 12로 늘립니다 |
| 정확도가 80%에 못 미침 | `eval/results/errors_<기업>.csv`의 "원인" 칸을 채웁니다 (근거를 못 찾음 / 판정이 다름 / 분류가 다름). 가장 많은 원인부터 고칩니다. 판정이 문제면 `judge_model`만 더 좋은 모델로 바꿔 `judge`, `card`, `evaluate`를 다시 돌립니다. 보고서에는 "같은 정답으로 고친 뒤 다시 잰 값"이라고 적습니다 |

## 8. 코드에 들어 있는 규칙

- AI는 문장을 고쳐 쓰지 않고 문장 번호만 고릅니다. 화면에 나가는 약속 문장과 근거 문장은 원문 그대로입니다.
- 인용 검사: 근거 문장이 읽은 장의 원문에 그대로 있는지(띄어쓰기 무시) 코드로 확인하고, 통과한 근거만 화면에 내보냅니다.
- 근거가 필요한 판정(근거 확인, 일부 확인, 미추진 공시)인데 통과한 근거가 없으면 "공시에서 확인 불가"로 낮추고 기록을 남깁니다.
- "공시에서 확인 불가"의 판정 이유는 정해진 문장으로 씁니다. ("읽은 공시 범위(…)에서 관련 내용을 찾지 못했습니다.")
- 판정 이유와 면접 카드에서 단정 표현("거짓", "AI 워싱" 등)을 막습니다.
- 답변 소재는 "근거 확인"과 "일부 확인" 약속만 쓰고, 근거 링크는 데이터에서 붙입니다.
- 모든 LLM 호출(약속 추출, 판정, 방향성 약속의 관련 활동, 면접 카드)의 입력과 출력을 `data/work/<기업>/llm_log.jsonl`에 남깁니다. 임베딩 호출은 남기지 않습니다. "AI Agent 실행 기록" 증빙으로 씁니다.
- 검색 기록은 `data/results/search_log.json`에 따로 남깁니다. 보고서와 발표의 예시 1건으로 씁니다.

## 9. 출처와 AI 사용

- 검색 구성(LangChain, ChromaDB, OpenAI 임베딩)은 DART-Foresight AI(https://github.com/Sungtae10/dart-foresight-ai)를 바탕으로 했습니다. 그 평가에서 검색이 약점(Hit@4 14/20)이어서, 이번에는 의미 검색에 키워드 검색을 더했습니다.
- 이 엔진 코드의 첫 버전은 AI 도구(Claude)로 작성했습니다. 실행과 점검, 수정은 김성태가 합니다.
