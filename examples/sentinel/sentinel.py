#!/usr/bin/env python3
"""Sentinel — personal monitoring agent for Gmail + Slack.

Watches your email and Slack, sends you vibes on Zinq with
summaries and urgent alerts. Listens for commands via webhook.

Usage:
    export ZINQ_API_KEY=zak_your_key
    export GMAIL_ACCOUNTS=you@gmail.com,work@company.com
    export SLACK_BOT_TOKEN=xoxb-your-token
    python sentinel.py

Optional env vars:
    VIP_SENDERS=boss@company.com,ceo@company.com
    GMAIL_POLL_INTERVAL=300  (seconds, default 5 min)
    SLACK_POLL_INTERVAL=600  (seconds, default 10 min)
"""

from __future__ import annotations

import json
import sys
import time
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

from apscheduler.schedulers.background import BackgroundScheduler

from zinq_agent import ZinqAgent

import config
from gmail_monitor import fetch_unread, classify_urgency
from slack_monitor import fetch_dms, fetch_mentions, is_urgent_dm
from summarizer import (
    summarize_emails,
    summarize_slack,
    format_urgent_email,
    format_urgent_dm,
)


def _log(tag: str, msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] [{tag}] {msg}", flush=True)


agent = ZinqAgent()

WEBHOOK_PORT = 8080


# ── Command handler ──────────────────────────────────────────────────────

def handle_command(text: str) -> str:
    """Handle a command from the user via vibe. Returns response text."""
    text = text.strip().lower()

    if text in ("last emails", "recent emails", "last 10 emails", "emails"):
        return _cmd_recent_emails(10)

    if text in ("last slack", "recent slack", "last 10 slack", "slack", "slack messages"):
        return _cmd_recent_slack(10)

    if text in ("status", "ping"):
        return _cmd_status()

    if text.startswith("send slack ") or text.startswith("slack send "):
        # "send slack #channel message" or "send slack @user message"
        return _cmd_send_slack(text)

    if text in ("digest", "email digest"):
        email_digest()
        return "Digest sent."

    if text in ("check", "check now"):
        check_gmail()
        check_slack()
        return "Checked Gmail and Slack."

    return (
        "Commands:\n"
        "• last emails — recent 10 emails\n"
        "• last slack — recent 10 Slack messages\n"
        "• send slack #channel message\n"
        "• send slack @user message\n"
        "• digest — send email digest now\n"
        "• check — check Gmail + Slack now\n"
        "• status — show agent status"
    )


def _cmd_recent_emails(count: int) -> str:
    all_emails = []
    for account in config.GMAIL_ACCOUNTS:
        emails = fetch_unread(account)
        all_emails.extend(emails[:count])

    if not all_emails:
        return "No unread emails."

    lines = []
    for e in all_emails[:count]:
        lines.append(f"• {e['sender']}: {e['subject']}")
    return f"{len(lines)} recent emails:\n" + "\n".join(lines)


def _cmd_recent_slack(count: int) -> str:
    if not config.SLACK_BOT_TOKEN:
        return "Slack not configured."

    dms = fetch_dms()
    if not dms:
        return "No recent Slack messages."

    lines = []
    for d in dms[:count]:
        lines.append(f"• {d['user']}: {d['text'][:80]}")
    return f"{len(lines)} recent Slack messages:\n" + "\n".join(lines)


def _cmd_status() -> str:
    parts = [
        "Sentinel status: ONLINE",
        f"Gmail accounts: {', '.join(config.GMAIL_ACCOUNTS) or 'none'}",
        f"Slack: {'connected' if config.SLACK_BOT_TOKEN else 'disabled'}",
    ]
    return "\n".join(parts)


def _cmd_send_slack(text: str) -> str:
    """Parse 'send slack #channel message' or 'send slack @user message'."""
    if not config.SLACK_BOT_TOKEN:
        return "Slack not configured."

    # Remove the "send slack " or "slack send " prefix
    for prefix in ("send slack ", "slack send "):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break

    parts = text.split(" ", 1)
    if len(parts) < 2:
        return "Usage: send slack #channel message"

    target = parts[0]
    message = parts[1]

    try:
        from slack_sdk import WebClient
        client = WebClient(token=config.SLACK_BOT_TOKEN)

        if target.startswith("#"):
            # Channel message
            channel = target[1:]
            client.chat_postMessage(channel=channel, text=message)
            return f"Sent to #{channel}"
        elif target.startswith("@"):
            # DM — need to open a conversation first
            username = target[1:]
            # Find user by name
            users = client.users_list()
            user_id = None
            for u in users["members"]:
                if u.get("name") == username or u.get("real_name", "").lower() == username.lower():
                    user_id = u["id"]
                    break
            if not user_id:
                return f"User {target} not found"
            conv = client.conversations_open(users=[user_id])
            client.chat_postMessage(channel=conv["channel"]["id"], text=message)
            return f"DM sent to {target}"
        else:
            return f"Target must start with # or @. Got: {target}"

    except Exception as e:
        return f"Slack send failed: {e}"


# ── Webhook server ───────────────────────────────────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
            event_type = data.get("event", "")
            _log("WEBHOOK", f"Received event: {event_type}")

            if event_type == "vibe.received":
                # User sent a message to the agent
                text = data.get("data", {}).get("transcript") or data.get("data", {}).get("text") or ""
                _log("WEBHOOK", f"Command: {text}")

                if text.strip():
                    response_text = handle_command(text)
                    agent.vibes.send(text=response_text)
                    _log("WEBHOOK", f"Responded: {response_text[:60]}")

            elif event_type == "agent.wave":
                # User opened the agent chat
                agent.vibes.send(text="Sentinel here. Type 'help' for commands.")

        except Exception as e:
            _log("WEBHOOK", f"Error: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, format, *args):
        pass  # Suppress default HTTP logs


def start_webhook_server():
    server = HTTPServer(("0.0.0.0", WEBHOOK_PORT), WebhookHandler)
    _log("WEBHOOK", f"Listening on port {WEBHOOK_PORT}")
    server.serve_forever()


# ── Gmail check (every 5 minutes) ────────────────────────────────────────

def check_gmail():
    """Poll Gmail for unread emails, send urgent ones immediately."""
    _log("GMAIL", f"Checking {len(config.GMAIL_ACCOUNTS)} accounts...")

    for account in config.GMAIL_ACCOUNTS:
        try:
            last_check = None
            try:
                mem = agent.memories.get(f"last_gmail_check_{account}")
                if mem:
                    last_check = mem.value
            except Exception:
                pass

            emails = fetch_unread(account, since=last_check)
            if not emails:
                _log("GMAIL", f"{account}: no new emails")
                continue

            urgent = []
            batch = []
            for email in emails:
                urgency = classify_urgency(email)
                email["urgency"] = urgency
                if urgency == "high":
                    urgent.append(email)
                else:
                    batch.append(email)

            for email in urgent:
                vibe_text = format_urgent_email(email)
                agent.vibes.send(text=vibe_text)
                _log("GMAIL", f"Sent urgent vibe: {email['subject'][:50]}")

            if batch:
                _log("GMAIL", f"{account}: {len(batch)} emails batched for digest")

            now = datetime.now(timezone.utc).isoformat()
            agent.memories.save(f"last_gmail_check_{account}", now)

        except Exception as e:
            _log("GMAIL", f"Error checking {account}: {e}")


# ── Slack check (every 10 minutes) ───────────────────────────────────────

def check_slack():
    if not config.SLACK_BOT_TOKEN:
        return

    _log("SLACK", "Checking DMs and mentions...")

    try:
        last_check = None
        try:
            mem = agent.memories.get("last_slack_check")
            if mem:
                last_check = mem.value
        except Exception:
            pass

        dms = fetch_dms(since=last_check)
        mentions = fetch_mentions(since=last_check)

        for dm in dms:
            if is_urgent_dm(dm):
                vibe_text = format_urgent_dm(dm)
                agent.vibes.send(text=vibe_text)
                _log("SLACK", f"Sent urgent DM vibe from {dm['user']}")

        _log("SLACK", f"{len(dms)} DMs, {len(mentions)} mentions")

        now = str(time.time())
        agent.memories.save("last_slack_check", now)

    except Exception as e:
        _log("SLACK", f"Error: {e}")


# ── Hourly Slack summary ─────────────────────────────────────────────────

def slack_summary():
    if not config.SLACK_BOT_TOKEN:
        return

    _log("SLACK", "Building hourly summary...")

    try:
        one_hour_ago = str(time.time() - 3600)
        dms = fetch_dms(since=one_hour_ago)
        mentions = fetch_mentions(since=one_hour_ago)

        if not dms and not mentions:
            _log("SLACK", "No activity in the last hour, skipping summary")
            return

        summary = summarize_slack(agent, dms, mentions)
        if summary:
            agent.vibes.send(text=f"Slack summary (last hour):\n\n{summary}")
            _log("SLACK", "Sent hourly summary vibe")

    except Exception as e:
        _log("SLACK", f"Summary error: {e}")


# ── Daily email digest (8am) ─────────────────────────────────────────────

def email_digest():
    _log("DIGEST", "Building daily email digest...")

    try:
        try:
            mem = agent.memories.get("last_email_digest")
            if mem and mem.value == datetime.now().strftime("%Y-%m-%d"):
                _log("DIGEST", "Already sent today's digest, skipping")
                return
        except Exception:
            pass

        all_emails = []
        for account in config.GMAIL_ACCOUNTS:
            yesterday = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0
            ).isoformat()
            emails = fetch_unread(account, since=yesterday)
            for e in emails:
                e["urgency"] = classify_urgency(e)
            all_emails.extend(emails)

        if not all_emails:
            _log("DIGEST", "No emails for digest")
            return

        summary = summarize_emails(agent, all_emails)
        count = len(all_emails)
        urgent_count = sum(1 for e in all_emails if e.get("urgency") == "high")

        vibe_text = (
            f"Daily Email Digest — {count} emails"
            f"{f' ({urgent_count} urgent)' if urgent_count else ''}\n\n"
            f"{summary}"
        )
        agent.vibes.send(text=vibe_text)
        _log("DIGEST", f"Sent digest with {count} emails")

        agent.memories.save("last_email_digest", datetime.now().strftime("%Y-%m-%d"))

    except Exception as e:
        _log("DIGEST", f"Error: {e}")


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    _log("SENTINEL", "Starting Sentinel agent")
    _log("SENTINEL", f"Gmail accounts: {config.GMAIL_ACCOUNTS or '(none)'}")
    _log("SENTINEL", f"Slack: {'enabled' if config.SLACK_BOT_TOKEN else 'disabled'}")
    _log("SENTINEL", f"Webhook: port {WEBHOOK_PORT}")

    if not config.ZINQ_API_KEY:
        _log("SENTINEL", "ERROR: ZINQ_API_KEY not set")
        sys.exit(1)

    if not config.GMAIL_ACCOUNTS and not config.SLACK_BOT_TOKEN:
        _log("SENTINEL", "ERROR: No GMAIL_ACCOUNTS or SLACK_BOT_TOKEN set")
        sys.exit(1)

    # Register webhook URL with the agent
    webhook_url = f"http://34.58.243.153:{WEBHOOK_PORT}/webhook"
    try:
        import httpx
        r = httpx.put(
            f"https://zinq-app.com/api/agent-api/profile",
            headers={"X-Agent-Key": config.ZINQ_API_KEY},
            json={"webhookUrl": webhook_url},
        )
        _log("SENTINEL", f"Webhook registered: {webhook_url}")
    except Exception as e:
        _log("SENTINEL", f"Failed to register webhook (non-fatal): {e}")

    # Send startup vibe
    agent.vibes.send(text=(
        "Sentinel is online.\n\n"
        "Commands: last emails, last slack, send slack #channel msg, "
        "digest, check, status"
    ))

    # Start webhook server in background thread
    webhook_thread = threading.Thread(target=start_webhook_server, daemon=True)
    webhook_thread.start()

    # Set up scheduler
    scheduler = BackgroundScheduler()

    if config.GMAIL_ACCOUNTS:
        scheduler.add_job(check_gmail, "interval", seconds=config.GMAIL_POLL_INTERVAL,
                          id="gmail_check", next_run_time=datetime.now())
        scheduler.add_job(email_digest, "cron", hour=config.DIGEST_HOUR,
                          id="email_digest")

    if config.SLACK_BOT_TOKEN:
        scheduler.add_job(check_slack, "interval", seconds=config.SLACK_POLL_INTERVAL,
                          id="slack_check", next_run_time=datetime.now())
        scheduler.add_job(slack_summary, "cron", minute=0,
                          id="slack_summary")

    scheduler.start()
    _log("SENTINEL", "Scheduler started. Press Ctrl+C to stop.")

    try:
        # Keep main thread alive
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        _log("SENTINEL", "Shutting down.")
        scheduler.shutdown()
        agent.vibes.send(text="Sentinel going offline.")
        agent.close()


if __name__ == "__main__":
    main()
