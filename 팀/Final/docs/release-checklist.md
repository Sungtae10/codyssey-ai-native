# 최종 제출 Release Checklist

## P0: 제출 불가를 막는 항목
- [ ] 공개 URL이 외부 브라우저에서 열린다
- [ ] 실제 사용자 5명 이상 설문 응답이 있다
- [ ] 실제 피드백 1건 이상 제품에 반영했다
- [ ] README에 공개 URL·사용자 수·반영 내용을 적었다
- [ ] AI 생성 분석 고지가 화면에 보인다

## P1: 서비스 품질
- [ ] Core 2 실제 데이터가 화면에 나온다
- [ ] 약속 상세에서 DART 원문 링크가 열린다
- [ ] citation_verified 표시가 실제 데이터와 일치한다
- [ ] 면접 카드가 비어 있거나 깨지지 않는다
- [ ] 모바일 390px에서 가로 스크롤이 없다
- [ ] 다크/라이트 모드 주요 텍스트 대비 이상 없음

## P1: 코드·문서
- [ ] python tests/test_config.py
- [ ] python tests/test_mock.py
- [ ] python tests/test_ui_static.py
- [ ] python tests/ui_check.py
- [ ] docs/requirements.md 존재
- [ ] docs/official-requirements-matrix.md 최신화
- [ ] docs/feedback-log.md 실제 값 기입
- [x] 발표자료/영상 링크 또는 파일 경로 README에 추가 (드라이브 폴더 `1020_발표자료_영상`, 10/19)

## P2: 시간이 남으면
- [x] 카카오 시연 데이터 (AI 엔진 결과, PR #39)
- [x] 현대자동차 시연 데이터 (NAVER 대신, AI 엔진 결과, PR #39)
- [x] 신한지주 시연 데이터 (신한은행 대신, AI 엔진 결과, PR #39)
- [ ] Human evaluation 보강
- [ ] 추가 사용자 테스트

## 제출 전 금지
- 실제로 하지 않은 테스트를 했다고 쓰기
- Demo 3를 Human blind evaluation 대상으로 표현하기
- '공시에서 확인 불가'를 '미이행'으로 표현하기
- 샘플 데이터를 실제 기업 데이터처럼 보여주기
