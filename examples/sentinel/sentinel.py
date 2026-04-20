#!/usr/bin/env python3
"""Sentinel — personal monitoring agent for Gmail + Slack.

Watches your email and Slack, sends you vibes on Zinq with
summaries and urgent alerts.

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

import sys
import time
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

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


# ── Gmail check (every 5 minutes) ────────────────────────────────────────

def check_gmail():
    """Poll Gmail for unread emails, send urgent ones immediately."""
    _log("GMAIL", f"Checking {len(config.GMAIL_ACCOUNTS)} accounts...")

    for account in config.GMAIL_ACCOUNTS:
        try:
            # Get last check time from memories
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

            # Classify and handle urgent ones
            urgent = []
            batch = []
            for email in emails:
                urgency = classify_urgency(email)
                email["urgency"] = urgency
                if urgency == "high":
                    urgent.append(email)
                else:
                    batch.append(email)

            # Send urgent emails as immediate vibes
            for email in urgent:
                vibe_text = format_urgent_email(email)
                agent.vibes.send(text=vibe_text)
                _log("GMAIL", f"Sent urgent vibe: {email['subject'][:50]}")

            # Save batch for daily digest
            if batch:
                _log("GMAIL", f"{account}: {len(batch)} emails batched for digest")

            # Update last check time
            now = datetime.now(timezone.utc).isoformat()
            agent.memories.save(f"last_gmail_check_{account}", now)

        except Exception as e:
            _log("GMAIL", f"Error checking {account}: {e}")


# ── Slack check (every 10 minutes) ───────────────────────────────────────

def check_slack():
    """Poll Slack for DMs and mentions, send urgent ones immediately."""
    if not config.SLACK_BOT_TOKEN:
        return

    _log("SLACK", "Checking DMs and mentions...")

    try:
        # Get last check time
        last_check = None
        try:
            mem = agent.memories.get("last_slack_check")
            if mem:
                last_check = mem.value
        except Exception:
            pass

        dms = fetch_dms(since=last_check)
        mentions = fetch_mentions(since=last_check)

        # Send urgent DMs immediately
        for dm in dms:
            if is_urgent_dm(dm):
                vibe_text = format_urgent_dm(dm)
                agent.vibes.send(text=vibe_text)
                _log("SLACK", f"Sent urgent DM vibe from {dm['user']}")

        total = len(dms) + len(mentions)
        _log("SLACK", f"{len(dms)} DMs, {len(mentions)} mentions")

        # Update last check time
        now = str(time.time())
        agent.memories.save("last_slack_check", now)

    except Exception as e:
        _log("SLACK", f"Error: {e}")


# ── Hourly Slack summary ─────────────────────────────────────────────────

def slack_summary():
    """Send hourly Slack activity summary."""
    if not config.SLACK_BOT_TOKEN:
        return

    _log("SLACK", "Building hourly summary...")

    try:
        # Get last hour's activity
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
    """Send daily email digest with all unread emails summarized."""
    _log("DIGEST", "Building daily email digest...")

    try:
        # Check if we already sent today's digest
        try:
            mem = agent.memories.get("last_email_digest")
            if mem and mem.value == datetime.now().strftime("%Y-%m-%d"):
                _log("DIGEST", "Already sent today's digest, skipping")
                return
        except Exception:
            pass

        all_emails = []
        for account in config.GMAIL_ACCOUNTS:
            # Get last 24h of emails
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

        # Mark today as done
        agent.memories.save("last_email_digest", datetime.now().strftime("%Y-%m-%d"))

    except Exception as e:
        _log("DIGEST", f"Error: {e}")


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    _log("SENTINEL", "Starting Sentinel agent")
    _log("SENTINEL", f"Gmail accounts: {config.GMAIL_ACCOUNTS or '(none)'}")
    _log("SENTINEL", f"Slack: {'enabled' if config.SLACK_BOT_TOKEN else 'disabled'}")

    if not config.ZINQ_API_KEY:
        _log("SENTINEL", "ERROR: ZINQ_API_KEY not set")
        sys.exit(1)

    if not config.GMAIL_ACCOUNTS and not config.SLACK_BOT_TOKEN:
        _log("SENTINEL", "ERROR: No GMAIL_ACCOUNTS or SLACK_BOT_TOKEN set")
        sys.exit(1)

    # Send startup vibe
    agent.vibes.send(text="Sentinel is online. Monitoring your email and Slack.")

    # Set up scheduler
    scheduler = BlockingScheduler()

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

    _log("SENTINEL", "Scheduler started. Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        _log("SENTINEL", "Shutting down.")
        agent.vibes.send(text="Sentinel going offline.")
        agent.close()


if __name__ == "__main__":
    main()
