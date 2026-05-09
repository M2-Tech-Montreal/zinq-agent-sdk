"""Marketplace admin client for Zinq Agent owners.

This module provides ``ZinqMarketplaceAdmin``, the admin client for
marketplace agent owners. It lets you deploy YAML definitions, view
users, reply to conversations, send broadcasts, and manage data
collections.

Usage::

    from zinq_agent import ZinqMarketplaceAdmin

    admin = ZinqMarketplaceAdmin(api_key="zbk_xxxxx")

    # Deploy your agent definition
    admin.agent.deploy(open("agent.yaml").read())

    # See who's using your agent
    users = admin.users.list()
    print(f"{admin.users.count()} active users")

    # Reply to a conversation awaiting human response
    convos = admin.conversations.list(status="awaiting_human")
    for c in convos:
        admin.conversations.reply(c["sessionId"], "Thanks for reaching out!")

    # Send a broadcast to all users
    admin.broadcast("We just launched a new feature!")
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from .exceptions import AuthenticationError
from .utils import raise_for_status as _raise_for_status

_DEFAULT_BASE_URL = "https://zinq-app.com/api"
_DEFAULT_TIMEOUT = 30.0


def _resolve_biz_key(api_key: str | None) -> str:
    """Resolve the business API key from argument or ZINQ_BIZ_KEY env var."""
    key = api_key or os.environ.get("ZINQ_BIZ_KEY")
    if not key:
        raise AuthenticationError(
            "No business API key provided. Set ZINQ_BIZ_KEY environment variable "
            "or pass api_key= to the ZinqMarketplaceAdmin constructor."
        )
    return key


# ---------------------------------------------------------------------------
# Sub-clients
# ---------------------------------------------------------------------------


class AgentLifecycleClient:
    """Manage your marketplace agent's lifecycle: deploy, update, enable/disable.

    Usage::

        admin.agent.deploy(open("agent.yaml").read())
        print(admin.agent.status())
        admin.agent.disable()
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def deploy(self, yaml: str) -> dict:
        """Submit a YAML agent definition for review.

        Args:
            yaml: The full YAML agent definition string.

        Returns:
            Dict with agent_id, status (e.g. ``"pending_review"``).
        """
        response = self._client.post("/agent/deploy", json={"yaml": yaml})
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def update(self, yaml: str) -> dict:
        """Update an existing agent definition.

        Args:
            yaml: The updated YAML agent definition string.

        Returns:
            Dict with agent_id and updated status.
        """
        response = self._client.put("/agent/definition", json={"yaml": yaml})
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def enable(self) -> dict:
        """Enable the agent (make it active in the marketplace).

        Returns:
            Dict with updated status.
        """
        response = self._client.post("/agent/enable")
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def disable(self) -> dict:
        """Disable the agent (remove from marketplace, existing users keep access).

        Returns:
            Dict with updated status.
        """
        response = self._client.post("/agent/disable")
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def status(self) -> dict:
        """Get the agent's current status.

        Returns:
            Dict with status (``"pending_review"``, ``"approved"``,
            ``"active"``, ``"disabled"``), name, created_at, etc.
        """
        response = self._client.get("/agent/status")
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def generate(self, description: str, *, name: str | None = None) -> dict:
        """Generate agent YAML from a business description using AI.

        Send a natural language description of your business and get back
        a complete YAML agent definition that you can review, edit, and deploy.

        Args:
            description: Natural language description of the business
                         (e.g., "I run a bakery with daily specials and pickup orders").
            name: Optional business name. Auto-extracted from description if not provided.

        Returns:
            Dict with: yaml (str), summary (dict with capabilities, collections).
        """
        body: dict[str, Any] = {"description": description}
        if name is not None:
            body["businessName"] = name
        response = self._client.post("/agent/generate", json=body)
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def upload_avatar(self, file_path: str) -> dict:
        """Upload an avatar image for the agent.

        Args:
            file_path: Path to image file (PNG, JPG, max 5MB).

        Returns:
            Dict with avatarUrl of the uploaded image.
        """
        with open(file_path, "rb") as f:
            response = self._client.post(
                "/agent/avatar",
                files={"file": f},
                headers={"Content-Type": None},  # let httpx set multipart
            )
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def set_webhook(self, url: str) -> dict:
        """Set the webhook URL for external tool calls.

        Args:
            url: HTTPS URL that receives tool call webhooks.

        Returns:
            Dict with updated webhook configuration.
        """
        response = self._client.put("/agent/webhook", json={"url": url})
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def publish(self) -> dict:
        """Submit agent for marketplace review.

        After you have tested and are satisfied with your agent, call this
        to submit it for review. Zinq reviews agents before they go live
        in the marketplace.

        Returns:
            Dict with: status ("pending_review"), estimated_review_time.
        """
        response = self._client.post("/agent/publish")
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def definition(self) -> str:
        """Get the current YAML definition.

        Returns:
            The YAML definition string.
        """
        response = self._client.get("/agent/definition")
        if not response.is_success:
            _raise_for_status(response)
        data = response.json()
        return data.get("yaml", "")

    def validate(self, yaml: str) -> dict:
        """Validate YAML structurally. Returns {valid, errors, warnings}.

        Checks syntax, required fields, types, and constraints without
        using AI. Fast and deterministic.

        Args:
            yaml: The YAML agent definition string to validate.

        Returns:
            Dict with: valid (bool), errors (list[str]), warnings (list[str]).
        """
        response = self._client.post("/agent/validate", json={"yaml": yaml})
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    def review(self, yaml: str) -> dict:
        """AI quality review. Returns {score, issues, suggestions}.

        Sends the YAML to an AI reviewer that scores the definition
        from 1-10 and provides actionable feedback.

        Args:
            yaml: The YAML agent definition string to review.

        Returns:
            Dict with: score (int, 1-10), issues (list[str]),
            suggestions (list[str]).
        """
        response = self._client.post("/agent/review", json={"yaml": yaml})
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    def refine(self, yaml: str, feedback: str) -> dict:
        """Refine YAML based on feedback. Returns {yaml, summary, changes}.

        Sends the existing YAML and user feedback to AI, which returns
        an improved version with a summary of what changed.

        Args:
            yaml: The existing YAML agent definition string.
            feedback: Natural language description of desired changes
                      (e.g., "add a delivery tracking tool" or
                      "make the tone more casual").

        Returns:
            Dict with: yaml (str), summary (dict), changes (list[str]).
        """
        response = self._client.post(
            "/agent/refine", json={"yaml": yaml, "feedback": feedback}
        )
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()


class MarketplaceUsersClient:
    """View pseudonymous user info for your marketplace agent.

    Users who enable your agent appear here. You see pseudonymous
    identifiers (name initial + avatar), never full profile data.

    Usage::

        print(f"Total users: {admin.users.count()}")
        for u in admin.users.list():
            print(u["sessionId"], u["nameInitial"])
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def list(self, *, limit: int = 50, offset: int = 0) -> list[dict]:
        """List users who have enabled this agent (pseudonymous).

        Args:
            limit: Max results per page (default 50, max 200).
            offset: Pagination offset.

        Returns:
            List of dicts with sessionId, nameInitial, avatarUrl, enabledAt.
        """
        response = self._client.get(
            "/users", params={"limit": limit, "offset": offset}
        )
        if not response.is_success:
            _raise_for_status(response)
        return response.json().get("users", [])

    def count(self) -> int:
        """Get total number of users who enabled this agent.

        Returns:
            Total user count.
        """
        response = self._client.get("/users/count")
        if not response.is_success:
            _raise_for_status(response)
        return response.json().get("count", 0)

    def profile(self, session_id: str) -> dict:
        """Get a user's public profile (name initial + avatar only).

        Args:
            session_id: The pseudonymous session identifier.

        Returns:
            Dict with nameInitial, avatarUrl, enabledAt, lastActiveAt.
        """
        response = self._client.get(f"/users/{session_id}/profile")
        if not response.is_success:
            _raise_for_status(response)
        return response.json()


class MarketplaceConversationsClient:
    """View and manage conversations with your agent's users.

    Usage::

        # List conversations awaiting human response
        convos = admin.conversations.list(status="awaiting_human")

        # Reply to a conversation
        admin.conversations.reply(session_id, "Thanks for your patience!")

        # Hand back to AI
        admin.conversations.resume_ai(session_id)
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def list(
        self,
        *,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """List all conversations, optionally filtered by status.

        Args:
            status: Filter by status: ``"awaiting_human"``, ``"active"``,
                    or ``"completed"``. None returns all.
            limit: Max results (default 20, max 100).

        Returns:
            List of conversation summary dicts.
        """
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            params["status"] = status

        response = self._client.get("/conversations", params=params)
        if not response.is_success:
            _raise_for_status(response)
        return response.json().get("conversations", [])

    def get(self, session_id: str) -> dict:
        """Get the full conversation history for a session.

        Args:
            session_id: The session identifier.

        Returns:
            Dict with sessionId, status, messages list, createdAt, updatedAt.
        """
        response = self._client.get(f"/conversations/{session_id}")
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def reply(self, session_id: str, text: str) -> dict:
        """Send a human reply vibe to a conversation.

        Args:
            session_id: The session to reply to.
            text: The reply text.

        Returns:
            Dict with vibeId, deliveredAt.
        """
        response = self._client.post(
            f"/conversations/{session_id}/reply",
            json={"text": text},
        )
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def resume_ai(self, session_id: str) -> dict:
        """Hand a conversation back to the AI agent.

        Args:
            session_id: The session to hand back.

        Returns:
            Dict with updated status.
        """
        response = self._client.post(
            f"/conversations/{session_id}/resume-ai"
        )
        if not response.is_success:
            _raise_for_status(response)
        return response.json()


class MarketplaceReviewsClient:
    """View user reviews and ratings for your marketplace agent.

    Usage::

        stats = admin.reviews.stats()
        print(f"Average rating: {stats['avg_rating']}")

        for review in admin.reviews.list():
            print(f"{review['rating']}/5: {review['text']}")
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def list(self, *, limit: int = 20, sort: str = "recent") -> list[dict]:
        """List all reviews for this agent.

        Args:
            limit: Max results (default 20, max 100).
            sort: Sort order: ``"recent"`` (default) or ``"highest"``
                  or ``"lowest"``.

        Returns:
            List of review dicts with rating, text, createdAt.
        """
        response = self._client.get(
            "/reviews", params={"limit": limit, "sort": sort}
        )
        if not response.is_success:
            _raise_for_status(response)
        return response.json().get("reviews", [])

    def stats(self) -> dict:
        """Get aggregate review statistics.

        Returns:
            Dict with avg_rating (float), total_count (int), and
            distribution (dict mapping star count to number of reviews,
            e.g. ``{1: 2, 2: 0, 3: 5, 4: 12, 5: 31}``).
        """
        response = self._client.get("/reviews/stats")
        if not response.is_success:
            _raise_for_status(response)
        return response.json()


class MarketplaceDataClient:
    """Manage data collections for your marketplace agent.

    Collections are key-value stores you can use to power your agent
    (e.g. product catalogs, FAQ entries, appointment slots).

    Usage::

        # Add a product
        admin.data.add("products", {"name": "Widget", "price": 9.99})

        # List all products
        for item in admin.data.list("products"):
            print(item["name"])

        # Clear test data
        admin.data.clear("products")
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def collections(self) -> list[dict]:
        """List all data collections with record counts.

        Returns:
            List of dicts with name, recordCount, createdAt, updatedAt.
        """
        response = self._client.get("/data/collections")
        if not response.is_success:
            _raise_for_status(response)
        return response.json().get("collections", [])

    def list(self, collection: str, *, limit: int = 50) -> list[dict]:
        """List records in a collection.

        Args:
            collection: Collection name.
            limit: Max results (default 50, max 200).

        Returns:
            List of record dicts.
        """
        response = self._client.get(
            f"/data/{collection}", params={"limit": limit}
        )
        if not response.is_success:
            _raise_for_status(response)
        return response.json().get("records", [])

    def add(self, collection: str, data: dict) -> dict:
        """Add a record to a collection.

        Args:
            collection: Collection name (created automatically if new).
            data: Record data as a dict.

        Returns:
            Dict with recordId and createdAt.
        """
        response = self._client.post(
            f"/data/{collection}", json={"data": data}
        )
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def update(self, collection: str, record_id: str, data: dict) -> dict:
        """Update a record in a collection.

        Args:
            collection: Collection name.
            record_id: The record ID to update.
            data: Updated record data.

        Returns:
            Dict with recordId and updatedAt.
        """
        response = self._client.put(
            f"/data/{collection}/{record_id}", json={"data": data}
        )
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def delete(self, collection: str, record_id: str) -> dict:
        """Delete a record from a collection.

        Args:
            collection: Collection name.
            record_id: The record ID to delete.

        Returns:
            Confirmation dict.
        """
        response = self._client.delete(f"/data/{collection}/{record_id}")
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def clear(self, collection: str) -> dict:
        """Clear all records from a collection.

        Args:
            collection: Collection name.

        Returns:
            Dict with deletedCount.
        """
        response = self._client.delete(f"/data/{collection}")
        if not response.is_success:
            _raise_for_status(response)
        return response.json()


class MarketplaceBillingClient:
    """Client for checking marketplace agent earnings and costs.

    Usage::

        earnings = admin.billing.earnings()
        print(f"Total earned: ${earnings['total_earned_usd']}")
        print(f"This month: ${earnings['this_month_usd']}")

        usage = admin.billing.usage()
        print(f"Active users: {usage['active_users']}")
        print(f"Gemini cost: ${usage['gemini_cost_usd']}")
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def earnings(self) -> dict:
        """Get earnings summary.

        Returns:
            Dict with: total_earned_usd, this_month_usd, pending_payout_usd,
            last_payout_date, next_payout_date, currency.
        """
        response = self._client.get("/billing/earnings")
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    def usage(self, *, period: str = "month") -> dict:
        """Get usage and cost breakdown.

        Args:
            period: "day", "week", "month" (default "month").

        Returns:
            Dict with: active_users, total_conversations, gemini_calls,
            gemini_tokens, gemini_cost_usd, revenue_usd, net_earnings_usd,
            breakdown_by_day.
        """
        response = self._client.get("/billing/usage", params={"period": period})
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    def payouts(self, *, limit: int = 10) -> list[dict]:
        """Get payout history.

        Args:
            limit: Max results (default 10).

        Returns:
            List of payout records with: amount_usd, date, status, method.
        """
        response = self._client.get("/billing/payouts", params={"limit": limit})
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json().get("payouts", [])


class MarketplaceTestClient:
    """Test your agent without a real user.

    Simulates a user conversation so you can verify your agent's
    behavior before going live.

    Usage::

        response = admin.test.chat("What services do you offer?")
        print(response["reply"])

        admin.test.reset()  # Clear test state
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def chat(self, text: str) -> dict:
        """Simulate a user message and get the agent's response.

        Args:
            text: The simulated user message.

        Returns:
            Dict with reply text, sessionId, and processing metadata.
        """
        response = self._client.post("/test/chat", json={"text": text})
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def reset(self) -> dict:
        """Clear the test conversation state.

        Returns:
            Confirmation dict.
        """
        response = self._client.post("/test/reset")
        if not response.is_success:
            _raise_for_status(response)
        return response.json()


# ===========================================================================
# Main admin client
# ===========================================================================


class ZinqMarketplaceAdmin:
    """Admin client for marketplace agent owners.

    Manage your marketplace agent: deploy YAML, view users,
    reply to conversations, send broadcasts, manage data.

    Usage::

        from zinq_agent import ZinqMarketplaceAdmin

        admin = ZinqMarketplaceAdmin(api_key="zbk_xxxxx")

        # Deploy your agent
        admin.agent.deploy(open("agent.yaml").read())

        # Check status
        print(admin.agent.status())

        # View users
        print(f"{admin.users.count()} users")

        # Reply to conversations
        for c in admin.conversations.list(status="awaiting_human"):
            admin.conversations.reply(c["sessionId"], "On it!")

        # Send a broadcast
        admin.broadcast("New feature launched!")

    Args:
        api_key: Business API key. Falls back to ``ZINQ_BIZ_KEY``
                 environment variable.
        base_url: Zinq backend URL (default: ``https://zinq-app.com/api``).
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = _DEFAULT_BASE_URL,
    ) -> None:
        self.api_key = _resolve_biz_key(api_key)
        self.base_url = base_url

        self._client = httpx.Client(
            base_url=f"{base_url}/marketplace/admin",
            headers={
                "X-Agent-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "zinq-agent-python/0.1.0",
            },
            timeout=_DEFAULT_TIMEOUT,
        )

        self.agent = AgentLifecycleClient(self._client)
        self.users = MarketplaceUsersClient(self._client)
        self.conversations = MarketplaceConversationsClient(self._client)
        self.reviews = MarketplaceReviewsClient(self._client)
        self.data = MarketplaceDataClient(self._client)
        self.billing = MarketplaceBillingClient(self._client)
        self.test = MarketplaceTestClient(self._client)

    def broadcast(self, text: str, *, options: dict | None = None) -> dict:
        """Send a broadcast vibe to all users who enabled this agent.

        Args:
            text: The broadcast message text.
            options: Optional dict with scheduling or targeting options
                     (e.g. ``{"schedule": "2026-04-20T10:00:00Z"}``).

        Returns:
            Dict with broadcastId, recipientCount, scheduledAt.
        """
        body: dict[str, Any] = {"text": text}
        if options is not None:
            body["options"] = options

        response = self._client.post("/broadcast", json=body)
        if not response.is_success:
            _raise_for_status(response)
        return response.json()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> ZinqMarketplaceAdmin:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}"
        return (
            f"ZinqMarketplaceAdmin(api_key='{masked_key}', "
            f"base_url='{self.base_url}')"
        )
