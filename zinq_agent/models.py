"""Pydantic models for all Zinq Agent API objects.

Every API response is parsed into a typed model. Field names use snake_case
(Python convention) and are mapped from the API's camelCase via aliases.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Diary
# ---------------------------------------------------------------------------


class DiaryEntry(BaseModel):
    """A single diary vibe entry."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    text: str | None = Field(default=None, alias="textContent")
    transcript: str | None = None
    media_type: str | None = Field(default=None, alias="mediaType")
    media_url: str | None = Field(default=None, alias="mediaUrl")
    media_description: str | None = Field(default=None, alias="mediaDescription")
    vibe_type: str | None = Field(default=None, alias="vibeType")
    location_name: str | None = Field(default=None, alias="locationName")
    city: str | None = None
    ai_tags: list[str] = Field(default_factory=list, alias="aiTags")
    created_at: datetime = Field(alias="createdAt")


class DiaryPage(BaseModel):
    """Paginated diary entries."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    entries: list[DiaryEntry] = Field(default_factory=list, alias="vibes")
    page: int
    total_pages: int = Field(default=0, alias="totalPages")
    total_entries: int = Field(default=0, alias="total")


class SearchResult(BaseModel):
    """A single semantic search result from the diary."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    text: str | None = Field(default=None, alias="textContent")
    ai_tags: list[str] = Field(default_factory=list, alias="aiTags")
    similarity: float = 0.0
    created_at: datetime | None = Field(default=None, alias="createdAt")


class SearchResults(BaseModel):
    """Results from a diary semantic search."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    results: list[SearchResult] = Field(default_factory=list, alias="vibes")
    query: str
    total: int = 0
    embedding_credits_used: int = Field(default=0, alias="embeddingCreditsUsed")


# ---------------------------------------------------------------------------
# Vibes
# ---------------------------------------------------------------------------


class Vibe(BaseModel):
    """A vibe sent to the agent by the user."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    type: str | None = Field(default=None, alias="vibeType")
    text: str | None = Field(default=None, alias="textContent")
    transcript: str | None = None
    media_url: str | None = Field(default=None, alias="mediaUrl")
    media_description: str | None = Field(default=None, alias="mediaDescription")
    charm_emoji: str | None = Field(default=None, alias="charmEmoji")
    reply_to_vibe_id: int | None = Field(default=None, alias="replyToVibeId")
    location_name: str | None = Field(default=None, alias="locationName")
    city: str | None = None
    created_at: datetime = Field(alias="createdAt")


class VibeSendResult(BaseModel):
    """Result of sending a vibe to the user."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    vibe_id: int = Field(alias="vibeId")
    success: bool = True
    delivered_at: datetime | None = Field(default=None, alias="deliveredAt")
    push_sent: bool | None = Field(default=None, alias="pushSent")


# ---------------------------------------------------------------------------
# Memories
# ---------------------------------------------------------------------------


class Memory(BaseModel):
    """A persistent key-value memory scoped to this agent and user."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    key: str
    value: str
    category: str | None = None
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class MemorySaveResult(BaseModel):
    """Result of saving or updating a memory."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    key: str
    created: bool | None = Field(default=None)
    saved: bool | None = Field(default=None)
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


# ---------------------------------------------------------------------------
# User Context
# ---------------------------------------------------------------------------


class NotificationHours(BaseModel):
    """Preferred notification hours (inclusive)."""

    model_config = ConfigDict(extra="ignore")

    start: int
    end: int


class AgentPreferences(BaseModel):
    """User's agent interaction preferences."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    notification_hours: NotificationHours | None = Field(
        default=None, alias="notificationHours"
    )
    preferred_response_length: str | None = Field(
        default=None, alias="preferredResponseLength"
    )


class CreditStatus(BaseModel):
    """User's current credit balance and tier."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    credits_remaining: int = Field(default=0, alias="creditsRemaining")
    monthly_limit: int = Field(default=0, alias="monthlyLimit")
    tier: str = "free"
    reset_date: datetime | None = Field(default=None, alias="resetDate")


class UserContext(BaseModel):
    """User profile and preferences relevant to agent operation."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    user_id: int = Field(alias="userId")
    name: str
    nickname: str | None = None
    timezone: str
    locale: str | None = None
    primary_language: str | None = Field(default=None, alias="primaryLanguage")
    country_code: str | None = Field(default=None, alias="countryCode")
    agent_preferences: AgentPreferences | None = Field(
        default=None, alias="agentPreferences"
    )
    preferences: dict | None = None
    credit_status: CreditStatus | None = Field(default=None, alias="creditStatus")


# ---------------------------------------------------------------------------
# Contacts / Connections
# ---------------------------------------------------------------------------


class Contact(BaseModel):
    """A user's connection (friend, colleague, club member)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int = Field(default=0, alias="userId")
    name: str
    nickname: str | None = None
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    zone_name: str | None = Field(default=None, alias="zoneName")
    zone_type: str | None = Field(default=None, alias="zoneType")
    connection_type: str | None = Field(default=None, alias="connectionType")
    last_active: datetime | None = Field(default=None, alias="lastActive")
    last_seen_at: datetime | None = Field(default=None, alias="lastSeenAt")
    presence_status: str | None = Field(default=None, alias="presenceStatus")
    is_online: bool | None = Field(default=None, alias="isOnline")
    is_system: bool = Field(default=False, alias="isSystem")
    is_agent: bool = Field(default=False, alias="isAgent")


class Zone(BaseModel):
    """A user's zone (life zone or club)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    name: str | None = Field(default=None, alias="customName")
    zone_type: str = Field(alias="zoneType")
    display_name: str | None = Field(default=None, alias="displayName")
    member_count: int = Field(default=0, alias="memberCount")
    is_owner: bool = Field(default=False, alias="isOwner")
    is_primary: bool = Field(default=False, alias="isPrimary")
    description: str | None = None
    bio: str | None = None
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    photo_url: str | None = Field(default=None, alias="photoUrl")
    sort_order: int | None = Field(default=None, alias="sortOrder")


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


class GeminiUsage(BaseModel):
    """Token usage and credit cost for a Gemini call."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    prompt_tokens: int = Field(default=0, alias="promptTokens")
    completion_tokens: int = Field(default=0, alias="completionTokens")
    total_tokens: int = Field(default=0, alias="totalTokens")
    credits_used: int = Field(default=0, alias="creditsUsed")


class GeminiResponse(BaseModel):
    """Response from the Gemini proxy."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    text: str = Field(default="", alias="content")
    tool_calls: list[dict] = Field(default_factory=list, alias="toolCalls")
    usage: GeminiUsage | None = None
    model: str = ""


class EmbeddingResponse(BaseModel):
    """Response from the embedding endpoint."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    embedding: list[float]
    dimensions: int = 0
    credits_used: int = Field(default=0, alias="creditsUsed")


# ---------------------------------------------------------------------------
# Webhook Events
# ---------------------------------------------------------------------------


class WebhookAgent(BaseModel):
    """Agent identity in a webhook payload."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str


class WebhookUser(BaseModel):
    """User identity in a webhook payload."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    timezone: str | None = None


class VibeReceivedData(BaseModel):
    """Data payload for a vibe.received webhook event."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    vibe_id: int = Field(alias="vibeId")
    type: str
    text: str | None = None
    transcript: str | None = None
    media_url: str | None = Field(default=None, alias="mediaUrl")
    media_type: str | None = Field(default=None, alias="mediaType")
    duration: int | None = None
    created_at: datetime = Field(alias="createdAt")


class CharmReceivedData(BaseModel):
    """Data payload for a charm.received webhook event."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    charm_id: int = Field(alias="charmId")
    emoji: str
    vibe_id: int = Field(alias="vibeId")
    created_at: datetime = Field(alias="createdAt")


class AgentWaveData(BaseModel):
    """Data payload for an agent.wave webhook event."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    is_first_wave: bool = Field(alias="isFirstWave")
    last_interaction_at: datetime | None = Field(default=None, alias="lastInteractionAt")


class VibeReplyData(BaseModel):
    """Data payload for a vibe.reply webhook event."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    vibe_id: int = Field(alias="vibeId")
    type: str
    text: str | None = None
    reply_to_vibe_id: int | None = Field(default=None, alias="replyToVibeId")
    button_value: str | None = Field(default=None, alias="buttonValue")
    created_at: datetime = Field(alias="createdAt")


class WebhookEvent(BaseModel):
    """A parsed webhook event from Zinq.

    The ``data`` field is a typed model depending on the event type:
    - ``vibe.received`` -> VibeReceivedData
    - ``charm.received`` -> CharmReceivedData
    - ``agent.wave`` -> AgentWaveData
    - ``vibe.reply`` -> VibeReplyData
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event: str
    delivery_id: str = Field(alias="deliveryId")
    timestamp: datetime
    agent: WebhookAgent
    user: WebhookUser
    data: VibeReceivedData | CharmReceivedData | AgentWaveData | VibeReplyData


# Maps event type strings to their data model class
EVENT_DATA_MODELS: dict[str, type] = {
    "vibe.received": VibeReceivedData,
    "charm.received": CharmReceivedData,
    "agent.wave": AgentWaveData,
    "vibe.reply": VibeReplyData,
}
