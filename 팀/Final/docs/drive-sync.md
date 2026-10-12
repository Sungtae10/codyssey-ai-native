# Google Drive ↔ GitHub 동기화 기준

2026-10-12 기준으로 Drive 협업 자료와 GitHub 구현물을 다음처럼 대응합니다.

| Google Drive | GitHub |
| --- | --- |
| 공통 `sample_data.json` | `tests/sample_data.json`, `app/data/sample-data.js` |
| 공통 `screen_spec_ko.md` | `app/README.md`, `app/js/app.js` |
| 공통 `1012_김성태_판정기준_v2(초안)` | `eval/판정기준_v2.md` |
| 김성태 `1012_김성태_화면_데이터연결.zip` | `app/` |
| 김서원 `1011_서원_삼성전자_연습판정.xlsx` | 원본은 Drive 보존. 평가용 CSV만 blind protocol에 맞춰 `eval/gold/`에 저장 |
| 김성태 엔진/평가 코드 | `engine/`, `eval/`, `tests/` |

## 원칙
- Drive: 팀 협업 문서, 원본 스프레드시트, 디자인/영상 중간 산출물
- GitHub: 실행 코드, 버전 고정된 방법론, 익명화된 평가 데이터, 재현 가능한 결과

## 아직 GitHub에 없는 핵심 산출물
- 실제 `app/data/results.json`
- SK하이닉스 blind Gold Label
- 사용자 테스트 실측 결과
- (관문 2를 통과했을 때만) 시연용 추가 기업의 실제 결과
- 서준용 디자인 시안 원본 zip (화면 반영은 PR #9로 완료, `app/css/style.css`)

판정기준 v2가 팀 합의로 확정되면 Drive와 GitHub 제목·내용을 같은 버전으로 맞춥니다.
