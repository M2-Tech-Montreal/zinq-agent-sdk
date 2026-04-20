# Sentinel Agent — Build Prompt

Copy this prompt into Claude Code on your deployment instance to build a Sentinel agent.

## Prerequisites

Before running this prompt, set up:

1. **Zinq API key** — `export ZINQ_API_KEY=zak_your_key`
2. **Gmail OAuth credentials** — download `credentials.json` from Google Cloud Console (Gmail API enabled, OAuth consent screen configured)
3. **Slack Bot Token** — create a Slack app with scopes: `channels:history`, `im:history`, `users:read`, `mpim:history`, `channels:read`, `im:read`. Copy the `xoxb-` token.

## The Prompt

```
Build a Sentinel personal agent using the zinq-agent Python SDK.
Read CLAUDE.md for SDK reference.

## What Sentinel does

Sentinel is a background monitoring agent that watches my Gmail and Slack,
then sends me vibes on Zinq with summaries and urgent alerts.

## Gmail Monitoring

- Monitor two Gmail accounts: ACCOUNT_1 and ACCOUNT_2
- Use the Gmail API with OAuth (credentials.json is in this directory)
- Poll every 5 minutes for new unread emails
- For each new email, use Gemini to classify urgency (high/medium/low)
- HIGH urgency: send a vibe immediately with sender, subject, and 1-line summary
- MEDIUM/LOW: batch for the daily digest

Daily digest at 8am local time:
- Group emails by account, then by urgency
- Use Gemini to summarize each email thread (not just subject lines)
- Format as a clean vibe with counts and summaries
- Save the digest to memories (key: "last_email_digest") so we don't re-send

## Slack Monitoring

- Use the Slack Bot Token (SLACK_BOT_TOKEN env var)
- Poll every 10 minutes for new DMs and @mentions
- For DMs: check im.history for unread messages
- For mentions: search for @mentions in channels the bot is in

Hourly Slack summary vibe:
- Group by: DMs received, mentions, active channels
- Use Gemini to summarize conversations (not raw messages)
- Only send if there's actual activity (skip empty hours)
- Save last check timestamp to memories (key: "last_slack_check")

Urgent DMs (from specific users or containing urgent keywords):
- Send immediately as a vibe, don't wait for hourly summary

## Architecture

Create these files:
- sentinel.py — main entry point, runs the scheduler
- gmail_monitor.py — Gmail API integration (OAuth flow, fetch unread, classify)
- slack_monitor.py — Slack API integration (DMs, mentions, channels)
- summarizer.py — Gemini-powered summarization for emails and Slack
- config.py — configuration (poll intervals, urgent keywords, accounts)

## Scheduling

Use APScheduler (pip install apscheduler):
- Gmail check: every 5 minutes
- Slack check: every 10 minutes
- Email digest: daily at 8am
- Slack summary: hourly at :00

## Error handling

- Gmail OAuth token refresh: handle token expiry, re-auth gracefully
- Slack rate limits: respect Retry-After headers
- Network errors: log and retry on next poll cycle, don't crash
- All errors logged with UILoggerService pattern (print with timestamp + tag)

## Memory usage

Use agent.memories to track state:
- "last_gmail_check_ACCOUNT" — timestamp of last check per account
- "last_slack_check" — timestamp of last Slack check
- "last_email_digest" — date of last daily digest
- "urgent_keywords" — list of words that trigger immediate alerts

## Systemd service

Create a systemd unit file (sentinel.service) so it runs on boot:
- WorkingDirectory=/home/vm/zinq-agent-python/examples/sentinel
- ExecStart with the venv python
- Restart=always
- Environment vars for API keys

## Dependencies

Add to requirements.txt:
- zinq-agent
- google-api-python-client
- google-auth-oauthlib
- slack-sdk
- apscheduler

## DO NOT

- Don't use IMAP — use Gmail API (better for OAuth, labels, threads)
- Don't store credentials in code — use env vars
- Don't send empty digests — skip if no new emails/messages
- Don't re-send old emails — track last check time in memories
- Don't crash on errors — log and continue
```
