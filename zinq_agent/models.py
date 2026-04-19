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

    model_config = ConfigDict(populate_by_name=True)

    id: int
    text: str | None = None
    transcript: str | None = None
    media_type: str | None = Field(default=None, alias="mediaType")
    media_url: str | None = Field(default=None, alias="mediaUrl")
    ai_tags: list[str] = Field(default_factory=list, alias="aiTags")
    created_at: datetime = Field(alias="createdAt")


class DiaryPage(BaseModel):
    """Paginated diary entries."""

    model_config = ConfigDict(populate_by_name=True)

    entries: list[DiaryEntry]
    page: int
    total_pages: int = Field(alias="totalPages")
    total_entries: int = Field(alias="totalEntries")


class SearchResult(BaseModel):
    """A single semantic search result from the diary."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    text: str | None = None
    ai_tags: list[str] = Field(default_factory=list, alias="aiTags")
    similarity: float
    created_at: datetime = Field(alias="createdAt")


class SearchResults(BaseModel):
    """Results from a diary semantic search."""

    model_config = ConfigDict(populate_by_name=True)

    results: list[SearchResult]
    query: str
    embedding_credits_used: int = Field(alias="embeddingCreditsUsed")


# ---------------------------------------------------------------------------
# Vibes
# ---------------------------------------------------------------------------


class Vibe(BaseModel):
    """A vibe sent to the agent by the user."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    type: str
    text: str | None = None
    transcript: str | None = None
    media_url: str | None = Field(default=None, alias="mediaUrl")
    charm_emoji: str | None = Field(default=None, alias="charmEmoji")
    reply_to_vibe_id: int | None = Field(default=None, alias="replyToVibeId")
    created_at: datetime = Field(alias="createdAt")


class VibeSendResult(BaseModel):
    """Result of sending a vibe to the user."""

    model_config = ConfigDict(populate_by_name=True)

    vibe_id: int = Field(alias="vibeId")
    delivered_at: datetime = Field(alias="deliveredAt")
    push_sent: bool = Field(alias="pushSent")


# ---------------------------------------------------------------------------
# Memories
# ---------------------------------------------------------------------------


class Memory(BaseModel):
    """A persistent key-value memory scoped to this agent and user."""

    model_config = ConfigDict(populate_by_name=True)

    key: str
    value: str
    category: str | None = None
    updated_at: datetime = Field(alias="updatedAt")


class MemorySaveResult(BaseModel):
    """Result of saving or updating a memory."""

    model_config = ConfigDict(populate_by_name=True)

    key: str
    created: bool
    updated_at: datetime = Field(alias="updatedAt")


# ---------------------------------------------------------------------------
# User Context
# ---------------------------------------------------------------------------


class NotificationHours(BaseModel):
    """Preferred notification hours (inclusive)."""

    start: int
    end: int


class AgentPreferences(BaseModel):
    """User's agent interaction preferences."""

    model_config = ConfigDict(populate_by_name=True)

    notification_hours: NotificationHours | None = Field(
        default=None, alias="notificationHours"
    )
    preferred_response_length: str | None = Field(
        default=None, alias="preferredResponseLength"
    )


class CreditStatus(BaseModel):
    """User's current credit balance and tier."""

    model_config = ConfigDict(populate_by_name=True)

    credits_remaining: int = Field(alias="creditsRemaining")
    monthly_limit: int = Field(alias="monthlyLimit")
    tier: str
    reset_date: datetime = Field(alias="resetDate")


class UserContext(BaseModel):
    """User profile and preferences relevant to agent operation."""

    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(alias="userId")
    name: str
    nickname: str | None = None
    timezone: str
    locale: str | None = None
    country_code: str | None = Field(default=None, alias="countryCode")
    agent_preferences: AgentPreferences | None = Field(
        default=None, alias="agentPreferences"
    )
    credit_status: CreditStatus = Field(alias="creditStatus")


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


class GeminiUsage(BaseModel):
    """Token usage and credit cost for a Gemini call."""

    model_config = ConfigDict(populate_by_name=True)

    prompt_tokens: int = Field(alias="promptTokens")
    completion_tokens: int = Field(alias="completionTokens")
    total_tokens: int = Field(alias="totalTokens")
    credits_used: int = Field(alias="creditsUsed")


class GeminiResponse(BaseModel):
    """Response from the Gemini proxy."""

    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(alias="content")
    tool_calls: list[dict] = Field(default_factory=list, alias="toolCalls")
    usage: GeminiUsage
    model: str


class EmbeddingResponse(BaseModel):
    """Response from the embedding endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    embedding: list[float]
    dimensions: int
    credits_used: int = Field(alias="creditsUsed")


# ---------------------------------------------------------------------------
# Webhook Events
# ---------------------------------------------------------------------------


class WebhookAgent(BaseModel):
    """Agent identity in a webhook payload."""

    id: int
    name: str


class WebhookUser(BaseModel):
    """User identity in a webhook payload."""

    id: int
    name: str
    timezone: str | None = None


class VibeReceivedData(BaseModel):
    """Data payload for a vibe.received webhook event."""

    model_config = ConfigDict(populate_by_name=True)

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

    model_config = ConfigDict(populate_by_name=True)

    charm_id: int = Field(alias="charmId")
    emoji: str
    vibe_id: int = Field(alias="vibeId")
    created_at: datetime = Field(alias="createdAt")


class AgentWaveData(BaseModel):
    """Data payload for an agent.wave webhook event."""

    model_config = ConfigDict(populate_by_name=True)

    is_first_wave: bool = Field(alias="isFirstWave")
    last_interaction_at: datetime | None = Field(default=None, alias="lastInteractionAt")


class VibeReplyData(BaseModel):
    """Data payload for a vibe.reply webhook event."""

    model_config = ConfigDict(populate_by_name=True)

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

    model_config = ConfigDict(populate_by_name=True)

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
