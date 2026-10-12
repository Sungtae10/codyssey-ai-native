# 5개 기업 확장 계획

## 최종 제품 목표
**실제 서비스 5개 기업 / 엄격한 Human-AI 검증 2개 기업 / ML benchmark 5개 기업**을 목표로 합니다.

### Core 2
- 삼성전자: calibration / development
- SK하이닉스: blind evaluation

### Expansion 3 후보
- 현대자동차
- LG전자
- NAVER

후보는 브랜드 인지도만으로 확정하지 않습니다. 실제 공시 feasibility를 먼저 확인합니다.

## 추가 기업 GO 조건
2024 사업보고서의 지정 섹션에서 판정기준 v2에 맞는 **구체적 AI 약속이 최소 3개** 있어야 합니다. 후속 2025 사업보고서 또는 2026 반기보고서에서 최소 일부 약속에 Evidence 후보가 연결되어야 합니다.

## 확장 기업의 검증 수준
추가 3개 기업은 다음을 반드시 통과합니다.
- 실제 DART 정기공시만 사용
- Promise 원문 보존
- Evidence 원문 보존
- Citation Verification 통과
- `engine/run.py check` 통과
- 최소 표본 수동 점검

다만 삼성전자·SK하이닉스처럼 두 사람이 모든 약속을 독립 판정할 필요는 없습니다.

## 중단 조건
아래가 끝나지 않았다면 기업 수를 늘리지 않습니다.
- 삼성전자 실제 results.json 생성
- SK하이닉스 blind Gold Label 확보
- 공개 배포 URL에서 4개 화면 end-to-end 작동
- 핵심 평가 스크립트 정상 실행

5개 완성 이후의 추가 기업은 Stretch Goal입니다.
