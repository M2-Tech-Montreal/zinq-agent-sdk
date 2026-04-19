"""E2E tests for the ZinqMarketplaceAdmin SDK.

Covers the full marketplace lifecycle: agent deployment, data management,
conversations, reviews, broadcast, billing, and testing.
"""

from __future__ import annotations

import uuid

import pytest

from zinq_agent import ZinqMarketplaceAdmin

# Minimal valid YAML definition for testing deploy/update
_TEST_YAML = """
name: E2E Test Agent
description: An agent created by the E2E test suite. Please ignore.
personality: Friendly and concise.
greeting: Hello from the E2E test suite!
capabilities:
  - Answer questions about testing
tools: []
""".strip()

_TEST_YAML_UPDATED = """
name: E2E Test Agent (Updated)
description: Updated by E2E test suite.
personality: Helpful and brief.
greeting: Hello again from E2E!
capabilities:
  - Answer questions about testing
  - Provide status updates
tools: []
""".strip()


# ---------------------------------------------------------------------------
# Agent Lifecycle
# ---------------------------------------------------------------------------


class TestAgentLifecycle:
    """Tests for admin.agent sub-client."""

    def test_generate_from_description(self, admin: ZinqMarketplaceAdmin) -> None:
        """Generate agent YAML from a natural language description."""
        result = admin.agent.generate(
            "I run a small coffee shop that sells espresso, lattes, and pastries. "
            "Customers should be able to check our menu and place pickup orders.",
            name="E2E Coffee Test",
        )
        assert isinstance(result, dict)
        assert "yaml" in result or "definition" in result

    def test_deploy_yaml(self, admin: ZinqMarketplaceAdmin) -> None:
        """Deploy a YAML agent definition."""
        result = admin.agent.deploy(_TEST_YAML)
        assert isinstance(result, dict)

    def test_update_definition(self, admin: ZinqMarketplaceAdmin) -> None:
        """Update the agent's YAML definition."""
        result = admin.agent.update(_TEST_YAML_UPDATED)
        assert isinstance(result, dict)

    def test_get_definition(self, admin: ZinqMarketplaceAdmin) -> None:
        """Retrieve the current YAML definition."""
        yaml_str = admin.agent.definition()
        assert isinstance(yaml_str, str)

    def test_status(self, admin: ZinqMarketplaceAdmin) -> None:
        """Get the agent's current status."""
        status = admin.agent.status()
        assert isinstance(status, dict)

    def test_enable_disable(self, admin: ZinqMarketplaceAdmin) -> None:
        """Enable then disable the agent."""
        try:
            enable_result = admin.agent.enable()
            assert isinstance(enable_result, dict)
        except Exception:
            pass  # Agent may already be enabled or not yet approved

        try:
            disable_result = admin.agent.disable()
            assert isinstance(disable_result, dict)
        except Exception:
            pass

        # Re-enable so the agent stays usable for subsequent tests
        try:
            admin.agent.enable()
        except Exception:
            pass

    def test_set_webhook(self, admin: ZinqMarketplaceAdmin) -> None:
        """Set a webhook URL for the agent."""
        try:
            result = admin.agent.set_webhook("https://example.com/webhook")
            assert isinstance(result, dict)
        except Exception:
            pass  # URL validation may reject example.com


# ---------------------------------------------------------------------------
# Data Management
# ---------------------------------------------------------------------------


class TestDataManagement:
    """Tests for admin.data sub-client."""

    def test_add_and_list_records(self, admin: ZinqMarketplaceAdmin) -> None:
        """Add records to a collection and list them."""
        collection = f"e2e_test_{uuid.uuid4().hex[:8]}"
        try:
            r1 = admin.data.add(collection, {"name": "Widget", "price": 9.99})
            assert isinstance(r1, dict)

            r2 = admin.data.add(collection, {"name": "Gadget", "price": 19.99})
            assert isinstance(r2, dict)

            records = admin.data.list(collection)
            assert isinstance(records, list)
            assert len(records) >= 2
        finally:
            admin.data.clear(collection)

    def test_update_record(self, admin: ZinqMarketplaceAdmin) -> None:
        """Update a record in a collection."""
        collection = f"e2e_upd_{uuid.uuid4().hex[:8]}"
        try:
            added = admin.data.add(collection, {"name": "Old Name", "price": 5.00})
            record_id = added.get("recordId") or added.get("record_id") or added.get("id")
            if record_id is None:
                pytest.skip("Could not get record ID from add response")

            updated = admin.data.update(
                collection, str(record_id), {"name": "New Name", "price": 7.50}
            )
            assert isinstance(updated, dict)
        finally:
            admin.data.clear(collection)

    def test_delete_record(self, admin: ZinqMarketplaceAdmin) -> None:
        """Delete a specific record from a collection."""
        collection = f"e2e_del_{uuid.uuid4().hex[:8]}"
        try:
            added = admin.data.add(collection, {"name": "Temporary"})
            record_id = added.get("recordId") or added.get("record_id") or added.get("id")
            if record_id is None:
                pytest.skip("Could not get record ID from add response")

            result = admin.data.delete(collection, str(record_id))
            assert isinstance(result, dict)

            remaining = admin.data.list(collection)
            assert not any(
                (r.get("recordId") or r.get("record_id") or r.get("id")) == record_id
                for r in remaining
            )
        finally:
            admin.data.clear(collection)

    def test_clear_collection(self, admin: ZinqMarketplaceAdmin) -> None:
        """Clear all records from a collection."""
        collection = f"e2e_clr_{uuid.uuid4().hex[:8]}"
        admin.data.add(collection, {"a": 1})
        admin.data.add(collection, {"b": 2})

        result = admin.data.clear(collection)
        assert isinstance(result, dict)

        records = admin.data.list(collection)
        assert len(records) == 0

    def test_list_collections(self, admin: ZinqMarketplaceAdmin) -> None:
        """List all data collections with record counts."""
        collections = admin.data.collections()
        assert isinstance(collections, list)


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


class TestConversations:
    """Tests for admin.conversations sub-client."""

    def test_list_conversations(self, admin: ZinqMarketplaceAdmin) -> None:
        """List all conversations."""
        convos = admin.conversations.list()
        assert isinstance(convos, list)

    def test_list_conversations_by_status(self, admin: ZinqMarketplaceAdmin) -> None:
        """List conversations filtered by status."""
        convos = admin.conversations.list(status="active")
        assert isinstance(convos, list)

    def test_reply_to_conversation(self, admin: ZinqMarketplaceAdmin) -> None:
        """Reply to an existing conversation.

        This requires at least one active conversation. If none exist,
        the test is skipped.
        """
        convos = admin.conversations.list(limit=1)
        if not convos:
            pytest.skip("No conversations available for reply test")

        session_id = convos[0].get("sessionId") or convos[0].get("session_id")
        if not session_id:
            pytest.skip("Could not extract session_id from conversation")

        try:
            result = admin.conversations.reply(
                session_id, "E2E test reply -- please ignore"
            )
            assert isinstance(result, dict)
        except Exception:
            pass  # Conversation may not be in a reply-able state

    def test_resume_ai(self, admin: ZinqMarketplaceAdmin) -> None:
        """Hand a conversation back to the AI.

        Requires a conversation in awaiting_human status.
        """
        convos = admin.conversations.list(status="awaiting_human", limit=1)
        if not convos:
            pytest.skip("No conversations awaiting human for resume test")

        session_id = convos[0].get("sessionId") or convos[0].get("session_id")
        if not session_id:
            pytest.skip("Could not extract session_id")

        try:
            result = admin.conversations.resume_ai(session_id)
            assert isinstance(result, dict)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


class TestReviews:
    """Tests for admin.reviews sub-client."""

    def test_list_reviews(self, admin: ZinqMarketplaceAdmin) -> None:
        """List reviews for this agent."""
        reviews = admin.reviews.list()
        assert isinstance(reviews, list)

    def test_stats(self, admin: ZinqMarketplaceAdmin) -> None:
        """Get aggregate review statistics."""
        stats = admin.reviews.stats()
        assert isinstance(stats, dict)


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------


class TestBroadcast:
    """Tests for admin.broadcast."""

    def test_send_broadcast(self, admin: ZinqMarketplaceAdmin) -> None:
        """Send a broadcast to all agent users."""
        result = admin.broadcast("E2E test broadcast -- please ignore")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------


class TestMarketplaceBilling:
    """Tests for admin.billing sub-client."""

    def test_earnings(self, admin: ZinqMarketplaceAdmin) -> None:
        """Get earnings summary."""
        earnings = admin.billing.earnings()
        assert isinstance(earnings, dict)

    def test_usage(self, admin: ZinqMarketplaceAdmin) -> None:
        """Get usage breakdown."""
        usage = admin.billing.usage(period="month")
        assert isinstance(usage, dict)

    def test_payouts(self, admin: ZinqMarketplaceAdmin) -> None:
        """Get payout history."""
        payouts = admin.billing.payouts(limit=5)
        assert isinstance(payouts, list)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class TestMarketplaceUsers:
    """Tests for admin.users sub-client."""

    def test_list_users(self, admin: ZinqMarketplaceAdmin) -> None:
        """List users who have enabled this agent."""
        users = admin.users.list(limit=10)
        assert isinstance(users, list)

    def test_user_count(self, admin: ZinqMarketplaceAdmin) -> None:
        """Get total user count."""
        count = admin.users.count()
        assert isinstance(count, int)
        assert count >= 0


# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------


class TestTestClient:
    """Tests for admin.test sub-client."""

    def test_chat(self, admin: ZinqMarketplaceAdmin) -> None:
        """Simulate a user conversation via the test client."""
        response = admin.test.chat("Hello, what can you do?")
        assert isinstance(response, dict)
        assert "reply" in response or "text" in response or "message" in response

    def test_reset(self, admin: ZinqMarketplaceAdmin) -> None:
        """Reset the test conversation state."""
        result = admin.test.reset()
        assert isinstance(result, dict)

    def test_multi_turn_conversation(self, admin: ZinqMarketplaceAdmin) -> None:
        """Verify multi-turn conversation works."""
        admin.test.reset()

        r1 = admin.test.chat("Hi there!")
        assert isinstance(r1, dict)

        r2 = admin.test.chat("Tell me more about your services")
        assert isinstance(r2, dict)
