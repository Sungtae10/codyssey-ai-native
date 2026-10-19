# 평가 계획

> 판정기준은 `eval/판정기준_v2.md`의 **2026-10-15 확정·동결본**을 사용합니다. SK하이닉스 blind evaluation 종료 전에는 결과를 보고 기준을 수정하지 않습니다.

## 평가 설계
- **삼성전자**: calibration / development 기업
- **SK하이닉스**: blind evaluation 기업
- 확장 분석 기업 3곳 (카카오, 현대자동차, 신한지주. 10/19 OpenDART 자동 수집으로 후보 11곳을 돌려 미리 정한 기준 '구체적 AI 약속 3개 이상'을 넘은 기업, `docs/company-expansion-plan.md`): 제품 확장성 데모용입니다. 사람 정답과 비교하지 않고, 평가 수치에는 섞지 않습니다.

## Human Ground Truth

> **10/19 바뀜 (SK하이닉스):** 시간이 부족해 두 사람이 따로 매기지 않고, 김성태·김서원이 함께 공시 원문을 보며 판정기준 v2로 공동 검토해 정답을 고정했습니다(드라이브 `1019_SK하이닉스_Human_Gold_공동합의본`, `eval/gold/skhynix_합의.csv`). 엔진은 그 뒤에 돌리므로 **AI 결과를 보기 전에 정답을 고정한다**는 원칙은 지켰습니다. 따로 매긴 판정이 없어 사람 간 일치율과 Cohen's kappa는 계산하지 않습니다.

아래는 처음 계획입니다. 두 사람이 AI 결과를 보기 전에 독립적으로 판정합니다.
1. 동일한 약속 목록을 각자 판정
2. 사람 간 일치율과 Cohen's kappa 계산
3. 불일치 항목은 원문을 다시 보고 합의
4. 합의본을 Gold Label로 고정
5. 그 뒤 AI 결과와 비교

## 핵심 지표

> **10/19 결과 (SK하이닉스 시범 평가, n=3):** 최종 엔진을 3번 돌려 정답 3건과 비교해 1회차 2/3, 2회차 3/3, 3회차 2/3개가 같았습니다(같은 약속의 반복이라 독립 표본 9개가 아님). 세 번 모두 인용 원문 일치 100%, 근거 없는 실행 판정 0건입니다 (`eval/results/skhynix_runs.md`). 건수가 적어 아래 지표 중 정확도, Macro-F1, 신뢰구간은 주장하지 않습니다.

- Human inter-rater agreement
- Cohen's kappa
- 판정 정확도
- Macro-F1
- 95% Wilson confidence interval
- Confusion matrix
- Citation inclusion
- Citation exact-match verification
- Unsupported execution claims
- Promise extraction recall
- **Comparison coverage**: Gold Label 중 실제 AI 판정 비교까지 간 비율
- **End-to-end accuracy**: AI가 약속을 놓치거나 방향성으로 잘못 분류한 경우까지 실패로 포함한 전체 정확도

조건부 판정 정확도만 높고 coverage가 낮으면 좋은 시스템으로 해석하지 않습니다.

## 개발·평가 분리
삼성전자 결과를 보면서 프롬프트와 규칙을 수정할 수 있습니다. SK하이닉스는 Gold Label 생성 전 AI 결과를 보지 않고, 평가가 시작된 뒤 판정 기준을 바꾸지 않습니다.

## 사용자 평가
자세한 절차는 `docs/user-test-protocol.md`를 따릅니다.
