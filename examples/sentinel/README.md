# Sentinel — Gmail + Slack Monitoring Agent

Watches your Gmail and Slack, sends you Zinq vibes with summaries and urgent alerts.

## Features

- Gmail poll every 5 minutes — urgent emails sent as immediate vibes
- Slack poll every 10 minutes — urgent DMs sent immediately
- Hourly Slack summary vibe
- Daily email digest at 8am
- Gemini-powered summarization
- State tracked in agent memories (no re-sends)

## Setup

### 1. Install dependencies

```bash
cd zinq-agent-python
pip install -e .
pip install apscheduler google-api-python-client google-auth-oauthlib slack-sdk
```

### 2. Create agent in Zinq app

Open menu → **My Agents** → **+** → name it "Sentinel" → copy the `zak_` API key.

### 3. Gmail API credentials

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Enable the Gmail API
3. Create **OAuth client ID** → **Desktop app**
4. Download the JSON → save as `credentials.json` in this directory (or `~/gmail_secret/client_secret.json`)
5. Add your Gmail addresses as test users in the OAuth consent screen

### 4. Slack Bot Token (optional)

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App
2. Add Bot Token Scopes: `channels:history`, `channels:read`, `im:history`, `im:read`, `users:read`, `search:read`
3. Install to workspace → copy `xoxb-` token

### 5. Run

```bash
export ZINQ_API_KEY=zak_your_key
export GMAIL_ACCOUNTS=you@gmail.com,work@company.com
export SLACK_BOT_TOKEN=xoxb-your-token          # optional
export VIP_SENDERS=boss@company.com              # optional
python sentinel.py
```

First run will prompt you to authorize each Gmail account — it prints a URL, you open it in any browser, sign in, paste back the code.

### 6. Deploy as systemd service (runs on boot)

```bash
sudo cp sentinel.service /etc/systemd/system/
# Edit the service file with your API keys:
sudo nano /etc/systemd/system/sentinel.service
sudo systemctl enable sentinel
sudo systemctl start sentinel
```

## Running Multiple Instances

Each Sentinel instance needs its own agent (separate `zak_` key) and webhook port. Create multiple agents in the Zinq app, then run each with different env vars:

```bash
# Instance 1 — watches personal email
ZINQ_API_KEY=zak_first_key \
GMAIL_ACCOUNTS=personal@gmail.com \
SENTINEL_WEBHOOK_PORT=8082 \
SENTINEL_WEBHOOK_HOST=your.server.ip \
python sentinel.py

# Instance 2 — watches work email
ZINQ_API_KEY=zak_second_key \
GMAIL_ACCOUNTS=work@company.com \
SENTINEL_WEBHOOK_PORT=8083 \
SENTINEL_WEBHOOK_HOST=your.server.ip \
python sentinel.py
```

Each instance shows up as a separate agent in your Zinq app with its own chat thread.

For systemd, copy the service file with a different name per instance:

```bash
sudo cp sentinel.service /etc/systemd/system/sentinel-personal.service
sudo cp sentinel.service /etc/systemd/system/sentinel-work.service
# Edit each with its own ZINQ_API_KEY, GMAIL_ACCOUNTS, and SENTINEL_WEBHOOK_PORT
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZINQ_API_KEY` | Yes | -- | Your agent's API key (`zak_...`) |
| `GMAIL_ACCOUNTS` | Yes* | -- | Comma-separated Gmail addresses to monitor |
| `SLACK_BOT_TOKEN` | No | -- | Slack bot token (`xoxb-...`) |
| `VIP_SENDERS` | No | -- | Comma-separated emails that trigger immediate alerts |
| `GMAIL_POLL_INTERVAL` | No | 300 | Seconds between Gmail checks |
| `SLACK_POLL_INTERVAL` | No | 600 | Seconds between Slack checks |
| `SENTINEL_WEBHOOK_PORT` | No | 8080 | Port for the local webhook listener |
| `SENTINEL_WEBHOOK_HOST` | No | -- (disabled) | Public IP for webhook registration with Zinq. If not set, webhook is disabled (polling only) |

*At least one of `GMAIL_ACCOUNTS` or `SLACK_BOT_TOKEN` is required.

## Files

| File | What |
|------|------|
| `sentinel.py` | Main entry point — scheduler + job definitions |
| `gmail_monitor.py` | Gmail API with OAuth, fetch unread, classify urgency |
| `slack_monitor.py` | Slack DMs + mentions polling |
| `summarizer.py` | Gemini-powered email/Slack summarization |
| `config.py` | Env-based configuration (poll intervals, keywords) |
| `sentinel.service` | Systemd unit file |
| `requirements.txt` | Python dependencies |
| `PROMPT.md` | Claude Code prompt to build this from scratch |
