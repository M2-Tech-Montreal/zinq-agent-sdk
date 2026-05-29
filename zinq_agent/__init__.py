"""Zinq Agent Python SDK.

Build personal AI agents that connect to the Zinq platform.

Usage::

    from zinq_agent import ZinqAgent

    agent = ZinqAgent(api_key="zak_xxxxx")

    # Read the user's diary
    diary = agent.diary.list(start="2026-04-01")

    # Send a vibe
    agent.vibes.send(text="Hey! Time for your afternoon stretch.")

    # Use Gemini (optional, charged to user's credits)
    response = agent.gemini.chat(
        messages=[{"role": "user", "content": "What should I eat?"}]
    )
    print(response.text)

For webhook support::

    from zinq_agent import ZinqAgent, ZinqWebhook

    agent = ZinqAgent(api_key="zak_xxxxx")
    webhook = ZinqWebhook(secret="dev", skip_signature_check=True)

    @webhook.on("vibe.received")
    def handle_vibe(event):
        text = event.data.transcript or event.data.text
        agent.vibes.send(text=f"You said: {text}")

    webhook.start(port=8080)
"""

from .client import AsyncZinqAgent, ZinqAgent
from .marketplace import ZinqMarketplaceAdmin
from .exceptions import (
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
    ZinqError,
)
from .models import (
    AgentPreferences,
    AgentWaveData,
    CharmReceivedData,
    Contact,
    CreditStatus,
    DiaryEntry,
    DiaryPage,
    EmbeddingResponse,
    GeminiResponse,
    GeminiUsage,
    Memory,
    MemorySaveResult,
    NotificationHours,
    SearchResult,
    SearchResults,
    UserContext,
    Vibe,
    VibeSendResult,
    VibeReceivedData,
    VibeReplyData,
    WebhookAgent,
    WebhookEvent,
    WebhookUser,
    Zone,
)
from .webhook import ZinqBusinessWebhook, ZinqWebhook

__version__ = "0.1.0"

__all__ = [
    # Main classes
    "ZinqAgent",
    "AsyncZinqAgent",
    "ZinqBusinessWebhook",
    "ZinqMarketplaceAdmin",
    "ZinqWebhook",
    # Models
    "AgentPreferences",
    "AgentWaveData",
    "CharmReceivedData",
    "CreditStatus",
    "DiaryEntry",
    "DiaryPage",
    "EmbeddingResponse",
    "GeminiResponse",
    "GeminiUsage",
    "Memory",
    "MemorySaveResult",
    "NotificationHours",
    "SearchResult",
    "SearchResults",
    "Contact",
    "UserContext",
    "Vibe",
    "Zone",
    "VibeSendResult",
    "VibeReceivedData",
    "VibeReplyData",
    "WebhookAgent",
    "WebhookEvent",
    "WebhookUser",
    # Exceptions
    "AuthenticationError",
    "InsufficientCreditsError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    "ValidationError",
    "ZinqError",
    # Version
    "__version__",
]
