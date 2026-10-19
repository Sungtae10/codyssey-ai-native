# 후속연구 실행계획

판정기준 v2는 **2026-10-15 확정·동결본**을 사용합니다.

## RQ1. Human reliability
SK하이닉스에서 김서원·김성태가 AI 결과를 보기 전에 같은 약속 목록을 독립 판정합니다.

보고:
- N
- 단순 일치율
- Cohen's kappa
- 판정별 불일치

불일치만 원문을 재검토해 합의 Gold Label을 만듭니다.

## RQ2. AI vs Human Gold
Gold Label을 고정한 뒤에만 SK하이닉스 AI 판정을 실행합니다.

보고:
- Accuracy
- Macro-F1
- 판정별 Precision / Recall / F1
- Confusion matrix
- 95% Wilson CI
- Comparison coverage
- End-to-end accuracy
- Citation inclusion / exact-match
- Unsupported execution claims

조건부 Accuracy만 높고 coverage가 낮으면 좋은 시스템으로 해석하지 않습니다. 결과가 기대보다 낮아도 이번 평가 도중 v2를 소급 수정하지 않습니다.

## RQ3. 사용자 효과
취업·이직 준비자 최소 6명, 목표 10명 대상으로 within-subject counterbalanced comparison을 합니다.

조건:
- AI Promise
- 직접 검색

주 지표:
- 4분 안에 정답을 찾은 비율

보조 지표:
- 시간 내 완료자의 소요시간 중앙값
- 정답률
- 이해도 / 신뢰도 / 면접 활용 의향
- 개선 의견

R0와 비실시간 의견 참여는 시간·정답률에서 제외합니다.

## RQ4. 외부 타당성
Core 2가 끝난 뒤에만 시연용 기업을 실행합니다 (10/19 결과: 후보 11곳 중 기준을 넘은 카카오, 현대자동차, 신한지주. `docs/company-expansion-plan.md`).

GO:
- Core 2 results.json 완성
- 공개 URL 작동
- SK하이닉스 blind evaluation 완료
- 사용자 테스트 일정에 영향 없음

2024 사업보고서에서 specific AI 약속이 3개 이상일 때만 시연용으로 추가합니다. 추가 기업은 Human-AI 정확도 수치에 섞지 않습니다.

## 제출 이후
이번 제출의 기본 범위에는 ML 300문장 실험을 넣지 않습니다. 후속연구로 PROMISE / EVIDENCE / OTHER 분류, TF-IDF + Logistic Regression baseline, LLM zero/few-shot, cross-company validation을 진행할 수 있습니다.
