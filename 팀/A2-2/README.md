# codyssey-a2-news-pipeline

코디세이 A2-2 팀프로젝트: 뉴스 자동 수집 → 정제 → AI 요약 → 인사이트 분석 → 리포트/내보내기까지 하나의 CLI로 동작하는 데이터 파이프라인.

## 팀 구성과 역할

| 팀원 | 역할 | 소유 파일 |
|---|---|---|
| A (김성태, 팀장) | 뼈대·저장소·통합·문서 | `main.py`, `config.py`, `db.py`, `seed_sample.py`, `README.md`, `AI_LOG.md` |
| B (박수민) | 데이터 수집·정제 | `fetcher.py`, `cleaner.py` |
| C (한다혜) | AI 요약·분석·감성 | `ai_client.py`, `analyzer.py` |
| D (김범근) | 시각화·리포트·내보내기·조회 | `report.py`, `output/` |

남의 파일을 고쳐야 하면 직접 수정하지 말고 소유자에게 요청한다. `main.py`는 `cmd_*` 함수 본문만 각자 수정 가능하고 파서 정의는 팀장이 관리한다.

## 설치

```bash
git clone https://github.com/Sungtae10/codyssey-a2-news-pipeline.git
cd codyssey-a2-news-pipeline
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # API 키 입력 (절대 커밋 금지)
cp config.example.json config.json   # 소스 URL·정책 수정
python seed_sample.py                # 개발용 샘플 20건 적재
```

Linux 에서 차트 한글이 깨지면: `sudo apt install fonts-nanum && rm -rf ~/.cache/matplotlib`

## 실행 흐름

```bash
python main.py fetch --source rss --limit 20          # 수집 (raw)
python main.py fetch --source crawl --limit 10
python main.py clean                                   # 정제 (clean)
python main.py summarize --unsummarized --limit 10    # AI 요약 (+키워드, 감성)
python main.py analyze --date-from 2026-09-01 --date-to 2026-09-15 --category IT
python main.py report --out output/report.md          # 차트 2종 + 품질지표 + TOP N + 인사이트
python main.py export --format csv --status summarized
python main.py export --format xlsx
python main.py list --category IT --page 1 --page-size 10   # 보너스
python main.py show --id 1                                   # 보너스
```

각 커맨드 옵션은 `python main.py <command> --help` 로 확인.

## 테스트

```bash
python -m unittest discover -s tests -t .
```

## 구조

```
main.py        argparse 서브커맨드 라우팅
config.py      config.json + .env + logging
db.py          SQLite (raw_articles, clean_articles, summaries, analyses)
fetcher.py     RSS(feedparser) + 크롤링(requests, BeautifulSoup)
cleaner.py     필수필드 검증, 정규화, 날짜 통일, 결측 처리
ai_client.py   AI API 호출 래퍼 (JSON 응답 강제, 실패 시 로깅 후 스킵)
analyzer.py    요약·분석·감성 프롬프트와 저장
report.py      matplotlib 차트, 리포트, csv/xlsx/jsonl 내보내기
seed_sample.py 개발용 샘플 데이터 적재
tests/         단위 테스트 (API·DB 없이 실행)
```

- 저장소: SQLite `data/news.db` (raw 와 clean 은 별도 테이블로 분리 저장)
- 중복 정책: `config.json` 의 `duplicate_policy` = `skip` | `upsert` (기준: url)
- 로그: 콘솔 + `logs/app.log` (INFO / WARNING / ERROR)

## 뉴스 소스와 크롤링 정책

- 방법 1 (RSS): `config.json` 의 `sources.rss` 에 카테고리별 URL 등록. 기본은 Google News RSS.
- 방법 2 (크롤링): `sources.crawl` 의 섹션 페이지(기본 ZDNet Korea IT)에서 기사 링크를 추출해 본문 수집.
- 대상 사이트 `robots.txt` 확인 완료(hani.co.kr, zdnet.co.kr, 2026-09-16 박수민): 허용 경로만 수집, User-Agent `CodysseyNewsBot/1.0` 명시
- 요청 간 지연 `request_delay_sec` (기본 1초), 타임아웃 `request_timeout_sec` (기본 10초), 재시도 최대 2회, User-Agent 명시, 1회 실행 최대 100건.

## 정기 실행 (보너스)

Linux/Mac `crontab -e`:

```
0 7 * * * cd /path/codyssey-a2-news-pipeline && .venv/bin/python main.py fetch --limit 30 && .venv/bin/python main.py clean && .venv/bin/python main.py summarize --unsummarized --limit 30 >> logs/cron.log 2>&1
0 8 * * * cd /path/codyssey-a2-news-pipeline && .venv/bin/python main.py report --out output/report.md >> logs/cron.log 2>&1
```

Windows: 작업 스케줄러 → 기본 작업 만들기 → 트리거 "매일 07:00" → 동작 "프로그램 시작" → 프로그램 `python.exe`, 인수 `main.py fetch --limit 30`, 시작 위치는 프로젝트 폴더.

## Git 규칙

- `main` 은 PR 로만 병합 (ruleset 적용). 브랜치: `feature/fetcher`, `feature/ai`, `feature/report`
- 함수 1개 완성마다 커밋, 하루 1회 이상 PR
- `.env`, `config.json`, `data/news.db`, `output/`, `logs/` 는 커밋 금지 (`.gitignore` 등록됨)

## 샘플 데이터

`data/sample_articles.json` 의 20건은 개발용으로 팀에서 작성한 가상 기사이며 실제 언론 기사가 아니다.
