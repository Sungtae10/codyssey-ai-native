# Google Drive ↔ GitHub 동기화 기준

2026-10-12 기준으로 Drive 협업 자료와 GitHub 구현물을 다음처럼 대응합니다. 표의 마지막 2줄은 10/19에 더했습니다.

| Google Drive | GitHub |
| --- | --- |
| 공통 `sample_data.json` | `tests/sample_data.json`, `app/data/sample-data.js` |
| 공통 `screen_spec_ko.md` | `app/README.md`, `app/js/app.js` |
| 공통 `1015_김성태_판정기준_v2(확정·동결)` | `eval/판정기준_v2.md` |
| 김성태 `1012_김성태_화면_데이터연결.zip` | `app/` |
| 김서원 `1011_서원_삼성전자_연습판정.xlsx` | 원본은 Drive 보존. 평가용 CSV만 blind protocol에 맞춰 `eval/gold/`에 저장 |
| 김성태 엔진/평가 코드 | `engine/`, `eval/`, `tests/` |
| `1019_SK하이닉스_Human_Gold_공동합의본` | `eval/gold/skhynix_합의.csv` |
| 공통 `1020_발표자료_영상` (발표자료, 3분 시연 영상) | README 14장의 링크 |

## 원칙
- Drive: 팀 협업 문서, 원본 스프레드시트, 디자인/영상 중간 산출물
- GitHub: 실행 코드, 버전 고정된 방법론, 익명화된 평가 데이터, 재현 가능한 결과

## 아직 GitHub에 없는 핵심 산출물 (10/19 23시 기준)
- 사용자 테스트 실측 결과 (설문 응답을 받는 중)
- 발표자료와 3분 시연 영상 (드라이브 `1020_발표자료_영상`에 10/20에 올림)
- 서준용 디자인 시안 원본 zip (화면 반영은 PR #9로 완료, `app/css/style.css`)

지금 GitHub에 있는 것: 화면 결과 파일 `app/data/results.json`, SK하이닉스 공동 검토 정답 `eval/gold/skhynix_합의.csv`, 확장 분석 기업 3곳(카카오, 현대자동차, 신한지주)의 엔진 결과 `data/work/` (PR #39).

판정기준 v2는 2026-10-15 확정·동결했습니다. Drive와 GitHub는 같은 v2를 사용하며, SK하이닉스 blind evaluation 종료 전에는 기준을 바꾸지 않습니다.
