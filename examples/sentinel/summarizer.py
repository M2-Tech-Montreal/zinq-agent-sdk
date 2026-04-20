"""Gemini-powered summarization for emails and Slack messages."""

from __future__ import annotations

from datetime import datetime

from zinq_agent import ZinqAgent


def _log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] [SUMMARY] {msg}")


def summarize_emails(agent: ZinqAgent, emails: list[dict]) -> str:
    """Summarize a batch of emails into a digest vibe."""
    if not emails:
        return ""

    email_text = "\n".join(
        f"- From: {e['sender']} | Subject: {e['subject']} | Preview: {e['snippet'][:100]}"
        for e in emails
    )

    try:
        resp = agent.gemini.chat(
            messages=[{
                "role": "user",
                "content": (
                    "Summarize these emails into a brief digest. "
                    "Group by urgency (urgent first). For each email, "
                    "give sender name + one sentence summary. Be concise.\n\n"
                    f"{email_text}"
                ),
            }],
            model="flash",
            max_tokens=500,
        )
        return resp.text
    except Exception as e:
        _log(f"Gemini summarization failed: {e}")
        # Fallback: plain list
        lines = [f"{e['sender']}: {e['subject']}" for e in emails[:10]]
        return "\n".join(lines)


def summarize_slack(agent: ZinqAgent, dms: list[dict], mentions: list[dict]) -> str:
    """Summarize Slack activity into an hourly vibe."""
    if not dms and not mentions:
        return ""

    parts = []
    if dms:
        dm_text = "\n".join(f"- {d['user']}: {d['text'][:100]}" for d in dms)
        parts.append(f"DMs:\n{dm_text}")
    if mentions:
        mention_text = "\n".join(f"- #{m['channel']} by {m['user']}: {m['text'][:100]}" for m in mentions)
        parts.append(f"Mentions:\n{mention_text}")

    activity = "\n\n".join(parts)

    try:
        resp = agent.gemini.chat(
            messages=[{
                "role": "user",
                "content": (
                    "Summarize this Slack activity into a brief update. "
                    "Lead with the most important items. Be concise.\n\n"
                    f"{activity}"
                ),
            }],
            model="flash",
            max_tokens=300,
        )
        return resp.text
    except Exception as e:
        _log(f"Gemini summarization failed: {e}")
        return activity


def format_urgent_email(email: dict) -> str:
    """Format a single urgent email for immediate vibe."""
    sender = email.get("sender", "Unknown")
    subject = email.get("subject", "(no subject)")
    snippet = email.get("snippet", "")[:150]
    account = email.get("account", "")
    return f"URGENT EMAIL ({account})\nFrom: {sender}\nSubject: {subject}\n{snippet}"


def format_urgent_dm(dm: dict) -> str:
    """Format an urgent Slack DM for immediate vibe."""
    user = dm.get("user", "Unknown")
    text = dm.get("text", "")[:200]
    return f"URGENT SLACK DM\nFrom: {user}\n{text}"
