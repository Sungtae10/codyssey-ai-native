# 실행 캡처 (2026-09-18, 실데이터)

실행 환경: Windows, Python 3.13, 모델 gpt-4o-mini. 소스: Google News RSS(IT·경제·사회), 한겨레 RSS, 경향 IT RSS, ZDNet Korea 크롤링.

| # | 파일 | 명령 | 확인 내용 |
|---|---|---|---|
| 01 | 01_fetch_crawl.png | `fetch --source crawl --limit 10` | ZDNet 섹션 크롤링 10건 신규 수집 (방법 2) |
| 02 | 02_fetch_rss_duplicate_skip.png | `fetch --source rss --limit 20` (2회차) | 4개 RSS 64건 처리, 신규 2건, 중복스킵 62건 (skip 정책 동작) |
| 03 | 03_clean.png | `clean` | raw 76건 → clean 33건 저장, 43건 제외(본문 100자 미만) |
| 04 | 04_summarize_progress.png | `summarize --unsummarized --limit 20` | 기사별 AI 호출 진행 로그 |
| 05 | 05_summarize_done.png | (위 명령 완료) | 요약 완료 20건 성공, 0건 실패 |
| 06 | 06_analyze.png | `analyze --date-from 2026-09-01 --date-to 2026-09-18 --category IT` | 트렌드·키워드·공통점·차이점·이슈·시사점 6개 항목 출력 |
| 07 | 07_report_metrics.png | `report` | 품질지표 3개, 카테고리 TOP 5, 키워드 TOP 10, 감성 분포 |
| 08 | 08_report_insight.png | (위 명령 계속) | AI 인사이트 섹션, output/report.md 저장 |
| 09 | 09_export_list.png | `export --format csv --status summarized`, `export --format xlsx`, `list --category IT` | CSV 20건(요약본 필터), XLSX 33건, 목록 페이지네이션 |
| 10 | 10_show.png | `show --id 74` | 본문·요약·키워드·감성 상세 조회 |
| 11 | chart_category.png | (report 가 생성) | 카테고리별 뉴스 수 막대차트, 한글 폰트 적용 |
| 12 | chart_daily.png | (report 가 생성) | 일자별 수집 추이 선차트 |

11·12번은 로컬 `output/` 폴더의 PNG 2장을 이 폴더에 복사해서 함께 올린다.
