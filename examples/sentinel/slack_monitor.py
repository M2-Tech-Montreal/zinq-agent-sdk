"""Slack monitoring — DMs, mentions, channel activity."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import SLACK_BOT_TOKEN, URGENT_KEYWORDS, VIP_SENDERS


def _log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] [SLACK] {msg}")


def get_slack_client() -> WebClient | None:
    if not SLACK_BOT_TOKEN:
        _log("No SLACK_BOT_TOKEN set, skipping Slack")
        return None
    return WebClient(token=SLACK_BOT_TOKEN)


def fetch_dms(since: str | None = None) -> list[dict[str, Any]]:
    """Fetch unread DMs since the given timestamp."""
    client = get_slack_client()
    if not client:
        return []

    oldest = since or "0"
    dms = []

    try:
        # List DM channels
        convos = client.conversations_list(types="im", limit=50)
        for ch in convos.get("channels", []):
            if not ch.get("is_im"):
                continue

            history = client.conversations_history(
                channel=ch["id"], oldest=oldest, limit=20
            )
            for msg in history.get("messages", []):
                # Skip bot's own messages
                if msg.get("bot_id") or msg.get("subtype") == "bot_message":
                    continue

                user_id = msg.get("user", "unknown")
                user_name = _resolve_user(client, user_id)

                dms.append({
                    "channel": ch["id"],
                    "user": user_name,
                    "user_id": user_id,
                    "text": msg.get("text", ""),
                    "ts": msg.get("ts", ""),
                })

    except SlackApiError as e:
        _log(f"Error fetching DMs: {e.response['error']}")

    _log(f"{len(dms)} new DMs")
    return dms


def fetch_mentions(since: str | None = None) -> list[dict[str, Any]]:
    """Fetch @mentions of the bot since the given timestamp."""
    client = get_slack_client()
    if not client:
        return []

    mentions = []
    try:
        # Get bot user ID
        auth = client.auth_test()
        bot_user_id = auth["user_id"]

        # Search for mentions
        result = client.search_messages(query=f"<@{bot_user_id}>", count=20)
        for match in result.get("messages", {}).get("matches", []):
            ts = match.get("ts", "0")
            if since and float(ts) <= float(since):
                continue

            mentions.append({
                "channel": match.get("channel", {}).get("name", "unknown"),
                "user": match.get("username", "unknown"),
                "text": match.get("text", ""),
                "ts": ts,
            })

    except SlackApiError as e:
        _log(f"Error fetching mentions: {e.response['error']}")

    _log(f"{len(mentions)} new mentions")
    return mentions


def is_urgent_dm(dm: dict[str, Any]) -> bool:
    """Check if a DM is urgent (VIP sender or urgent keywords)."""
    text = dm.get("text", "").lower()
    user = dm.get("user", "").lower()

    for vip in VIP_SENDERS:
        if vip.lower() in user:
            return True

    for kw in URGENT_KEYWORDS:
        if kw in text:
            return True

    return False


_user_cache: dict[str, str] = {}


def _resolve_user(client: WebClient, user_id: str) -> str:
    """Resolve Slack user ID to display name."""
    if user_id in _user_cache:
        return _user_cache[user_id]

    try:
        info = client.users_info(user=user_id)
        name = (
            info["user"].get("real_name")
            or info["user"].get("name")
            or user_id
        )
        _user_cache[user_id] = name
        return name
    except SlackApiError:
        return user_id
