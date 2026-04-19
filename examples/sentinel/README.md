# Sentinel — Email & Slack Monitor Agent

**The flagship example of what you can build with the Zinq Agent SDK.**

Sentinel watches your Gmail and Slack, sends you Zinq vibes when something important comes in, and lets you reply without leaving the app.

## What It Does

- Checks Gmail every 5 minutes, scores importance with AI
- Checks Slack every 2 minutes for @mentions and DMs
- Sends you a Zinq vibe immediately for urgent items
- Sends hourly digest summaries for everything else
- You can ask it questions: "Any important emails?", "What's happening on Slack?"
- You can reply through vibes: "Reply to Glenn: sounds good, Thursday works"

## Setup (10 minutes)

### 1. Create Your Agent in Zinq

Open Zinq app → Settings → My Agents → Create Agent
- Name: "Sentinel"
- Bio: "Your email & Slack watcher"
- Copy your API key (shown once!)

### 2. Get Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Create app password for "Mail"
3. Copy the 16-character password

### 3. Get Slack Bot Token

1. Go to https://api.slack.com/apps → Create New App
2. Add scopes: `channels:history`, `channels:read`, `im:history`, `im:read`, `users:read`, `search:read`
3. Install to workspace → Copy Bot Token (`xoxb-...`)

### 4. Deploy

```bash
# Install
pip install zinq-agent slack-sdk apscheduler

# Set credentials
export ZINQ_API_KEY=zak_your_key
export GMAIL_USER=you@gmail.com
export GMAIL_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx
export SLACK_BOT_TOKEN=xoxb-your-token

# Run
python sentinel.py
```

### 5. Deploy to GCloud (free, runs 24/7)

```bash
gcloud compute instances create sentinel \
  --machine-type=e2-micro --zone=us-east1-b \
  --image-family=debian-12 --image-project=debian-cloud

gcloud compute ssh sentinel
# ... install, configure, run as systemd service
```

See `deploy-gcloud.md` for full instructions.

## What You'll See in Zinq

```
Sentinel: 📬 3 new emails (last hour)
• Glenn R. — "Dubai deal update" — 10 min ago ⚡
• Shopify — "Your order shipped" — 25 min ago
• Newsletter — "TechCrunch Daily" — 45 min ago

Reply with a number to read, or "reply 1: [message]"
```

```
Sentinel: 💬 Slack update
• #dev: @you mentioned by Alex: "Can you review PR #234?"
• DM from Sarah: "Meeting moved to 3pm"
```

## Files

- `sentinel.py` — main agent (entry point)
- `gmail_monitor.py` — Gmail IMAP polling + importance scoring
- `slack_monitor.py` — Slack API polling
- `classifier.py` — AI importance scoring via Gemini
- `deploy-gcloud.md` — GCloud deployment guide
