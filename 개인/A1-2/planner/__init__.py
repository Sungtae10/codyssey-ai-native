"""국내 여행 추천 프로그램(코디세이 A1-2)의 기능 모듈 모음.

모듈 역할(한 줄씩)
- config.py   : .env / 환경변수에서 키와 제공자 선택을 읽는다. 키가 없으면 안내문과 함께 멈춘다.
- errors.py   : 오류 타입 이름, 오류 목록(errors) 관리, HTTP 상태 코드 분류, 조치 안내 문구
- http_client.py : 외부 API 공통 호출(GET / POST), 일시적 오류 1회 재시도, 키 가리기(***)
- schema.py   : LLM 출력에서 JSON 꺼내기, 1차 추천 필수 키/타입 검사
- llm.py      : OpenAI / Gemini 호출, 1차 추천 프롬프트, 재요청 프롬프트, 리포트 프롬프트
- places.py   : Kakao / Naver 장소 검색, 지명 보정, 응답 필드 통일, 지역 검증
- report.py   : 리포트 조립(맛집 표 채우기, 오류 요약 붙이기), 실패 시 기본 템플릿
- storage.py  : results/ 저장, 캐시 읽기
- pipeline.py : [1/3] -> [2/3] -> [3/3] 실행 순서와 저장
"""

__version__ = "2.0.0"
