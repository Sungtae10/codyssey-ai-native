# 협업 규칙

AI Promise는 코드와 평가 증빙을 함께 남기는 팀 프로젝트입니다.

## 역할
- 김성태: Product / AI Engine / Evaluation / Integration
- 김서원: Research / Human Validation / User Test
- 박수민: Frontend / App Implementation / QA
- 서준용: UX / Visual / Demo / Presentation

## 브랜치
`main`에 큰 변경을 바로 올리지 않고 아래처럼 작업합니다.
- `feature/<내용>`
- `fix/<내용>`
- `docs/<내용>`
- `eval/<내용>`

작업 후 PR을 열고 최소 한 명이 확인한 뒤 합칩니다.

## 데이터와 보안
- OpenAI API 키와 `.env`는 절대 커밋하지 않습니다.
- 사용자 테스트는 이름·연락처 대신 `P01`, `P02`처럼 번호만 저장합니다.
- DART PDF 원본은 저장소에 올리지 않습니다.
- SK하이닉스 blind evaluation이 끝나기 전에는 AI 판정 결과를 Human Validator에게 공유하지 않습니다.

## 판정 기준
판정 기준은 `eval/판정기준_v2.md`를 사용합니다. v2가 팀 합의로 확정된 뒤에는 blind evaluation이 끝날 때까지 규칙을 바꾸지 않습니다.

## 완료 기준
코드 변경은 최소한 아래를 통과해야 합니다.

```bash
python tests/test_config.py
python tests/test_mock.py
node --check app/js/app.js
```

실제 결과 파일은 추가로 다음을 확인합니다.

```bash
cd engine
python run.py check --file ../app/data/results.json
```
