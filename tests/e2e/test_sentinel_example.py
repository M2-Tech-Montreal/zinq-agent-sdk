"""E2E tests for the Sentinel personal agent example.

Sentinel is a personal agent that monitors email/Slack and sends
digest vibes, saves alert memories, and uses Gemini for summarization.
These tests exercise the SDK methods that Sentinel would use.
"""

from __future__ import annotations

import uuid

import pytest

from zinq_agent import ZinqAgent
from zinq_agent.models import GeminiResponse, Memory, VibeSendResult


class TestSentinelDigest:
    """Tests covering Sentinel's email digest vibe flow."""

    def test_send_digest_vibe(self, agent: ZinqAgent) -> None:
        """Sentinel sends an email digest as a vibe to the user."""
        digest_text = (
            "3 new emails:\n"
            "  Glenn -- Dubai deal update\n"
            "  Shopify -- Order #4821 shipped\n"
            "  Calendar -- Team standup in 30 min"
        )
        result = agent.vibes.send(text=digest_text)
        assert isinstance(result, VibeSendResult)
        assert result.vibe_id > 0

    def test_send_slack_summary_vibe(self, agent: ZinqAgent) -> None:
        """Sentinel sends a Slack channel summary."""
        summary = (
            "Slack recap (last 2h):\n"
            "  #engineering -- 12 messages, deploy discussion\n"
            "  #random -- 3 messages, lunch plans\n"
            "  DM from Alex -- question about API keys"
        )
        result = agent.vibes.send(text=summary)
        assert isinstance(result, VibeSendResult)

    def test_send_priority_alert_vibe(self, agent: ZinqAgent) -> None:
        """Sentinel sends an urgent notification vibe."""
        result = agent.vibes.send(
            text="URGENT: Build failed on main branch. 3 tests failing.",
            vibe_type="NOTIFICATION",
        )
        assert isinstance(result, VibeSendResult)


class TestSentinelMemory:
    """Tests covering Sentinel's alert memory persistence."""

    def test_save_alert_memory(self, agent: ZinqAgent) -> None:
        """Sentinel saves the timestamp of the last email check."""
        key = f"sentinel_last_check_{uuid.uuid4().hex[:6]}"
        agent.memories.save(key, "2026-04-19T21:00:00Z", category="sentinel")

        mem = agent.memories.get(key)
        assert mem is not None
        assert isinstance(mem, Memory)
        assert "2026-04-19" in mem.value
        assert mem.category == "sentinel"

        # Cleanup
        agent.memories.delete(key)

    def test_save_email_summary_memory(self, agent: ZinqAgent) -> None:
        """Sentinel saves a per-sender email summary."""
        key = f"sentinel_sender_{uuid.uuid4().hex[:6]}"
        agent.memories.save(
            key,
            "Glenn: 3 emails about Dubai deal, latest needs approval by Friday",
            category="sentinel_senders",
        )

        mem = agent.memories.get(key)
        assert mem is not None
        assert "Glenn" in mem.value

        # Cleanup
        agent.memories.delete(key)

    def test_list_sentinel_memories(self, agent: ZinqAgent) -> None:
        """Sentinel lists all memories in its category."""
        key = f"sentinel_list_{uuid.uuid4().hex[:6]}"
        agent.memories.save(key, "test_sentinel_list", category="sentinel_e2e")

        memories = agent.memories.list(category="sentinel_e2e")
        assert isinstance(memories, list)
        assert any(m.key == key for m in memories)

        # Cleanup
        agent.memories.delete(key)

    def test_update_check_timestamp(self, agent: ZinqAgent) -> None:
        """Sentinel updates the last check timestamp (upsert)."""
        key = f"sentinel_ts_{uuid.uuid4().hex[:6]}"
        agent.memories.save(key, "2026-04-19T20:00:00Z", category="sentinel")
        agent.memories.save(key, "2026-04-19T21:00:00Z", category="sentinel")

        mem = agent.memories.get(key)
        assert mem is not None
        assert "21:00" in mem.value

        # Cleanup
        agent.memories.delete(key)


class TestSentinelGemini:
    """Tests covering Sentinel's use of Gemini for summarization."""

    def test_gemini_summarize_emails(self, agent: ZinqAgent) -> None:
        """Sentinel uses Gemini to summarize a batch of emails."""
        response = agent.gemini.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an email summarizer. Produce a 2-3 sentence "
                        "summary of the emails provided."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Email 1: From Glenn -- Dubai deal moving forward, "
                        "need sign-off by Friday.\n"
                        "Email 2: From Shopify -- Order #4821 shipped, arrives Tuesday.\n"
                        "Email 3: From HR -- Benefits enrollment deadline extended to May 1."
                    ),
                },
            ],
            model="flash",
            max_tokens=200,
        )
        assert isinstance(response, GeminiResponse)
        assert len(response.text) > 0

    def test_gemini_classify_urgency(self, agent: ZinqAgent) -> None:
        """Sentinel asks Gemini to classify email urgency."""
        response = agent.gemini.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify the urgency of this email as HIGH, MEDIUM, or LOW. "
                        "Reply with just the classification word."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Subject: URGENT - Server down in production\n"
                        "Body: The main API server is returning 503 errors. "
                        "All customer-facing services are affected."
                    ),
                },
            ],
            model="flash",
            max_tokens=10,
        )
        assert isinstance(response, GeminiResponse)
        assert len(response.text) > 0

    def test_gemini_generate_reply_draft(self, agent: ZinqAgent) -> None:
        """Sentinel uses Gemini to draft an email reply."""
        response = agent.gemini.chat(
            messages=[
                {
                    "role": "system",
                    "content": "Draft a brief, professional email reply.",
                },
                {
                    "role": "user",
                    "content": (
                        "Original email from Glenn: 'Can we move the Dubai meeting "
                        "to Thursday instead of Wednesday?'\n"
                        "Draft a reply confirming Thursday works."
                    ),
                },
            ],
            model="flash",
            max_tokens=150,
        )
        assert isinstance(response, GeminiResponse)
        assert len(response.text) > 20
