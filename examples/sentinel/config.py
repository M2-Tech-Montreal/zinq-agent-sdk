"""Sentinel configuration."""

import os

# Zinq
ZINQ_API_KEY = os.environ.get("ZINQ_API_KEY", "")

# Gmail accounts to monitor
GMAIL_ACCOUNTS = [
    a.strip() for a in os.environ.get("GMAIL_ACCOUNTS", "").split(",") if a.strip()
]

# Slack
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

# Poll intervals (seconds)
GMAIL_POLL_INTERVAL = 300       # 5 minutes
SLACK_POLL_INTERVAL = 600       # 10 minutes
SLACK_SUMMARY_INTERVAL = 3600   # 1 hour
DIGEST_HOUR = 8                 # 8am local time

# Urgency keywords — emails/DMs containing these trigger immediate vibes
URGENT_KEYWORDS = [
    "urgent", "asap", "emergency", "critical", "important",
    "deadline", "action required", "immediately", "time sensitive",
]

# VIP senders — always treated as urgent
VIP_SENDERS = [
    a.strip() for a in os.environ.get("VIP_SENDERS", "").split(",") if a.strip()
]
