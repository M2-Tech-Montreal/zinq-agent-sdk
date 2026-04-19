"""Gemini proxy client for the Zinq Agent SDK.

Provides access to Zinq's managed Gemini API with optional streaming.
Using this is optional -- developers can use any LLM they want.
When used, credits are deducted from the user's Zinq account.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Iterator

import httpx

from .exceptions import InsufficientCreditsError
from .models import EmbeddingResponse, GeminiResponse


def _raise_for_status(response: httpx.Response) -> None:
    """Raise an appropriate ZinqError for a non-200 response."""
    from .client import _raise_for_status as raise_helper

    raise_helper(response)


class GeminiClient:
    """Synchronous client for Zinq's Gemini LLM proxy.

    Usage::

        # Non-streaming
        response = agent.gemini.chat(
            messages=[
                {"role": "system", "content": "You are a fitness coach."},
                {"role": "user", "content": "What should I eat after a run?"},
            ],
            model="flash",
        )
        print(response.text)

        # Streaming
        for chunk in agent.gemini.chat(
            messages=[{"role": "user", "content": "Tell me a story"}],
            stream=True,
        ):
            print(chunk, end="", flush=True)
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = False,
        model: str = "flash",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[dict[str, Any]] | None = None,
    ) -> GeminiResponse | Iterator[str]:
        """Send a conversation to Gemini and get a response.

        Args:
            messages: Conversation history with ``role`` and ``content`` keys.
                      Roles: ``system``, ``user``, ``assistant``.
            stream: If True, return a streaming iterator of text chunks.
            model: ``"flash"`` (default, cheapest) or ``"pro"`` (higher quality).
            temperature: Sampling temperature, 0.0-1.0 (default 0.7).
            max_tokens: Maximum response tokens (default 2048, max 8192).
            tools: Optional function-calling tool definitions in Gemini format.

        Returns:
            GeminiResponse if stream=False, or Iterator[str] if stream=True.

        Raises:
            InsufficientCreditsError: If the user has no credits remaining.
            ZinqError: On other API errors.
        """
        if stream:
            return self._stream_chat(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
            )
        return self._chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        )

    def _chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
    ) -> GeminiResponse:
        body: dict[str, Any] = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "maxTokens": max_tokens,
        }
        if tools is not None:
            body["tools"] = tools

        response = self._client.post("/gemini/chat", json=body)

        if response.status_code == 402:
            data = response.json()
            raise InsufficientCreditsError(
                message=data.get("error", "Insufficient credits"),
                credits_remaining=data.get("creditsRemaining", 0),
                credits_required=data.get("creditsRequired", 0),
            )

        if response.status_code != 200:
            _raise_for_status(response)

        return GeminiResponse.model_validate(response.json())

    def _stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        """Streaming variant -- yields text chunks via SSE.

        Usage::

            for chunk in agent.gemini.chat(messages, stream=True):
                print(chunk, end="", flush=True)
        """
        body: dict[str, Any] = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "maxTokens": max_tokens,
            "stream": True,
        }
        if tools is not None:
            body["tools"] = tools

        with self._client.stream("POST", "/gemini/chat", json=body) as response:
            if response.status_code == 402:
                response.read()
                data = response.json()
                raise InsufficientCreditsError(
                    message=data.get("error", "Insufficient credits"),
                    credits_remaining=data.get("creditsRemaining", 0),
                    credits_required=data.get("creditsRequired", 0),
                )

            if response.status_code != 200:
                response.read()
                _raise_for_status(response)

            for line in response.iter_lines():
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        text = chunk.get("text") or chunk.get("content", "")
                        if text:
                            yield text
                    except json.JSONDecodeError:
                        continue

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
        body = {
            "text": text,
            "taskType": task_type,
        }

        response = self._client.post("/gemini/embed", json=body)

        if response.status_code == 402:
            data = response.json()
            raise InsufficientCreditsError(
                message=data.get("error", "Insufficient credits"),
                credits_remaining=data.get("creditsRemaining", 0),
                credits_required=data.get("creditsRequired", 0),
            )

        if response.status_code != 200:
            _raise_for_status(response)

        return EmbeddingResponse.model_validate(response.json())


class AsyncGeminiClient:
    """Async client for Zinq's Gemini LLM proxy.

    Usage::

        # Non-streaming
        response = await agent.gemini.chat(
            messages=[{"role": "user", "content": "Hello!"}],
        )
        print(response.text)

        # Streaming
        async for chunk in agent.gemini.stream_chat(
            messages=[{"role": "user", "content": "Tell me a story"}],
        ):
            print(chunk, end="", flush=True)
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

        For streaming, use ``stream_chat()`` instead.

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

        if response.status_code == 402:
            data = response.json()
            raise InsufficientCreditsError(
                message=data.get("error", "Insufficient credits"),
                credits_remaining=data.get("creditsRemaining", 0),
                credits_required=data.get("creditsRequired", 0),
            )

        if response.status_code != 200:
            _raise_for_status(response)

        return GeminiResponse.model_validate(response.json())

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "flash",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Streaming chat -- yields text chunks via SSE.

        Usage::

            async for chunk in agent.gemini.stream_chat(messages):
                print(chunk, end="", flush=True)
        """
        body: dict[str, Any] = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "maxTokens": max_tokens,
            "stream": True,
        }

        async with self._client.stream("POST", "/gemini/chat", json=body) as response:
            if response.status_code == 402:
                await response.aread()
                data = response.json()
                raise InsufficientCreditsError(
                    message=data.get("error", "Insufficient credits"),
                    credits_remaining=data.get("creditsRemaining", 0),
                    credits_required=data.get("creditsRequired", 0),
                )

            if response.status_code != 200:
                await response.aread()
                _raise_for_status(response)

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        text = chunk.get("text") or chunk.get("content", "")
                        if text:
                            yield text
                    except json.JSONDecodeError:
                        continue

    async def embed(
        self,
        text: str,
        *,
        task_type: str = "RETRIEVAL_QUERY",
    ) -> EmbeddingResponse:
        """Generate an embedding vector for semantic search."""
        body = {"text": text, "taskType": task_type}

        response = await self._client.post("/gemini/embed", json=body)

        if response.status_code == 402:
            data = response.json()
            raise InsufficientCreditsError(
                message=data.get("error", "Insufficient credits"),
                credits_remaining=data.get("creditsRemaining", 0),
                credits_required=data.get("creditsRequired", 0),
            )

        if response.status_code != 200:
            _raise_for_status(response)

        return EmbeddingResponse.model_validate(response.json())
