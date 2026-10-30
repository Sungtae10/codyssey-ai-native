"""서비스 계층에서 쓰는 예외. main.py의 예외 처리기가 HTTP 응답({"detail": ...})으로 바꾼다."""
from __future__ import annotations


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class RateLimitedError(AppError):
    status_code = 429


class AIServiceError(AppError):
    status_code = 502


class StorageUnavailableError(AppError):
    status_code = 503
