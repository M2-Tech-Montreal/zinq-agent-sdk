"""Tests for the ZinqAgent client and sub-clients."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from zinq_agent import (
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ZinqAgent,
)

BASE_URL = "https://zinq-app.com/api/agent-api"


@pytest.fixture
def agent():
    """Create a ZinqAgent instance for testing."""
    a = ZinqAgent(api_key="zak_" + "a" * 64)
    yield a
    a.close()


# ---------------------------------------------------------------------------
# ZinqAgent initialization
# ---------------------------------------------------------------------------


class TestZinqAgentInit:
    def test_valid_api_key(self):
        agent = ZinqAgent(api_key="zak_" + "x" * 64)
        assert agent.api_key == "zak_" + "x" * 64
        agent.close()

    def test_invalid_api_key_prefix(self):
        with pytest.raises(ValueError, match="Expected 'zak_' prefix"):
            ZinqAgent(api_key="bad_key_here")

    def test_repr_masks_key(self):
        agent = ZinqAgent(api_key="zak_abcdefgh12345678")
        r = repr(agent)
        assert "zak_abcd" in r
        assert "5678" in r
        assert "abcdefgh12345678" not in r
        agent.close()

    def test_context_manager(self):
        with ZinqAgent(api_key="zak_" + "x" * 64) as agent:
            assert agent.api_key.startswith("zak_")


# ---------------------------------------------------------------------------
# DiaryClient
# ---------------------------------------------------------------------------


class TestDiaryClient:
    @respx.mock
    def test_list_diary_entries(self, agent):
        respx.get(f"{BASE_URL}/diary").mock(
            return_value=httpx.Response(
                200,
                json={
                    "entries": [
                        {
                            "id": 1,
                            "text": "Morning run",
                            "transcript": None,
                            "mediaType": None,
                            "mediaUrl": None,
                            "aiTags": ["fitness"],
                            "createdAt": "2026-04-19T08:00:00Z",
                        }
                    ],
                    "page": 0,
                    "totalPages": 1,
                    "totalEntries": 1,
                },
            )
        )

        page = agent.diary.list(start="2026-04-01", tags=["fitness"])
        assert len(page.entries) == 1
        assert page.entries[0].text == "Morning run"
        assert page.entries[0].ai_tags == ["fitness"]
        assert page.total_entries == 1

    @respx.mock
    def test_search_diary(self, agent):
        respx.get(f"{BASE_URL}/diary/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": 1,
                            "text": "5K run in the park",
                            "aiTags": ["fitness"],
                            "similarity": 0.92,
                            "createdAt": "2026-04-19T08:00:00Z",
                        }
                    ],
                    "query": "running",
                    "embeddingCreditsUsed": 1,
                },
            )
        )

        results = agent.diary.search("running", limit=5)
        assert len(results.results) == 1
        assert results.results[0].similarity == 0.92
        assert results.embedding_credits_used == 1


# ---------------------------------------------------------------------------
# VibeClient
# ---------------------------------------------------------------------------


class TestVibeClient:
    @respx.mock
    def test_send_text_vibe(self, agent):
        respx.post(f"{BASE_URL}/vibes/send").mock(
            return_value=httpx.Response(
                200,
                json={
                    "vibeId": 99001,
                    "deliveredAt": "2026-04-19T19:01:00Z",
                    "pushSent": True,
                },
            )
        )

        result = agent.vibes.send(text="Time for your walk!")
        assert result.vibe_id == 99001
        assert result.push_sent is True

    @respx.mock
    def test_send_interactive_vibe(self, agent):
        respx.post(f"{BASE_URL}/vibes/send").mock(
            return_value=httpx.Response(
                200,
                json={
                    "vibeId": 99002,
                    "deliveredAt": "2026-04-19T19:02:00Z",
                    "pushSent": True,
                },
            )
        )

        result = agent.vibes.send(
            text="Which workout?",
            input_type="choice",
            options=["Upper body", "Lower body"],
        )
        assert result.vibe_id == 99002

        # Verify the request body included interactive fields
        request = respx.calls.last.request
        body = json.loads(request.content)
        assert body["interactive"]["inputType"] == "choice"
        assert body["interactive"]["options"] == ["Upper body", "Lower body"]

    @respx.mock
    def test_received_vibes(self, agent):
        respx.get(f"{BASE_URL}/vibes/received").mock(
            return_value=httpx.Response(
                200,
                json={
                    "vibes": [
                        {
                            "id": 67890,
                            "type": "TEXT",
                            "text": "What should I eat?",
                            "transcript": None,
                            "mediaUrl": None,
                            "charmEmoji": None,
                            "replyToVibeId": None,
                            "createdAt": "2026-04-19T19:00:00Z",
                        }
                    ]
                },
            )
        )

        vibes = agent.vibes.received(unread=True)
        assert len(vibes) == 1
        assert vibes[0].text == "What should I eat?"


# ---------------------------------------------------------------------------
# MemoryClient
# ---------------------------------------------------------------------------


class TestMemoryClient:
    @respx.mock
    def test_list_memories(self, agent):
        respx.get(f"{BASE_URL}/memories").mock(
            return_value=httpx.Response(
                200,
                json={
                    "memories": [
                        {
                            "key": "diet",
                            "value": "vegetarian",
                            "category": "health",
                            "updatedAt": "2026-04-18T14:00:00Z",
                        }
                    ]
                },
            )
        )

        memories = agent.memories.list(category="health")
        assert len(memories) == 1
        assert memories[0].key == "diet"
        assert memories[0].value == "vegetarian"

    @respx.mock
    def test_get_memory(self, agent):
        respx.get(f"{BASE_URL}/memories").mock(
            return_value=httpx.Response(
                200,
                json={
                    "memories": [
                        {
                            "key": "workout_pref",
                            "value": "morning yoga",
                            "category": None,
                            "updatedAt": "2026-04-15T09:00:00Z",
                        }
                    ]
                },
            )
        )

        mem = agent.memories.get("workout_pref")
        assert mem is not None
        assert mem.value == "morning yoga"

    @respx.mock
    def test_get_memory_not_found(self, agent):
        respx.get(f"{BASE_URL}/memories").mock(
            return_value=httpx.Response(200, json={"memories": []})
        )

        mem = agent.memories.get("nonexistent")
        assert mem is None

    @respx.mock
    def test_save_memory(self, agent):
        respx.post(f"{BASE_URL}/memories").mock(
            return_value=httpx.Response(
                200,
                json={
                    "key": "diet",
                    "created": True,
                    "updatedAt": "2026-04-19T19:02:00Z",
                },
            )
        )

        result = agent.memories.save("diet", "vegetarian", category="health")
        assert result.created is True

    @respx.mock
    def test_delete_memory(self, agent):
        respx.delete(f"{BASE_URL}/memories/old_key").mock(
            return_value=httpx.Response(204)
        )

        agent.memories.delete("old_key")  # Should not raise


# ---------------------------------------------------------------------------
# UserClient
# ---------------------------------------------------------------------------


class TestUserClient:
    @respx.mock
    def test_get_context(self, agent):
        respx.get(f"{BASE_URL}/user/context").mock(
            return_value=httpx.Response(
                200,
                json={
                    "userId": 42,
                    "name": "Alex",
                    "nickname": "Alex",
                    "timezone": "America/New_York",
                    "locale": "en-US",
                    "countryCode": "US",
                    "agentPreferences": {
                        "notificationHours": {"start": 8, "end": 21},
                        "preferredResponseLength": "concise",
                    },
                    "creditStatus": {
                        "creditsRemaining": 85,
                        "monthlyLimit": 100,
                        "tier": "free",
                        "resetDate": "2026-05-01T00:00:00Z",
                    },
                },
            )
        )

        ctx = agent.user.context()
        assert ctx.name == "Alex"
        assert ctx.timezone == "America/New_York"
        assert ctx.credit_status.credits_remaining == 85
        assert ctx.credit_status.tier == "free"
        assert ctx.agent_preferences is not None
        assert ctx.agent_preferences.notification_hours is not None
        assert ctx.agent_preferences.notification_hours.start == 8


# ---------------------------------------------------------------------------
# GeminiClient
# ---------------------------------------------------------------------------


class TestGeminiClient:
    @respx.mock
    def test_chat(self, agent):
        respx.post(f"{BASE_URL}/gemini/chat").mock(
            return_value=httpx.Response(
                200,
                json={
                    "content": "Eat a banana and some protein!",
                    "toolCalls": [],
                    "usage": {
                        "promptTokens": 100,
                        "completionTokens": 50,
                        "totalTokens": 150,
                        "creditsUsed": 2,
                    },
                    "model": "gemini-2.0-flash",
                },
            )
        )

        response = agent.gemini.chat(
            messages=[{"role": "user", "content": "What to eat?"}],
        )
        assert response.text == "Eat a banana and some protein!"
        assert response.usage.credits_used == 2

    @respx.mock
    def test_chat_insufficient_credits(self, agent):
        respx.post(f"{BASE_URL}/gemini/chat").mock(
            return_value=httpx.Response(
                402,
                json={
                    "error": "insufficient_credits",
                    "creditsRemaining": 2,
                    "creditsRequired": 5,
                },
            )
        )

        with pytest.raises(InsufficientCreditsError) as exc_info:
            agent.gemini.chat(
                messages=[{"role": "user", "content": "Hello"}],
            )

        assert exc_info.value.credits_remaining == 2
        assert exc_info.value.credits_required == 5

    @respx.mock
    def test_embed(self, agent):
        respx.post(f"{BASE_URL}/gemini/embed").mock(
            return_value=httpx.Response(
                200,
                json={
                    "embedding": [0.01, -0.02, 0.03],
                    "dimensions": 768,
                    "creditsUsed": 1,
                },
            )
        )

        result = agent.gemini.embed("morning run")
        assert len(result.embedding) == 3
        assert result.dimensions == 768
        assert result.credits_used == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @respx.mock
    def test_authentication_error(self, agent):
        respx.get(f"{BASE_URL}/diary").mock(
            return_value=httpx.Response(
                401,
                json={"error": "Invalid API key"},
            )
        )

        with pytest.raises(AuthenticationError):
            agent.diary.list()

    @respx.mock
    def test_rate_limit_error(self, agent):
        respx.post(f"{BASE_URL}/vibes/send").mock(
            return_value=httpx.Response(
                429,
                json={"error": "Rate limit exceeded"},
                headers={"Retry-After": "30"},
            )
        )

        with pytest.raises(RateLimitError) as exc_info:
            agent.vibes.send(text="test")

        assert exc_info.value.retry_after == 30.0

    @respx.mock
    def test_not_found_error(self, agent):
        respx.delete(f"{BASE_URL}/memories/nonexistent").mock(
            return_value=httpx.Response(
                404,
                json={"error": "Memory not found"},
            )
        )

        with pytest.raises(NotFoundError):
            agent.memories.delete("nonexistent")

    @respx.mock
    def test_server_error(self, agent):
        respx.get(f"{BASE_URL}/user/context").mock(
            return_value=httpx.Response(
                500,
                json={"error": "Internal server error"},
            )
        )

        with pytest.raises(ServerError):
            agent.user.context()
