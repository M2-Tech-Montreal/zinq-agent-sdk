"""Main ZinqAgent client and sub-clients.

This module contains the primary entry point for the SDK. All API
interactions go through the ``ZinqAgent`` class (sync) or
``AsyncZinqAgent`` class (async) which expose typed sub-clients
for each API domain.

Usage::

    from zinq_agent import ZinqAgent

    # API key from ZINQ_API_KEY env var (auto-read)
    agent = ZinqAgent()

    # Or pass explicitly
    agent = ZinqAgent(api_key="zak_xxxxx")

    # Context manager (auto-closes connections)
    with ZinqAgent() as agent:
        for entry in agent.diary.list():
            print(entry.text)

    # Async variant
    async with AsyncZinqAgent() as agent:
        page = await agent.diary.list()
        for entry in page.entries:
            print(entry.text)
"""

from __future__ import annotations

import os
from typing import Any, Iterator

import httpx

from .exceptions import AuthenticationError
from .gemini import AsyncGeminiClient, GeminiClient
from .utils import raise_for_status as _raise_for_status
from .models import (
    Contact,
    DiaryEntry,
    DiaryPage,
    Memory,
    MemorySaveResult,
    SearchResults,
    UserContext,
    Vibe,
    VibeSendResult,
    Zone,
)

_DEFAULT_BASE_URL = "https://zinq-app.com/api"
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_api_key(api_key: str | None) -> str:
    """Resolve the API key from argument or ZINQ_API_KEY env var."""
    key = api_key or os.environ.get("ZINQ_API_KEY")
    if not key:
        raise AuthenticationError(
            "No API key provided. Set ZINQ_API_KEY environment variable "
            "or pass api_key= to the client constructor."
        )
    if not key.startswith("zak_"):
        raise ValueError(
            f"Invalid API key format. Expected 'zak_' prefix, got '{key[:4]}...'"
        )
    return key


# ===========================================================================
# Resource clients (sync)
# ===========================================================================


class DiaryClient:
    """Client for reading the user's diary entries.

    Supports page-based access (``list``) and an auto-paginating
    iterator (``iter``).

    Usage::

        # Page-based
        page = agent.diary.list(start="2026-04-01")
        for entry in page.entries:
            print(entry.text)

        # Auto-paginating iterator
        for entry in agent.diary.iter(start="2026-04-01"):
            print(entry.text)
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def list(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        tags: list[str] | None = None,
        page: int = 0,
        size: int = 20,
    ) -> DiaryPage:
        """List diary entries with optional filters.

        Args:
            start: ISO date string for the earliest entry (inclusive).
            end: ISO date string for the latest entry (inclusive).
            tags: List of AI tags to filter by (e.g., ``["fitness", "nutrition"]``).
            page: Page number (0-indexed, default 0).
            size: Page size (default 20, max 100).

        Returns:
            DiaryPage with entries and pagination info.
        """
        params: dict[str, Any] = {"page": page, "size": size}
        if start is not None:
            params["from"] = start
        if end is not None:
            params["to"] = end
        if tags is not None:
            params["tags"] = ",".join(tags)

        response = self._client.get("/diary", params=params)
        if response.status_code != 200:
            _raise_for_status(response)

        data = response.json()
        page_obj = DiaryPage.model_validate(data)
        # Compute total_pages from total entries and page size if not provided
        if page_obj.total_pages == 0 and page_obj.total_entries > 0:
            page_size = data.get("size", size)
            page_obj.total_pages = (page_obj.total_entries + page_size - 1) // page_size
        return page_obj

    def iter(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        tags: list[str] | None = None,
        size: int = 50,
    ) -> Iterator[DiaryEntry]:
        """Auto-paginating iterator over diary entries.

        Fetches pages automatically until all entries are returned.

        Args:
            start: ISO date string for the earliest entry (inclusive).
            end: ISO date string for the latest entry (inclusive).
            tags: List of AI tags to filter by.
            size: Page size per request (default 50).

        Yields:
            DiaryEntry objects in reverse chronological order.
        """
        page_num = 0
        while True:
            page = self.list(start=start, end=end, tags=tags, page=page_num, size=size)
            yield from page.entries
            if page_num >= page.total_pages - 1:
                break
            page_num += 1

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        start: str | None = None,
        end: str | None = None,
    ) -> SearchResults:
        """Semantic search over the user's diary.

        Args:
            query: Natural language search query.
            limit: Maximum number of results (default 10, max 50).
            start: ISO date string for the earliest entry.
            end: ISO date string for the latest entry.

        Returns:
            SearchResults with ranked results and credit usage.
        """
        params: dict[str, Any] = {"q": query, "limit": limit}
        if start is not None:
            params["from"] = start
        if end is not None:
            params["to"] = end

        response = self._client.get("/diary/search", params=params)
        if response.status_code != 200:
            _raise_for_status(response)

        return SearchResults.model_validate(response.json())

    def save(self, text: str, *, mood_score: int | None = None) -> dict:
        """Save a new entry to the user's diary.

        Args:
            text: The diary entry text.
            mood_score: Optional mood score 1-10.

        Returns:
            Dict with vibe_id of the created diary entry.
        """
        body: dict[str, Any] = {"textContent": text}
        if mood_score is not None:
            body["moodScore"] = mood_score

        response = self._client.post("/diary", json=body)
        if response.status_code not in (200, 201):
            _raise_for_status(response)

        return response.json()

    def star(self, vibe_id: int, *, rating: int = 1) -> dict:
        """Star/save a vibe to the diary.

        Args:
            vibe_id: The vibe to star.
            rating: Star rating (default 1).

        Returns:
            Confirmation dict.
        """
        response = self._client.post(
            f"/diary/{vibe_id}/star", json={"rating": rating}
        )
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    def archive(self, vibe_id: int) -> dict:
        """Archive a vibe (soft delete from diary).

        Args:
            vibe_id: The vibe to archive.

        Returns:
            Confirmation dict.
        """
        response = self._client.post(f"/diary/{vibe_id}/archive")
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()


class VibeClient:
    """Client for sending vibes to the user and reading received vibes.

    Usage::

        agent.vibes.send(text="Time for your afternoon walk!")
        vibes = agent.vibes.received(unread=True)
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def send(
        self,
        text: str,
        *,
        vibe_type: str = "TEXT",
        input_type: str | None = None,
        options: list[str] | None = None,
        buttons: list[dict[str, str]] | None = None,
        reply_to: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VibeSendResult:
        """Send a vibe (message) from the agent to the user.

        Args:
            text: Vibe text content (max 10,000 chars).
            vibe_type: ``"TEXT"`` (default) or ``"NOTIFICATION"``.
            input_type: Interactive input type: ``"yes_no"``, ``"choice"``,
                        ``"text_input"``, or ``"rating"``.
            options: Options for ``"choice"`` input type.
            buttons: Up to 4 buttons, each a dict with ``"label"`` and ``"value"``.
            reply_to: Vibe ID to reply to (for threaded replies).
            metadata: Arbitrary JSON stored with the vibe (max 4KB).

        Returns:
            VibeSendResult with vibe_id, delivered_at, and push_sent.
        """
        body: dict[str, Any] = {
            "textContent": text,
            "type": vibe_type,
        }

        interactive: dict[str, Any] = {}
        if input_type is not None:
            interactive["inputType"] = input_type
        if options is not None:
            interactive["options"] = options
        if buttons is not None:
            interactive["buttons"] = buttons
        if interactive:
            body["interactive"] = interactive

        if reply_to is not None:
            body["replyToVibeId"] = reply_to
        if metadata is not None:
            body["metadata"] = metadata

        response = self._client.post("/vibes/send", json=body)
        if response.status_code != 200:
            _raise_for_status(response)

        return VibeSendResult.model_validate(response.json())

    def send_to(self, recipient_user_id: int, text: str) -> VibeSendResult:
        """Send a vibe from the owner to a specific connection (on their behalf).

        Args:
            recipient_user_id: The user ID of the connection to send to.
            text: The vibe text content.
        """
        body = {"textContent": text, "recipientUserId": recipient_user_id}
        response = self._client.post("/vibes/send-to", json=body)
        if response.status_code != 200:
            _raise_for_status(response)
        return VibeSendResult.model_validate(response.json())

    def send_charm(self, target_user_id: int, charm_type: str = "wave") -> dict:
        """Send a charm from the owner to a connection (on their behalf).

        Args:
            target_user_id: The user ID to send the charm to.
            charm_type: Type of charm (wave, thumbs_up, heart, etc.)
        """
        body = {"targetUserId": target_user_id, "charmType": charm_type}
        response = self._client.post("/charms/send", json=body)
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    def send_to_zone(self, zone_id: int, text: str) -> VibeSendResult:
        """Send a vibe to a zone/club (on behalf of the owner).

        Args:
            zone_id: The zone ID to post to.
            text: The vibe text content.
        """
        body = {"textContent": text, "zoneId": zone_id}
        response = self._client.post("/vibes/send-to-zone", json=body)
        if response.status_code != 200:
            _raise_for_status(response)
        return VibeSendResult.model_validate(response.json())

    def received(
        self,
        *,
        since: str | None = None,
        limit: int = 20,
        unread: bool = False,
    ) -> list[Vibe]:
        """Get vibes sent to this agent by the user.

        Args:
            since: ISO datetime string. Only return vibes after this timestamp.
            limit: Maximum number of results (default 20, max 100).
            unread: If True, only return unread vibes (default False).

        Returns:
            List of Vibe objects.
        """
        params: dict[str, Any] = {"limit": limit}
        if since is not None:
            params["since"] = since
        if unread:
            params["unread"] = "true"

        response = self._client.get("/vibes/received", params=params)
        if response.status_code != 200:
            _raise_for_status(response)

        data = response.json()
        return [Vibe.model_validate(v) for v in data.get("vibes", [])]


class MemoryClient:
    """Client for persistent key-value storage.

    Memories are scoped to this agent and user. Max 500 memories per agent per user.

    Usage::

        agent.memories.save(key="preferred_workout", value="morning yoga")
        pref = agent.memories.get("preferred_workout")
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def list(self, *, category: str | None = None) -> list[Memory]:
        """List all memories, optionally filtered by category.

        Args:
            category: Filter by category string.

        Returns:
            List of Memory objects.
        """
        response = self._client.get("/memories")
        if response.status_code != 200:
            _raise_for_status(response)

        data = response.json()
        memories = [Memory.model_validate(m) for m in data.get("memories", [])]
        if category is not None:
            memories = [m for m in memories if m.category == category]
        return memories

    def get(self, key: str) -> Memory | None:
        """Get a specific memory by key.

        Args:
            key: The memory key.

        Returns:
            Memory object if found, None otherwise.
        """
        response = self._client.get("/memories")
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            _raise_for_status(response)

        data = response.json()
        memories = data.get("memories", [])
        for m in memories:
            if m.get("key") == key:
                return Memory.model_validate(m)
        return None

    def save(
        self,
        key: str,
        value: str,
        *,
        category: str | None = None,
    ) -> MemorySaveResult:
        """Save or update a memory (upsert).

        Args:
            key: Memory key (max 100 chars, unique per agent+user).
            value: Memory value (max 10KB).
            category: Optional category for grouping (max 50 chars).

        Returns:
            MemorySaveResult with key, created flag, and updated_at.
        """
        body: dict[str, Any] = {"key": key, "value": value}
        if category is not None:
            body["category"] = category

        response = self._client.post("/memories", json=body)
        if response.status_code != 200:
            _raise_for_status(response)

        return MemorySaveResult.model_validate(response.json())

    def delete(self, key: str) -> None:
        """Delete a specific memory by key.

        Args:
            key: The memory key to delete.

        Raises:
            NotFoundError: If the memory key does not exist.
        """
        response = self._client.delete(f"/memories/{key}")
        if response.status_code not in (200, 204):
            _raise_for_status(response)


class ContactsClient:
    """Client for reading the user's connections/contacts.

    Requires the ``contacts`` data access permission to be enabled
    by the user in My Agents settings.

    Usage::

        contacts = agent.contacts.list()
        for c in contacts:
            print(f"{c.name} — last active {c.last_active}")

        # Search by name
        results = agent.contacts.search("Glenn")
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def list(self, *, limit: int = 50, offset: int = 0) -> list[Contact]:
        """List the user's connections.

        Args:
            limit: Max results per page (default 50, max 200).
            offset: Pagination offset.

        Returns:
            List of Contact objects with name, avatar, status, zone.
        """
        response = self._client.get(
            "/contacts", params={"limit": limit, "offset": offset}
        )
        if response.status_code != 200:
            _raise_for_status(response)

        return [Contact.model_validate(c) for c in response.json().get("contacts", [])]

    def search(self, query: str, *, limit: int = 10) -> list[Contact]:
        """Search contacts by name.

        Args:
            query: Name to search for (case-insensitive partial match).
            limit: Max results (default 10).

        Returns:
            Matching Contact objects.
        """
        response = self._client.get(
            "/contacts/search", params={"q": query, "limit": limit}
        )
        if response.status_code != 200:
            _raise_for_status(response)

        return [Contact.model_validate(c) for c in response.json().get("contacts", [])]

    def get(self, contact_id: str) -> Contact:
        """Get a single contact by ID.

        Args:
            contact_id: The connection ID.

        Returns:
            Contact object.
        """
        response = self._client.get(f"/contacts/{contact_id}")
        if response.status_code != 200:
            _raise_for_status(response)

        return Contact.model_validate(response.json())

    def profile(self, user_id: int) -> dict:
        """Get a contact's public profile.

        Returns public info: name, avatar, bio, zones. Does NOT return
        private data (phone, email, diary).

        Args:
            user_id: The user ID to look up.

        Returns:
            Dict with public profile fields.
        """
        response = self._client.get(f"/contacts/{user_id}/profile")
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()


class ZonesClient:
    """Client for reading the user's zones (life zones and clubs).

    Usage::

        zones = agent.zones.list()
        for z in zones:
            print(f"{z.name} ({z.zone_type}) — {z.member_count} members")

        # Get vibes from a specific zone/club
        vibes = agent.zones.vibes(zone_id=42, limit=20)
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def list(self) -> list[Zone]:
        """List all of the user's zones (life zones + clubs).

        Returns:
            List of Zone objects.
        """
        response = self._client.get("/zones")
        if response.status_code != 200:
            _raise_for_status(response)

        return [Zone.model_validate(z) for z in response.json().get("zones", [])]

    def get(self, zone_id: int) -> Zone:
        """Get a zone/club's profile (name, description, member count).

        Args:
            zone_id: The zone/club ID.

        Returns:
            Zone object.
        """
        response = self._client.get(f"/zones/{zone_id}")
        if response.status_code != 200:
            _raise_for_status(response)
        return Zone.model_validate(response.json())

    def vibes(self, zone_id: int, *, limit: int = 20, offset: int = 0) -> list[Vibe]:
        """Get vibes from a specific zone or club.

        Args:
            zone_id: The zone/club ID.
            limit: Max results (default 20).
            offset: Pagination offset.

        Returns:
            List of Vibe objects from that zone.
        """
        response = self._client.get(
            f"/zones/{zone_id}/vibes",
            params={"limit": limit, "offset": offset},
        )
        if response.status_code != 200:
            _raise_for_status(response)

        return [Vibe.model_validate(v) for v in response.json().get("vibes", [])]


    def create(
        self,
        name: str,
        *,
        zone_type: str = "club",
        description: str | None = None,
    ) -> Zone:
        """Create a new zone or club.

        Args:
            name: Display name for the zone/club.
            zone_type: "life", "club", or "event" (default "club").
            description: Optional description.

        Returns:
            The created Zone object.
        """
        body: dict[str, Any] = {"name": name, "zoneType": zone_type}
        if description:
            body["description"] = description

        response = self._client.post("/zones", json=body)
        if response.status_code not in (200, 201):
            _raise_for_status(response)

        return Zone.model_validate(response.json())

    def invite(self, zone_id: int, user_ids: list[int]) -> dict:
        """Invite users to a club/zone.

        Args:
            zone_id: The club/zone ID.
            user_ids: List of user IDs to invite.

        Returns:
            Confirmation dict.
        """
        response = self._client.post(
            f"/zones/{zone_id}/invite",
            json={"userIds": user_ids},
        )
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()


class FeedClient:
    """Client for reading the user's vibe feed.

    Usage::

        vibes = agent.feed.list(limit=10)
        for v in vibes:
            print(f"{v.user_name}: {v.text or v.transcript_summary}")
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def list(self, *, limit: int = 20, offset: int = 0) -> list[Vibe]:
        """Get the user's vibe feed (vibes from connections).

        Args:
            limit: Max results (default 20).
            offset: Pagination offset.

        Returns:
            List of Vibe objects.
        """
        response = self._client.get(
            "/feed", params={"limit": limit, "offset": offset}
        )
        if response.status_code != 200:
            _raise_for_status(response)

        return [Vibe.model_validate(v) for v in response.json().get("vibes", [])]


class BillingClient:
    """Client for checking credits, usage, and costs.

    Usage::

        credits = agent.billing.credits()
        print(f"Remaining: {credits['remaining']} credits")

        usage = agent.billing.usage()
        print(f"This month: {usage['total_tokens']} tokens, {usage['total_cost_usd']}")
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def credits(self) -> dict:
        """Get current credit balance.

        Returns:
            Dict with: remaining, used_this_month, total_purchased,
            reset_date, tier.
        """
        response = self._client.get("/billing/credits")
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    def usage(self, *, period: str = "month") -> dict:
        """Get usage breakdown.

        Args:
            period: "day", "week", "month" (default "month").

        Returns:
            Dict with: total_tokens, total_calls, total_cost_usd,
            gemini_chat_calls, gemini_embed_calls, breakdown_by_day.
        """
        response = self._client.get("/billing/usage", params={"period": period})
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    def cost_estimate(self, tokens: int) -> dict:
        """Estimate cost for a given token count.

        Args:
            tokens: Number of tokens to estimate cost for.

        Returns:
            Dict with: estimated_credits, estimated_cost_usd.
        """
        response = self._client.get("/billing/estimate", params={"tokens": tokens})
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()


class UserClient:
    """Client for reading user context (profile and preferences).

    Usage::

        ctx = agent.user.context()
        print(f"User: {ctx.name}, TZ: {ctx.timezone}")
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._client = http_client

    def context(self) -> UserContext:
        """Get the user's profile information and preferences.

        Returns:
            UserContext with name, timezone, preferences, and credit status.
        """
        response = self._client.get("/user/context")
        if response.status_code != 200:
            _raise_for_status(response)

        return UserContext.model_validate(response.json())

    def profile(self) -> dict:
        """Get the agent's own profile (name, bio, avatar, etc.)."""
        response = self._client.get("/profile")
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    def update_profile(
        self,
        *,
        name: str | None = None,
        nickname: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
    ) -> dict:
        """Update the agent's own profile. Only provided fields are changed.

        Args:
            name: Display name (3-50 chars).
            nickname: Short name.
            bio: One-line description (max 200 chars).
            avatar_url: Profile image URL.

        Returns:
            Updated agent profile dict.
        """
        body: dict[str, str] = {}
        if name is not None:
            body["name"] = name
        if nickname is not None:
            body["nickname"] = nickname
        if bio is not None:
            body["bio"] = bio
        if avatar_url is not None:
            body["avatarUrl"] = avatar_url

        response = self._client.put("/profile", json=body)
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    def upload_avatar(self, file_path: str) -> dict:
        """Upload an avatar image for the agent.

        Args:
            file_path: Path to image file (PNG or JPEG, max 5MB).

        Returns:
            Dict with ``avatarUrl`` of the uploaded image.
        """
        import mimetypes
        mime = mimetypes.guess_type(file_path)[0] or "image/png"
        name = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
        with open(file_path, "rb") as f:
            response = self._client.post(
                "/profile/avatar",
                files={"file": (name, f, mime)},
            )
        if not response.is_success:
            _raise_for_status(response)
        return response.json()


# ===========================================================================
# Resource clients (async)
# ===========================================================================


class AsyncDiaryClient:
    """Async client for reading the user's diary entries."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    async def list(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        tags: list[str] | None = None,
        page: int = 0,
        size: int = 20,
    ) -> DiaryPage:
        """List diary entries with optional filters.

        Args:
            start: ISO date string for the earliest entry (inclusive).
            end: ISO date string for the latest entry (inclusive).
            tags: List of AI tags to filter by.
            page: Page number (0-indexed, default 0).
            size: Page size (default 20, max 100).

        Returns:
            DiaryPage with entries and pagination info.
        """
        params: dict[str, Any] = {"page": page, "size": size}
        if start is not None:
            params["from"] = start
        if end is not None:
            params["to"] = end
        if tags is not None:
            params["tags"] = ",".join(tags)

        response = await self._client.get("/diary", params=params)
        if response.status_code != 200:
            _raise_for_status(response)

        data = response.json()
        page_obj = DiaryPage.model_validate(data)
        # Compute total_pages from total entries and page size if not provided
        if page_obj.total_pages == 0 and page_obj.total_entries > 0:
            page_size = data.get("size", size)
            page_obj.total_pages = (page_obj.total_entries + page_size - 1) // page_size
        return page_obj

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        start: str | None = None,
        end: str | None = None,
    ) -> SearchResults:
        """Semantic search over the user's diary."""
        params: dict[str, Any] = {"q": query, "limit": limit}
        if start is not None:
            params["from"] = start
        if end is not None:
            params["to"] = end

        response = await self._client.get("/diary/search", params=params)
        if response.status_code != 200:
            _raise_for_status(response)

        return SearchResults.model_validate(response.json())


class AsyncVibeClient:
    """Async client for sending vibes to the user and reading received vibes."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    async def send(
        self,
        text: str,
        *,
        vibe_type: str = "TEXT",
        input_type: str | None = None,
        options: list[str] | None = None,
        buttons: list[dict[str, str]] | None = None,
        reply_to: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VibeSendResult:
        """Send a vibe (message) from the agent to the user."""
        body: dict[str, Any] = {"textContent": text, "type": vibe_type}

        interactive: dict[str, Any] = {}
        if input_type is not None:
            interactive["inputType"] = input_type
        if options is not None:
            interactive["options"] = options
        if buttons is not None:
            interactive["buttons"] = buttons
        if interactive:
            body["interactive"] = interactive

        if reply_to is not None:
            body["replyToVibeId"] = reply_to
        if metadata is not None:
            body["metadata"] = metadata

        response = await self._client.post("/vibes/send", json=body)
        if response.status_code != 200:
            _raise_for_status(response)

        return VibeSendResult.model_validate(response.json())

    async def received(
        self,
        *,
        since: str | None = None,
        limit: int = 20,
        unread: bool = False,
    ) -> list[Vibe]:
        """Get vibes sent to this agent by the user."""
        params: dict[str, Any] = {"limit": limit}
        if since is not None:
            params["since"] = since
        if unread:
            params["unread"] = "true"

        response = await self._client.get("/vibes/received", params=params)
        if response.status_code != 200:
            _raise_for_status(response)

        data = response.json()
        return [Vibe.model_validate(v) for v in data.get("vibes", [])]


class AsyncMemoryClient:
    """Async client for persistent key-value storage."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    async def list(self, *, category: str | None = None) -> list[Memory]:
        """List all memories, optionally filtered by category."""
        response = await self._client.get("/memories")
        if response.status_code != 200:
            _raise_for_status(response)

        data = response.json()
        memories = [Memory.model_validate(m) for m in data.get("memories", [])]
        if category is not None:
            memories = [m for m in memories if m.category == category]
        return memories

    async def get(self, key: str) -> Memory | None:
        """Get a specific memory by key."""
        response = await self._client.get("/memories")
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            _raise_for_status(response)

        data = response.json()
        memories = data.get("memories", [])
        for m in memories:
            if m.get("key") == key:
                return Memory.model_validate(m)
        return None

    async def save(
        self, key: str, value: str, *, category: str | None = None
    ) -> MemorySaveResult:
        """Save or update a memory (upsert)."""
        body: dict[str, Any] = {"key": key, "value": value}
        if category is not None:
            body["category"] = category

        response = await self._client.post("/memories", json=body)
        if response.status_code != 200:
            _raise_for_status(response)

        return MemorySaveResult.model_validate(response.json())

    async def delete(self, key: str) -> None:
        """Delete a specific memory by key."""
        response = await self._client.delete(f"/memories/{key}")
        if response.status_code not in (200, 204):
            _raise_for_status(response)


class AsyncUserClient:
    """Async client for reading user context."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    async def context(self) -> UserContext:
        """Get the user's profile information and preferences."""
        response = await self._client.get("/user/context")
        if response.status_code != 200:
            _raise_for_status(response)

        return UserContext.model_validate(response.json())

    async def profile(self) -> dict:
        """Get the agent's own profile."""
        response = await self._client.get("/profile")
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()

    async def update_profile(
        self,
        *,
        name: str | None = None,
        nickname: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
    ) -> dict:
        """Update the agent's own profile. Only provided fields are changed."""
        body: dict[str, str] = {}
        if name is not None:
            body["name"] = name
        if nickname is not None:
            body["nickname"] = nickname
        if bio is not None:
            body["bio"] = bio
        if avatar_url is not None:
            body["avatarUrl"] = avatar_url

        response = await self._client.put("/profile", json=body)
        if response.status_code != 200:
            _raise_for_status(response)
        return response.json()


# ===========================================================================
# Main client classes
# ===========================================================================


class ZinqAgent:
    """Synchronous client for the Zinq Agent SDK.

    Provides access to the user's diary, vibes, memories, profile,
    and optionally Zinq's Gemini LLM proxy.

    Usage::

        from zinq_agent import ZinqAgent

        # Reads ZINQ_API_KEY from environment
        agent = ZinqAgent()

        # Or pass explicitly
        agent = ZinqAgent(api_key="zak_xxxxx")

        # Context manager (auto-closes connections)
        with ZinqAgent() as agent:
            diary = agent.diary.list(start="2026-04-01")
            for entry in diary.entries:
                print(entry.text)

        # Configurable retries and timeout
        agent = ZinqAgent(max_retries=3, timeout=60.0)

    Args:
        api_key: Agent API key (``zak_`` prefix). Falls back to
                 ``ZINQ_API_KEY`` environment variable.
        base_url: Zinq backend URL (default: ``https://zinq-app.com/api``).
        max_retries: Number of retries on transient failures (default: 2).
        timeout: HTTP request timeout in seconds (default: 30.0).
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key = _resolve_api_key(api_key)
        self.base_url = base_url

        transport = httpx.HTTPTransport(retries=max_retries)
        self._client = httpx.Client(
            base_url=f"{base_url}/agent-api",
            headers={
                "X-Agent-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "zinq-agent-python/0.1.0",
            },
            timeout=timeout,
            transport=transport,
        )

        self.diary = DiaryClient(self._client)
        self.vibes = VibeClient(self._client)
        self.feed = FeedClient(self._client)
        self.contacts = ContactsClient(self._client)
        self.zones = ZonesClient(self._client)
        self.memories = MemoryClient(self._client)
        self.billing = BillingClient(self._client)
        self.user = UserClient(self._client)
        self.gemini = GeminiClient(self._client)

    def close(self) -> None:
        """Close the underlying HTTP client. Call when done using the agent."""
        self._client.close()

    def __enter__(self) -> ZinqAgent:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}"
        return f"ZinqAgent(api_key='{masked_key}', base_url='{self.base_url}')"


class AsyncZinqAgent:
    """Asynchronous client for the Zinq Agent SDK.

    Provides the same API as ``ZinqAgent`` but all methods are async.
    Use ``async with`` for automatic cleanup.

    Usage::

        import asyncio
        from zinq_agent import AsyncZinqAgent

        async def main():
            async with AsyncZinqAgent() as agent:
                page = await agent.diary.list(start="2026-04-01")
                for entry in page.entries:
                    print(entry.text)

                # Streaming Gemini
                async for chunk in agent.gemini.stream_chat(
                    messages=[{"role": "user", "content": "Hello!"}]
                ):
                    print(chunk, end="", flush=True)

        asyncio.run(main())

    Args:
        api_key: Agent API key (``zak_`` prefix). Falls back to
                 ``ZINQ_API_KEY`` environment variable.
        base_url: Zinq backend URL (default: ``https://zinq-app.com/api``).
        max_retries: Number of retries on transient failures (default: 2).
        timeout: HTTP request timeout in seconds (default: 30.0).
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key = _resolve_api_key(api_key)
        self.base_url = base_url

        transport = httpx.AsyncHTTPTransport(retries=max_retries)
        self._client = httpx.AsyncClient(
            base_url=f"{base_url}/agent-api",
            headers={
                "X-Agent-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "zinq-agent-python/0.1.0",
            },
            timeout=timeout,
            transport=transport,
        )

        self.diary = AsyncDiaryClient(self._client)
        self.vibes = AsyncVibeClient(self._client)
        self.memories = AsyncMemoryClient(self._client)
        self.user = AsyncUserClient(self._client)
        self.gemini = AsyncGeminiClient(self._client)

    async def close(self) -> None:
        """Close the underlying async HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> AsyncZinqAgent:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def __repr__(self) -> str:
        masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}"
        return f"AsyncZinqAgent(api_key='{masked_key}', base_url='{self.base_url}')"
