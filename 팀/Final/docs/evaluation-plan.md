# 평가 계획

## 평가 설계
- **삼성전자**: calibration / development 기업
- **SK하이닉스**: blind evaluation 기업
- 추가 3개 기업: 제품 확장성과 외부 타당성 데모용. Human blind evaluation의 핵심 수치에는 섞지 않습니다.

## Human Ground Truth
두 사람이 AI 결과를 보기 전에 독립적으로 판정합니다.
1. 동일한 약속 목록을 각자 판정
2. 사람 간 일치율과 Cohen's kappa 계산
3. 불일치 항목은 원문을 다시 보고 합의
4. 합의본을 Gold Label로 고정
5. 그 뒤 AI 결과와 비교

## 핵심 지표
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
