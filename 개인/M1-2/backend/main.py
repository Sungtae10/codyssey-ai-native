"""실행: uvicorn main:app --reload  (backend 폴더에서)

구조
  main.py              앱 시작점
  app/factory.py       FastAPI 앱 조립 (CORS, 예외 처리, 라우터 등록)
  app/routers/         HTTP 경로만 담당 (요청 받기 → 서비스 호출 → 응답)
  app/services/        실제 규칙과 계산 (CRUD 규칙, 요약 분석, 프롬프트, GPT 호출, 도구)
  app/schemas/         Pydantic 요청·응답 모델 (입력 검증)
  app/repositories/    저장소 (Firestore / 메모리)
"""
from app.factory import create_app

app = create_app()
