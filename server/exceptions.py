"""
FormNest — Custom Exception Hierarchy

Pattern mirrors TREEEX-WBSP's TreexBaseException system.
"""

from __future__ import annotations

from typing import Any


class FormNestBaseError(Exception):
    """Base exception for all FormNest errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    detail: str = "An internal error occurred"

    def __init__(
        self,
        detail: str | None = None,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        self.detail = detail or self.__class__.detail
        if status_code:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code
        self.extra = extra or {}
        super().__init__(self.detail)

    def to_response(self) -> dict[str, Any]:
        response: dict[str, Any] = {
            "error": self.error_code,
            "detail": self.detail,
        }
        if self.extra:
            response["extra"] = self.extra
        return response


# --- 400 Errors ---

class BadRequestError(FormNestBaseError):
    status_code = 400
    error_code = "BAD_REQUEST"
    detail = "Bad request"


class ValidationError(FormNestBaseError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    detail = "Validation error"


# --- 401/403 Errors ---

class UnauthorizedError(FormNestBaseError):
    status_code = 401
    error_code = "UNAUTHORIZED"
    detail = "Authentication required"


class ForbiddenError(FormNestBaseError):
    status_code = 403
    error_code = "FORBIDDEN"
    detail = "You do not have permission to perform this action"


# --- 404 Errors ---

class NotFoundError(FormNestBaseError):
    status_code = 404
    error_code = "NOT_FOUND"
    detail = "Resource not found"


# --- 409 Errors ---

class ConflictError(FormNestBaseError):
    status_code = 409
    error_code = "CONFLICT"
    detail = "Resource already exists"


# --- 429 Errors ---

class RateLimitError(FormNestBaseError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    detail = "Too many requests. Please try again later."


# --- Business Logic Errors ---

class PlanLimitError(FormNestBaseError):
    status_code = 403
    error_code = "PLAN_LIMIT_EXCEEDED"
    detail = "You have reached your plan limit"


class FormNotActiveError(FormNestBaseError):
    status_code = 410
    error_code = "FORM_NOT_ACTIVE"
    detail = "This form is no longer accepting submissions"


class SpamDetectedError(FormNestBaseError):
    status_code = 422
    error_code = "SPAM_DETECTED"
    detail = "Submission flagged as spam"
