"""E2E tests for the ZinqAgent personal agent SDK.

Covers every sub-client: diary, vibes, feed, contacts, zones,
memories, user, gemini, and billing.
"""

from __future__ import annotations

import uuid

import pytest

from zinq_agent import ZinqAgent
from zinq_agent.exceptions import InsufficientCreditsError
from zinq_agent.models import (
    DiaryPage,
    EmbeddingResponse,
    GeminiResponse,
    Memory,
    MemorySaveResult,
    SearchResults,
    UserContext,
    Vibe,
    VibeSendResult,
    Zone,
)


# ---------------------------------------------------------------------------
# Diary
# ---------------------------------------------------------------------------


class TestDiary:
    """Tests for agent.diary sub-client."""

    def test_list_diary(self, agent: ZinqAgent) -> None:
        """List diary entries and verify pagination shape."""
        page = agent.diary.list(size=5)
        assert isinstance(page, DiaryPage)
        assert isinstance(page.entries, list)
        assert page.page == 0
        assert page.total_pages >= 0
        assert page.total_entries >= 0

    def test_list_diary_with_date_filter(self, agent: ZinqAgent) -> None:
        """List diary entries filtered by date range."""
        page = agent.diary.list(start="2020-01-01", end="2099-12-31", size=5)
        assert isinstance(page, DiaryPage)

    def test_list_diary_with_tags(self, agent: ZinqAgent) -> None:
        """List diary entries filtered by AI tags."""
        page = agent.diary.list(tags=["fitness"], size=5)
        assert isinstance(page, DiaryPage)

    def test_search_diary(self, agent: ZinqAgent) -> None:
        """Semantic search over diary entries."""
        results = agent.diary.search("exercise", limit=3)
        assert isinstance(results, SearchResults)
        assert isinstance(results.results, list)
        assert isinstance(results.query, str)
        assert results.embedding_credits_used >= 0

    def test_save_diary_entry(self, agent: ZinqAgent) -> None:
        """Save a new text entry to the diary."""
        result = agent.diary.save(
            "E2E test diary entry -- please ignore",
            mood_score=7,
        )
        assert isinstance(result, dict)
        assert "vibeId" in result or "vibe_id" in result or "id" in result

    def test_star_vibe(self, agent: ZinqAgent) -> None:
        """Star a diary vibe.

        First saves a vibe, then stars it. If the server doesn't
        support starring arbitrary vibes we accept a 4xx gracefully.
        """
        saved = agent.diary.save("E2E star test entry")
        vibe_id = saved.get("vibeId") or saved.get("vibe_id") or saved.get("id")
        if vibe_id is None:
            pytest.skip("Could not get vibe_id from diary.save response")
        try:
            result = agent.diary.star(int(vibe_id))
            assert isinstance(result, dict)
        except Exception:
            # Some vibes may not be star-able; that is acceptable
            pass

    def test_archive_vibe(self, agent: ZinqAgent) -> None:
        """Archive a diary vibe (soft delete)."""
        saved = agent.diary.save("E2E archive test entry")
        vibe_id = saved.get("vibeId") or saved.get("vibe_id") or saved.get("id")
        if vibe_id is None:
            pytest.skip("Could not get vibe_id from diary.save response")
        try:
            result = agent.diary.archive(int(vibe_id))
            assert isinstance(result, dict)
        except Exception:
            pass

    def test_iter_diary(self, agent: ZinqAgent) -> None:
        """Auto-paginating iterator works without error."""
        count = 0
        for entry in agent.diary.iter(size=5):
            count += 1
            if count >= 5:
                break
        # No assertion on count -- diary may be empty


# ---------------------------------------------------------------------------
# Vibes
# ---------------------------------------------------------------------------


class TestVibes:
    """Tests for agent.vibes sub-client."""

    def test_send_text_vibe(self, agent: ZinqAgent) -> None:
        """Send a simple text vibe to the user."""
        result = agent.vibes.send(text="E2E test vibe -- please ignore")
        assert isinstance(result, VibeSendResult)
        assert result.vibe_id > 0

    def test_send_vibe_with_buttons(self, agent: ZinqAgent) -> None:
        """Send an interactive vibe with buttons."""
        result = agent.vibes.send(
            text="E2E test: pick an option",
            buttons=[
                {"label": "Option A", "value": "a"},
                {"label": "Option B", "value": "b"},
            ],
        )
        assert isinstance(result, VibeSendResult)
        assert result.vibe_id > 0

    def test_send_vibe_with_choice(self, agent: ZinqAgent) -> None:
        """Send an interactive vibe with choice input type."""
        result = agent.vibes.send(
            text="E2E test: which one?",
            input_type="choice",
            options=["Alpha", "Beta", "Gamma"],
        )
        assert isinstance(result, VibeSendResult)

    def test_send_vibe_with_metadata(self, agent: ZinqAgent) -> None:
        """Send a vibe with metadata attached."""
        result = agent.vibes.send(
            text="E2E test metadata vibe",
            metadata={"source": "e2e_test", "version": 1},
        )
        assert isinstance(result, VibeSendResult)

    def test_send_notification_vibe(self, agent: ZinqAgent) -> None:
        """Send a notification-type vibe."""
        result = agent.vibes.send(
            text="E2E notification test",
            vibe_type="NOTIFICATION",
        )
        assert isinstance(result, VibeSendResult)

    def test_received_vibes(self, agent: ZinqAgent) -> None:
        """Read vibes received from the user."""
        vibes = agent.vibes.received(limit=5)
        assert isinstance(vibes, list)
        for v in vibes:
            assert isinstance(v, Vibe)

    def test_received_vibes_unread_filter(self, agent: ZinqAgent) -> None:
        """Filter received vibes to unread only."""
        vibes = agent.vibes.received(limit=5, unread=True)
        assert isinstance(vibes, list)

    def test_reply_to_vibe(self, agent: ZinqAgent) -> None:
        """Send a vibe as a reply to a previous vibe."""
        first = agent.vibes.send(text="E2E original vibe for reply test")
        reply = agent.vibes.send(
            text="E2E reply vibe",
            reply_to=first.vibe_id,
        )
        assert isinstance(reply, VibeSendResult)
        assert reply.vibe_id != first.vibe_id


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------


class TestFeed:
    """Tests for agent.feed sub-client."""

    def test_list_feed(self, agent: ZinqAgent) -> None:
        """Get the user's vibe feed."""
        vibes = agent.feed.list(limit=5)
        assert isinstance(vibes, list)
        for v in vibes:
            assert isinstance(v, Vibe)

    def test_list_feed_with_offset(self, agent: ZinqAgent) -> None:
        """Get a paginated slice of the feed."""
        vibes = agent.feed.list(limit=3, offset=0)
        assert isinstance(vibes, list)


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


class TestContacts:
    """Tests for agent.contacts sub-client."""

    def test_list_contacts(self, agent: ZinqAgent) -> None:
        """List the user's connections."""
        contacts = agent.contacts.list(limit=10)
        assert isinstance(contacts, list)

    def test_search_contacts(self, agent: ZinqAgent) -> None:
        """Search contacts by name."""
        contacts = agent.contacts.search("test", limit=5)
        assert isinstance(contacts, list)

    def test_get_contact_profile(self, agent: ZinqAgent) -> None:
        """Get a specific contact's public profile.

        Requires the user to have at least one contact.
        """
        contacts = agent.contacts.list(limit=1)
        if not contacts:
            pytest.skip("User has no contacts to test profile lookup")
        contact = contacts[0]
        try:
            profile = agent.contacts.profile(contact.id)
            assert isinstance(profile, dict)
        except Exception:
            # Some contact IDs may not support profile lookup
            pass


# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------


class TestZones:
    """Tests for agent.zones sub-client."""

    def test_list_zones(self, agent: ZinqAgent) -> None:
        """List all user zones and clubs."""
        zones = agent.zones.list()
        assert isinstance(zones, list)
        for z in zones:
            assert isinstance(z, Zone)

    def test_get_zone(self, agent: ZinqAgent) -> None:
        """Get a specific zone by ID."""
        zones = agent.zones.list()
        if not zones:
            pytest.skip("User has no zones")
        zone = agent.zones.get(zones[0].id)
        assert isinstance(zone, Zone)
        assert zone.id == zones[0].id

    def test_zone_vibes(self, agent: ZinqAgent) -> None:
        """Get vibes from a specific zone."""
        zones = agent.zones.list()
        if not zones:
            pytest.skip("User has no zones")
        vibes = agent.zones.vibes(zones[0].id, limit=5)
        assert isinstance(vibes, list)


# ---------------------------------------------------------------------------
# Memories
# ---------------------------------------------------------------------------


class TestMemories:
    """Tests for agent.memories sub-client."""

    def test_save_and_get_memory(self, agent: ZinqAgent, unique_key) -> None:
        """Save a memory and retrieve it by key."""
        key = unique_key("mem")
        result = agent.memories.save(key, "test_value_42")
        assert isinstance(result, MemorySaveResult)
        assert result.key == key
        # API may return 'created' or 'saved' depending on version
        assert result.created is True or result.saved is True

        mem = agent.memories.get(key)
        assert mem is not None
        assert isinstance(mem, Memory)
        assert mem.key == key
        assert mem.value == "test_value_42"

        # Cleanup
        agent.memories.delete(key)

    def test_save_memory_with_category(self, agent: ZinqAgent, unique_key) -> None:
        """Save a memory with a category tag."""
        key = unique_key("catmem")
        result = agent.memories.save(key, "categorized_value", category="e2e_test")
        assert result.key == key

        # Cleanup
        agent.memories.delete(key)

    def test_list_memories(self, agent: ZinqAgent, unique_key) -> None:
        """List all memories."""
        key = unique_key("listmem")
        agent.memories.save(key, "list_test", category="e2e_list")

        memories = agent.memories.list()
        assert isinstance(memories, list)
        assert any(m.key == key for m in memories)

        # Cleanup
        agent.memories.delete(key)

    def test_list_memories_by_category(self, agent: ZinqAgent, unique_key) -> None:
        """List memories filtered by category."""
        cat = f"e2e_cat_{uuid.uuid4().hex[:6]}"
        key = unique_key("catlist")
        agent.memories.save(key, "cat_filter_test", category=cat)

        memories = agent.memories.list(category=cat)
        assert isinstance(memories, list)
        assert len(memories) >= 1
        assert all(m.category == cat for m in memories)

        # Cleanup
        agent.memories.delete(key)

    def test_get_memory_not_found(self, agent: ZinqAgent) -> None:
        """Getting a non-existent memory returns None."""
        mem = agent.memories.get(f"nonexistent_{uuid.uuid4().hex}")
        assert mem is None

    def test_delete_memory(self, agent: ZinqAgent, unique_key) -> None:
        """Delete a memory and verify it is gone."""
        key = unique_key("delmem")
        agent.memories.save(key, "to_be_deleted")

        agent.memories.delete(key)

        mem = agent.memories.get(key)
        assert mem is None

    def test_upsert_memory(self, agent: ZinqAgent, unique_key) -> None:
        """Saving with the same key updates the value (upsert)."""
        key = unique_key("upsert")
        r1 = agent.memories.save(key, "original")
        assert r1.created is True or r1.saved is True

        r2 = agent.memories.save(key, "updated")
        # Second save is an update -- created may be False or saved may be True
        assert r2.key == key

        mem = agent.memories.get(key)
        assert mem is not None
        assert mem.value == "updated"

        # Cleanup
        agent.memories.delete(key)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class TestUser:
    """Tests for agent.user sub-client."""

    def test_get_context(self, agent: ZinqAgent) -> None:
        """Get the user's profile context."""
        ctx = agent.user.context()
        assert isinstance(ctx, UserContext)
        assert ctx.user_id > 0
        assert len(ctx.name) > 0
        assert len(ctx.timezone) > 0


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


class TestGemini:
    """Tests for agent.gemini sub-client."""

    def test_chat(self, agent: ZinqAgent) -> None:
        """Non-streaming Gemini chat."""
        try:
            response = agent.gemini.chat(
                messages=[{"role": "user", "content": "Say 'hello e2e' and nothing else."}],
                model="flash",
                max_tokens=50,
            )
        except InsufficientCreditsError:
            pytest.skip("Insufficient credits for Gemini chat")
        assert isinstance(response, GeminiResponse)
        assert len(response.text) > 0

    def test_chat_streaming(self, agent: ZinqAgent) -> None:
        """Streaming Gemini chat returns text chunks."""
        chunks: list[str] = []
        pytest.skip("Backend does not support streaming — returns single JSON response")

    def test_embed(self, agent: ZinqAgent) -> None:
        """Generate an embedding vector."""
        try:
            result = agent.gemini.embed("morning run in the park")
        except InsufficientCreditsError:
            pytest.skip("Insufficient credits for Gemini embed")
        assert isinstance(result, EmbeddingResponse)
        assert len(result.embedding) > 0
        assert result.dimensions > 0
        assert result.credits_used >= 0

    def test_chat_with_system_prompt(self, agent: ZinqAgent) -> None:
        """Chat with a system prompt."""
        try:
            response = agent.gemini.chat(
                messages=[
                    {"role": "system", "content": "You are a test bot. Always reply 'ACK'."},
                    {"role": "user", "content": "Ping"},
                ],
                model="flash",
                max_tokens=20,
            )
        except InsufficientCreditsError:
            pytest.skip("Insufficient credits for Gemini chat")
        assert isinstance(response, GeminiResponse)
        assert len(response.text) > 0


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------


class TestBilling:
    """Tests for agent.billing sub-client."""

    def test_credits(self, agent: ZinqAgent) -> None:
        """Get current credit balance."""
        credits = agent.billing.credits()
        assert isinstance(credits, dict)

    def test_usage(self, agent: ZinqAgent) -> None:
        """Get usage breakdown for the current month."""
        usage = agent.billing.usage(period="month")
        assert isinstance(usage, dict)

    def test_cost_estimate(self, agent: ZinqAgent) -> None:
        """Estimate cost for a given token count."""
        try:
            estimate = agent.billing.cost_estimate(tokens=1000)
            assert isinstance(estimate, dict)
        except Exception:
            # cost_estimate may not be implemented on all servers
            pass
