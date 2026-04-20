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
from gmail_monitor import fetch_unread, classify_urgency, search_emails
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

# Conversation history — last 10 messages for context
_conversation: list[dict[str, str]] = []
MAX_HISTORY = 10


# ── Conversation handler ──────────────────────────────────────────────────

def handle_message(text: str) -> str:
    """Handle a natural language message from the user via Gemini."""

    # Gather context for Gemini
    context_parts = []

    # Check if user is asking about a specific person/topic — search for it
    search_results = []
    text_lower = text.lower()
    # Extract potential search terms (names, subjects) using simple heuristics
    search_triggers = ["from ", "email from ", "message from ", "about ", "regarding "]
    search_query = None
    for trigger in search_triggers:
        if trigger in text_lower:
            search_query = text[text_lower.index(trigger) + len(trigger):].strip().rstrip("?.")
            break

    if search_query:
        for account in config.GMAIL_ACCOUNTS:
            try:
                results = search_emails(account, f"from:{search_query} OR subject:{search_query}", max_results=5)
                search_results.extend(results)
            except Exception:
                pass

        if search_results:
            search_lines = []
            for e in search_results[:5]:
                body_preview = e.get('body', e.get('snippet', ''))[:500]
                search_lines.append(
                    f"- FROM: {e['sender']}\n  SUBJECT: {e['subject']}\n  DATE: {e['date']}\n  BODY: {body_preview}\n"
                )
            context_parts.append(f"SEARCH RESULTS FOR '{search_query}' ({len(search_results)} found):\n" + "\n".join(search_lines))

    # Recent unread emails
    all_emails = []
    for account in config.GMAIL_ACCOUNTS:
        try:
            emails = fetch_unread(account)
            all_emails.extend(emails[:10])
        except Exception:
            pass

    if all_emails:
        email_lines = "\n".join(
            f"- {e['sender']}: {e['subject']} | {e.get('snippet', '')[:150]} ({e['account']})" for e in all_emails[:15]
        )
        context_parts.append(f"RECENT UNREAD EMAILS ({len(all_emails)}):\n{email_lines}")
    else:
        context_parts.append("RECENT UNREAD EMAILS: None")

    # Recent Slack DMs
    if config.SLACK_BOT_TOKEN:
        try:
            dms = fetch_dms()
            if dms:
                dm_lines = "\n".join(f"- {d['user']}: {d['text'][:100]}" for d in dms[:10])
                context_parts.append(f"RECENT SLACK DMs ({len(dms)}):\n{dm_lines}")
            else:
                context_parts.append("RECENT SLACK DMs: None")
        except Exception:
            context_parts.append("RECENT SLACK DMs: Error fetching")
    else:
        context_parts.append("SLACK: Not connected")

    context = "\n\n".join(context_parts)

    # Status info
    status = (
        f"Gmail accounts: {', '.join(config.GMAIL_ACCOUNTS) or 'none'}\n"
        f"Slack: {'connected' if config.SLACK_BOT_TOKEN else 'not connected'}"
    )

    try:
        # Build messages with conversation history
        messages = [
            {"role": "system", "content": (
                "You are Sentinel, a personal monitoring assistant. You watch the user's "
                "Gmail and Slack and keep them informed. Be concise and direct — this is "
                "a chat message, not an essay. Use bullet points for lists.\n\n"
                f"STATUS:\n{status}\n\n"
                f"CURRENT DATA:\n{context}\n\n"
                "If the user asks about emails, use the email data above. "
                "If they ask about Slack, use the Slack data above. "
                "If they ask to send a Slack message, say you'll send it and confirm. "
                "If they ask to check now, say you're checking. "
                "Keep responses short — 2-5 lines max."
            )},
        ]
        # Add conversation history for context
        messages.extend(_conversation[-MAX_HISTORY:])
        # Add current user message
        messages.append({"role": "user", "content": text})

        resp = agent.gemini.chat(
            messages=messages,
            model="flash",
            max_tokens=4096,
        )
        response = resp.text

        # Save to conversation history
        _conversation.append({"role": "user", "content": text})
        _conversation.append({"role": "assistant", "content": response})
        # Trim history
        while len(_conversation) > MAX_HISTORY * 2:
            _conversation.pop(0)

        # If Gemini suggests sending a Slack message, try to do it
        if _should_send_slack(text, response):
            slack_result = _try_send_slack(text)
            if slack_result:
                response += f"\n\n{slack_result}"

        # If user wants a fresh check, do it
        text_lower = text.lower()
        if any(w in text_lower for w in ["check now", "refresh", "check again", "look now"]):
            check_gmail()
            check_slack()

        return response

    except Exception as e:
        _log("GEMINI", f"Error: {e}")
        # Fallback: just show the data directly
        return f"Here's what I have:\n\n{context}"


def _should_send_slack(user_text: str, ai_response: str) -> bool:
    """Detect if the user wants to send a Slack message."""
    text = user_text.lower()
    return any(w in text for w in [
        "tell ", "message ", "send ", "dm ", "slack ",
        "let them know", "reply to", "write to",
    ])


def _try_send_slack(text: str) -> str | None:
    """Try to extract and send a Slack message from natural language."""
    if not config.SLACK_BOT_TOKEN:
        return None

    # Use Gemini to extract the target and message
    try:
        resp = agent.gemini.chat(
            messages=[
                {"role": "system", "content": (
                    "Extract the Slack recipient and message from the user's text. "
                    "Reply with EXACTLY this format, nothing else:\n"
                    "TO: channel_name or user_name\n"
                    "MSG: the message\n\n"
                    "If you can't extract both, reply with: SKIP"
                )},
                {"role": "user", "content": text},
            ],
            model="flash",
            max_tokens=100,
        )

        lines = resp.text.strip().split("\n")
        if resp.text.strip() == "SKIP" or len(lines) < 2:
            return None

        target = None
        message = None
        for line in lines:
            if line.startswith("TO:"):
                target = line[3:].strip().lstrip("#@")
            elif line.startswith("MSG:"):
                message = line[4:].strip()

        if not target or not message:
            return None

        from slack_sdk import WebClient
        client = WebClient(token=config.SLACK_BOT_TOKEN)

        # Try as channel first, then as DM
        try:
            client.chat_postMessage(channel=f"#{target}", text=message)
            return f"Sent to #{target}"
        except Exception:
            # Try as DM
            try:
                users = client.users_list()
                for u in users["members"]:
                    if u.get("name") == target or (u.get("real_name") or "").lower() == target.lower():
                        conv = client.conversations_open(users=[u["id"]])
                        client.chat_postMessage(channel=conv["channel"]["id"], text=message)
                        return f"DM sent to {target}"
            except Exception:
                pass

        return None

    except Exception as e:
        _log("SLACK-SEND", f"Error: {e}")
        return None


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
                    response_text = handle_message(text)
                    agent.vibes.send(text=response_text)
                    _log("WEBHOOK", f"Responded: {response_text[:60]}")

            elif event_type == "agent.wave":
                # User opened the agent chat
                agent.vibes.send(text="Sentinel here. What do you need?")

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
    agent.vibes.send(text="Sentinel is online. Watching your email and Slack.")

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
