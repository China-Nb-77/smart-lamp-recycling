from __future__ import annotations

from typing import Any


class ApplicationError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class UnauthorizedError(ApplicationError):
    status_code = 401
    code = "unauthorized"


class NotFoundError(ApplicationError):
    status_code = 404
    code = "not_found"


class ConflictError(ApplicationError):
    status_code = 409
    code = "conflict"


class ServiceUnavailable(ApplicationError):
    status_code = 503
    code = "service_unavailable"


class LLMFormatError(ApplicationError):
    status_code = 502
    code = "llm_format_error"


class RequiresReviewError(ApplicationError):
    status_code = 412
    code = "requires_review"
