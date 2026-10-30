# 문장 분류 ML Benchmark

**이번 제출에서는 하지 않습니다.** 기획 보고서 8.3에 따라 다음 단계로 두고, 코드와 데이터 형식만 남겨 둡니다.

제품 본체가 안정화된 뒤 수행하는 보조 실험입니다.

## 질문
기업 공시의 AI 관련 문장을 `PROMISE / EVIDENCE / OTHER`로 구분할 때 전통 ML baseline이 어느 정도 성능을 내는지 확인합니다.

## 데이터
다음 단계 목표(참고): 약 300문장. `template.csv` 형식으로 저장합니다.

- text: 원문 문장
- label: PROMISE / EVIDENCE / OTHER
- company: 기업 ID
- report: 보고서
- source: 위치

100문장 이상은 두 명이 겹쳐 라벨링해 일치도를 점검합니다.

## 실행
```bash
pip install -r eval/ml/requirements.txt
python eval/ml/benchmark.py eval/ml/sentences.csv
```

모델은 TF-IDF + Logistic Regression이며 Stratified 5-fold CV의 accuracy와 macro-F1을 출력합니다. 이후 동일한 holdout/fold 정의를 LLM zero-shot/few-shot 비교에도 사용합니다.
