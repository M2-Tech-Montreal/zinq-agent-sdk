"""Shared utilities for the Zinq Agent SDK."""

from __future__ import annotations

import httpx

from .exceptions import (
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
    ZinqError,
)


def raise_for_status(response: httpx.Response) -> None:
    """Raise a typed ZinqError based on the HTTP status code."""
    if response.is_success:
        return

    status = response.status_code

    try:
        detail = response.json()
        message = detail.get("error") or detail.get("message") or response.text
    except (ValueError, KeyError):
        detail = {}
        message = response.text or f"HTTP {status}"

    if status == 401:
        raise AuthenticationError(str(message))
    if status == 402:
        raise InsufficientCreditsError(
            str(message),
            credits_remaining=detail.get("creditsRemaining", 0),
            credits_required=detail.get("creditsRequired", 0),
        )
    if status == 404:
        raise NotFoundError(str(message))
    if status == 422:
        raise ValidationError(str(message))
    if status == 429:
        retry_after = float(response.headers.get("Retry-After", "60"))
        raise RateLimitError(str(message), retry_after=retry_after)
    if 500 <= status < 600:
        raise ServerError(str(message))

    raise ZinqError(str(message), status_code=status)
