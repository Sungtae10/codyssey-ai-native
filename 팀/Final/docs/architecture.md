# AI Promise 아키텍처

## 목표
기업이 정기공시에서 밝힌 AI 계획과 이후 정기공시의 실행 근거를 연결하고, 근거가 검증된 정보만 면접 준비에 사용합니다.

이 문서는 엔진 7단계를 다룹니다. 화면, 배포, 평가까지 포함한 시스템 전체 그림은 [기능 요구 명세서](requirements.md) 5장에 있습니다.

## 7단계
1. **Collect**: 2024 사업보고서와 후속 보고서에서 지정 섹션을 추출
2. **Promise Extraction**: AI 관련 미래 계획 문장을 원문 그대로 선택
3. **Specificity Classification**: 구체적 약속 / 방향성 약속 분리
4. **Evidence Retrieval**: 후속 공시를 hybrid retrieval로 검색
5. **LLM Judgment**: 4개 판정 중 하나 선택
6. **Citation Verification**: 선택한 근거 문장이 수집 원문에 실제 존재하는지 코드로 검사
7. **Interview Card**: 검증된 근거만 사용해 핵심 이슈·답변 소재·역질문 생성

## 핵심 안전장치
- 근거가 필요한 판정인데 인용 검사를 통과한 문장이 없으면 판정을 낮춥니다.
- 검색 실패 시 검색어를 바꾸되 최대 횟수를 제한합니다.
- `not_verifiable`은 미이행을 뜻하지 않습니다.
- 모든 실제 결과는 `engine/run.py check`를 통과한 뒤 화면으로 내보냅니다.

## 데이터 흐름
```text
DART PDF
  -> collected_*.json
  -> promises.json
  -> judged.json
  -> card.json
  -> ai_promise_data.json
  -> app/data/results.json
  -> Web UI
```

## 소스 오브 트루스
- 판정 방법론: `eval/판정기준_v2.md`
- 엔진 설정: `engine/config.yaml`
- 화면 데이터 계약: `tests/sample_data.json` + `engine/aipromise/checker.py`
- 실제 결과: `app/data/results.json` (생성 후)
