# Personal Agent Developer Guide

Build a Python agent that runs on your machine and connects to Zinq. Monitor email, automate Slack, track crypto, send daily digests -- anything Python can do, your agent can do.

**Time to first vibe: 10 minutes.**

---

## Overview

A personal agent is a Python script that uses the `ZinqAgent` SDK to interact with a single user (you). It runs on your machine (laptop, server, cloud VM) and communicates with the Zinq platform via REST API.

```
Your Machine                    Zinq Platform                  Your Phone
   |                                |                              |
   |--- agent.vibes.send() -------->|                              |
   |                                |--- push notification ------->|
   |                                |                              |
   |<-- agent.vibes.received() -----|<--- user sends vibe ---------|
```

There is no web dashboard or portal. Everything is done through Python code and the SDK.

---

## Step 1: Install the SDK

```bash
pip install zinq-agent
```

For webhook support (real-time events from users):

```bash
pip install zinq-agent[webhook]
```

## Step 2: Create Your Agent

Open the Zinq app on your phone, go to **My Agents**, and tap **Create Agent**. You get back an API key (`zak_...`). This key is shown once -- save it.

Alternatively, if you already have an agent, use its existing API key.

Set the key as an environment variable:

```bash
export ZINQ_API_KEY=zak_your_key_here
```

## Step 3: Write Your Agent

Create a file called `my_agent.py`:

```python
from zinq_agent import ZinqAgent

agent = ZinqAgent()  # reads ZINQ_API_KEY from env

# Send a vibe to yourself
agent.vibes.send(text="Agent is alive!")

# Read your diary
for entry in agent.diary.iter(size=5):
    print(f"  {entry.created_at}: {entry.text}")

# Check your credits
ctx = agent.user.context()
print(f"Credits: {ctx.credit_status.credits_remaining}")

agent.close()
```

## Step 4: Run It

```bash
python my_agent.py
```

Open your Zinq app. You should see a vibe from your agent.

---

## Code Patterns

### Polling agent (no webhook server)

Best for periodic checks -- email, prices, calendar events. Runs as a loop or cron job.

```python
from zinq_agent import ZinqAgent
from apscheduler.schedulers.blocking import BlockingScheduler

agent = ZinqAgent()

def check_something():
    # Your logic here
    agent.vibes.send(text="Something happened!")

scheduler = BlockingScheduler()
scheduler.add_job(check_something, "interval", minutes=5)
scheduler.start()
```

### Webhook agent (real-time responses)

Best for interactive agents that respond to user messages immediately.

```python
from zinq_agent import ZinqAgent, ZinqWebhook

agent = ZinqAgent()
webhook = ZinqWebhook(secret="zws_your_secret")

@webhook.on("vibe.received")
def handle(event):
    text = event.data.transcript or event.data.text or ""
    agent.vibes.send(text=f"Got: {text}")

@webhook.on("agent.wave")
def greet(event):
    agent.vibes.send(text="Hey! I'm your agent.")

webhook.start(port=8080)
```

For development, expose your local server with ngrok:

```bash
ngrok http 8080
# Set webhook URL to the ngrok HTTPS URL in My Agents settings
```

### Using Gemini AI

The SDK includes a Gemini proxy -- no separate API key needed. Credits are deducted from the user's account.

```python
response = agent.gemini.chat(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Summarize this email..."},
    ],
    model="flash",  # "flash" (cheap) or "pro" (better)
)
print(response.text)
print(f"Credits used: {response.usage.credits_used}")
```

### Persistent memory

Store and retrieve key-value data that persists between runs:

```python
# Save
agent.memories.save(key="last_check", value="2026-04-19T12:00:00Z")

# Retrieve
mem = agent.memories.get("last_check")
if mem:
    print(mem.value)  # "2026-04-19T12:00:00Z"

# List by category
agent.memories.save(key="pref_diet", value="vegetarian", category="prefs")
prefs = agent.memories.list(category="prefs")
```

### Diary search

Search the user's diary with natural language:

```python
results = agent.diary.search("morning workouts", limit=5)
for r in results.results:
    print(f"[{r.similarity:.0%}] {r.text}")
```

### Interactive vibes

Send vibes with buttons, choices, and structured input:

```python
# Multiple choice
agent.vibes.send(
    text="Which report?",
    input_type="choice",
    options=["Daily", "Weekly", "Monthly"],
)

# Custom buttons
agent.vibes.send(
    text="Your summary is ready.",
    buttons=[
        {"label": "View Details", "value": "view"},
        {"label": "Dismiss", "value": "dismiss"},
    ],
)
```

---

## Testing Tips

### Test without webhooks first

Start with a polling agent or one-shot script. Webhooks add complexity -- save them for when you need real-time responses.

### Use skip_signature_check for local dev

```python
webhook = ZinqWebhook(secret="dev", skip_signature_check=True)
```

Never do this in production.

### Test with curl

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "vibe.received",
    "deliveryId": "test-001",
    "timestamp": "2026-04-19T12:00:00Z",
    "agent": {"id": 1, "name": "Test"},
    "user": {"id": 42, "name": "Test User"},
    "data": {"vibeId": 1, "type": "TEXT", "text": "hello", "createdAt": "2026-04-19T12:00:00Z"}
  }'
```

### Check credits before AI calls

```python
ctx = agent.user.context()
if ctx.credit_status.credits_remaining < 5:
    agent.vibes.send(text="Low on AI credits this month.")
else:
    response = agent.gemini.chat(messages=[...])
```

---

## Deployment

Your agent is a Python script. Deploy it anywhere Python runs.

### Quick options

| Platform | Cost | Best For |
|----------|------|----------|
| Your laptop | Free | Development, testing |
| GCloud e2-micro | Free tier | Always-on polling agents |
| AWS t2.micro | Free tier (12 months) | Always-on polling agents |
| Railway | Free (500 hrs/mo) | Webhook agents |
| Render | Free tier | Webhook agents |
| Docker anywhere | Varies | Portable deployment |

### Minimal GCloud deployment

```bash
# Create a free-tier VM
gcloud compute instances create my-agent \
  --machine-type=e2-micro \
  --zone=us-central1-a \
  --image-family=debian-12 \
  --image-project=debian-cloud

# SSH in, install, run
gcloud compute ssh my-agent
sudo apt install -y python3-pip python3-venv
python3 -m venv ~/agent && source ~/agent/bin/activate
pip install zinq-agent
# copy your script, set env vars, run with systemd
```

See [deployment.md](deployment.md) for full guides (systemd, Docker, Railway, Render, Fly.io).

---

## Billing

Check your credit balance and usage through the SDK:

```python
# Credit balance
credits = agent.billing.credits()
print(f"Remaining: {credits['remaining']}")
print(f"Tier: {credits['tier']}")
print(f"Resets: {credits['reset_date']}")

# Usage breakdown
usage = agent.billing.usage(period="month")
print(f"Total tokens: {usage['total_tokens']}")
print(f"Total cost: ${usage['total_cost_usd']}")

# Cost estimate before an expensive operation
estimate = agent.billing.cost_estimate(tokens=5000)
print(f"Estimated cost: {estimate['estimated_credits']} credits")
```

---

## Common Pitfalls

### 1. Forgetting to handle voice vibes

Voice vibes have `transcript` but might not have `text`. Always check both:

```python
content = event.data.transcript or event.data.text or "(empty)"
```

### 2. Hardcoding the API key

Use environment variables. Never commit keys to version control:

```python
# Wrong
agent = ZinqAgent(api_key="zak_actual_secret")

# Right
agent = ZinqAgent()  # reads ZINQ_API_KEY from env
```

### 3. Not closing the client

For one-shot scripts, use a context manager:

```python
with ZinqAgent() as agent:
    agent.vibes.send(text="Done!")
# Connection closed automatically
```

### 4. Sending too many vibes at once

Batch information into one vibe instead of spamming:

```python
# Wrong: 50 vibes in a burst
for item in items:
    agent.vibes.send(text=str(item))

# Right: one summary vibe
summary = "\n".join(f"- {item}" for item in items)
agent.vibes.send(text=f"Here are your items:\n{summary}")
```

### 5. Ignoring notification preferences

Check the user's preferred hours before sending non-urgent vibes:

```python
from datetime import datetime
import pytz

ctx = agent.user.context()
if ctx.agent_preferences and ctx.agent_preferences.notification_hours:
    hours = ctx.agent_preferences.notification_hours
    tz = pytz.timezone(ctx.timezone)
    current_hour = datetime.now(tz).hour
    if not (hours.start <= current_hour <= hours.end):
        return  # Save for later
```

---

## Next Steps

- [API Reference](api-reference.md) -- every class, method, and parameter
- [Webhooks](webhooks.md) -- full webhook setup and event types
- [Examples Cookbook](examples.md) -- complete runnable agents
- [Deployment](deployment.md) -- production deployment guides
- [Best Practices](best-practices.md) -- tips for building great agents
