# Sentinel — TODO

## Send emails via Gmail
- Add `gmail.send` scope to OAuth
- Re-auth both accounts with new scope
- Add `send_email(account, to, subject, body)` to `gmail_monitor.py`
- Gemini detects "reply to Dan" or "email John about X" and triggers send
- User confirms before sending ("Send this? [preview]")

## Fix Slack mentions
- `search:read` scope requires a **user token** (`xoxp-`), not a bot token (`xoxb-`)
- Options:
  1. Add a user token OAuth flow (user installs app → gets `xoxp-` token with `search:read`)
  2. Use `conversations.history` on each channel the bot is in and filter for mentions of the bot user ID — no `search:read` needed, works with bot token
- Option 2 is simpler — iterate channels, check history for `<@BOT_USER_ID>` in message text
- Need `channels:history` (already have) + `groups:history` (for private channels)
