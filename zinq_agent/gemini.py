"""Gemini proxy client for the Zinq Agent SDK.

Provides access to Zinq's managed Gemini API.
Using this is optional -- developers can use any LLM they want.
When used, credits are deducted from the user's Zinq account.
"""

from __future__ import annotations

from typing import Any

import httpx

from .exceptions import InsufficientCreditsError
from .models import EmbeddingResponse, GeminiResponse
from .utils import raise_for_status


class GeminiClient:
    """Synchronous client for Zinq's Gemini LLM proxy.

    Usage::

        response = agent.gemini.chat(
            messages=[
                {"role": "system", "content": "You are a fitness coach."},
                {"role": "user", "content": "What should I eat after a run?"},
            ],
            model="flash",
        )
        print(response.text)
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "flash",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[dict[str, Any]] | None = None,
    ) -> GeminiResponse:
        """Send a conversation to Gemini and get a response.

        Args:
            messages: Conversation history with ``role`` and ``content`` keys.
                      Roles: ``system``, ``user``, ``assistant``.
            model: ``"flash"`` (default, cheapest) or ``"pro"`` (higher quality).
            temperature: Sampling temperature, 0.0-1.0 (default 0.7).
            max_tokens: Maximum response tokens (default 2048, max 8192).
            tools: Optional function-calling tool definitions in Gemini format.

        Returns:
            GeminiResponse.

        Raises:
            InsufficientCreditsError: If the user has no credits remaining.
            ZinqError: On other API errors.
        """
        body: dict[str, Any] = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "maxTokens": max_tokens,
        }
        if tools is not None:
            body["tools"] = tools

        response = self._client.post("/gemini/chat", json=body)
        _check_credits(response)
        if response.status_code != 200:
            raise_for_status(response)

        return GeminiResponse.model_validate(response.json())

    def embed(
        self,
        text: str,
        *,
        task_type: str = "RETRIEVAL_QUERY",
    ) -> EmbeddingResponse:
        """Generate an embedding vector for semantic search.

        Args:
            text: Text to embed (max 2048 chars).
            task_type: ``"RETRIEVAL_QUERY"`` (default) or ``"RETRIEVAL_DOCUMENT"``.

        Returns:
            EmbeddingResponse with the embedding vector, dimensions, and credit cost.

        Raises:
            InsufficientCreditsError: If the user has no credits remaining.
            ZinqError: On other API errors.
        """
        response = self._client.post("/gemini/embed", json={
            "text": text,
            "taskType": task_type,
        })
        _check_credits(response)
        if response.status_code != 200:
            raise_for_status(response)

        return EmbeddingResponse.model_validate(response.json())


class AsyncGeminiClient:
    """Async client for Zinq's Gemini LLM proxy.

    Usage::

        response = await agent.gemini.chat(
            messages=[{"role": "user", "content": "Hello!"}],
        )
        print(response.text)
    """

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "flash",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[dict[str, Any]] | None = None,
    ) -> GeminiResponse:
        """Send a conversation to Gemini and get a response.

        Args:
            messages: Conversation history with ``role`` and ``content`` keys.
            model: ``"flash"`` (default) or ``"pro"``.
            temperature: Sampling temperature (default 0.7).
            max_tokens: Maximum response tokens (default 2048).
            tools: Optional function-calling tool definitions.

        Returns:
            GeminiResponse with text, tool_calls, usage, and model info.
        """
        body: dict[str, Any] = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "maxTokens": max_tokens,
        }
        if tools is not None:
            body["tools"] = tools

        response = await self._client.post("/gemini/chat", json=body)
        _check_credits(response)
        if response.status_code != 200:
            raise_for_status(response)

        return GeminiResponse.model_validate(response.json())

    async def embed(
        self,
        text: str,
        *,
        task_type: str = "RETRIEVAL_QUERY",
    ) -> EmbeddingResponse:
        """Generate an embedding vector for semantic search."""
        response = await self._client.post("/gemini/embed", json={
            "text": text,
            "taskType": task_type,
        })
        _check_credits(response)
        if response.status_code != 200:
            raise_for_status(response)

        return EmbeddingResponse.model_validate(response.json())


def _check_credits(response: httpx.Response) -> None:
    """Raise InsufficientCreditsError on 402."""
    if response.status_code == 402:
        data = response.json()
        raise InsufficientCreditsError(
            message=data.get("error", "Insufficient credits"),
            credits_remaining=data.get("creditsRemaining", 0),
            credits_required=data.get("creditsRequired", 0),
        )
