"""Typed exceptions for the Zinq Agent SDK.

All exceptions inherit from ZinqError so callers can catch broadly
or narrowly depending on their error-handling strategy.
"""

from __future__ import annotations


class ZinqError(Exception):
    """Base exception for all Zinq SDK errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(ZinqError):
    """Raised when the API key is invalid, revoked, or missing (HTTP 401)."""

    def __init__(self, message: str = "Invalid or revoked API key") -> None:
        super().__init__(message, status_code=401)


class RateLimitError(ZinqError):
    """Raised when the agent exceeds the rate limit (HTTP 429).

    Attributes:
        retry_after: Seconds until the next request is allowed.
    """

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float = 60.0) -> None:
        self.retry_after = retry_after
        super().__init__(message, status_code=429)


class InsufficientCreditsError(ZinqError):
    """Raised when the user has insufficient credits for a Gemini proxy call (HTTP 402).

    Attributes:
        credits_remaining: Credits the user currently has.
        credits_required: Credits needed for the requested operation.
    """

    def __init__(
        self,
        message: str = "Insufficient credits",
        credits_remaining: int = 0,
        credits_required: int = 0,
    ) -> None:
        self.credits_remaining = credits_remaining
        self.credits_required = credits_required
        super().__init__(message, status_code=402)


class NotFoundError(ZinqError):
    """Raised when a requested resource does not exist (HTTP 404)."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404)


class ValidationError(ZinqError):
    """Raised when the request parameters are invalid (HTTP 422)."""

    def __init__(self, message: str = "Invalid request parameters") -> None:
        super().__init__(message, status_code=422)


class ServerError(ZinqError):
    """Raised when the Zinq backend returns a 5xx error."""

    def __init__(self, message: str = "Zinq server error") -> None:
        super().__init__(message, status_code=500)
