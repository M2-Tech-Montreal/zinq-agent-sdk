# Zinq Agent Python SDK

## What this repo is

Python SDK for building personal and business agents on the Zinq platform. Agents connect to Zinq users and can read diary entries, send vibes, use Gemini LLM, store memories, and receive webhooks.

## Quick start: Build an agent

### 1. Create an agent in the Zinq app
Open the menu → **My Agents** → tap **+** → enter a name → copy the `zak_` API key.

### 2. Install the SDK
```bash
pip install zinq-agent
# or with webhook support:
pip install zinq-agent[webhook]
```

### 3. Write your agent

```python
import os
from zinq_agent import ZinqAgent

agent = ZinqAgent(api_key=os.environ["ZINQ_API_KEY"])

# Read user's diary
diary = agent.diary.list(size=5)
for entry in diary.entries:
    print(entry.text)

# Send a vibe to the user
agent.vibes.send(text="Hello from my agent!")

# Use Gemini
response = agent.gemini.chat(
    messages=[{"role": "user", "content": "Summarize my day"}],
    model="flash",
)
print(response.text)

# Store a memory
agent.memories.save(key="last_run", value="2026-04-20T17:00:00Z")
```

### 4. Deploy to GCloud (free tier)

```bash
# Create VM
gcloud compute instances create my-agent \
  --machine-type=e2-micro \
  --zone=us-central1-a \
  --image-family=debian-12 \
  --image-project=debian-cloud

# SSH in
gcloud compute ssh my-agent

# Set up
sudo apt update && sudo apt install -y python3-pip python3-venv git
git clone https://github.com/M2-Tech-Montreal/zinq-agent-python.git
cd zinq-agent-python
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[webhook]

# Set API key
export ZINQ_API_KEY=zak_your_key_here

# Run
python my_agent.py
```

For persistent running, use systemd — see `docs/deployment.md`.

## SDK Architecture

```
zinq_agent/
├── client.py        # ZinqAgent + AsyncZinqAgent main classes
│                     # Sub-clients: diary, vibes, feed, contacts, zones,
│                     #              memories, billing, user, gemini, tools
├── gemini.py        # GeminiClient (chat, embed) — streaming NOT supported
├── marketplace.py   # ZinqMarketplaceAdmin for business agents
├── webhook.py       # ZinqWebhook for receiving events
├── models.py        # Pydantic models (DiaryEntry, Vibe, Contact, etc.)
└── exceptions.py    # ZinqError, AuthenticationError, InsufficientCreditsError
```

## Key APIs

| Client | Method | What it does |
|--------|--------|-------------|
| `agent.diary` | `.list()`, `.search()`, `.save()`, `.star()`, `.archive()` | Read/write diary entries |
| `agent.vibes` | `.send()`, `.received()`, `.reply()` | Send/receive vibes |
| `agent.feed` | `.list()` | Read the user's vibe feed |
| `agent.contacts` | `.list()`, `.search()`, `.profile()` | User's connections |
| `agent.zones` | `.list()`, `.get()`, `.vibes()` | User's zones/clubs |
| `agent.memories` | `.save()`, `.get()`, `.list()`, `.delete()` | Persistent key-value storage |
| `agent.user` | `.context()`, `.profile()`, `.update_profile()` | User info + agent's own profile |
| `agent.gemini` | `.chat()`, `.embed()` | Gemini LLM (no streaming) |
| `agent.billing` | `.credits()`, `.usage()` | Credit status |
| `agent.tools` | `.register()`, `.list()`, `.remove()` | Register tools that Gemini can call |

## API base URL

- **Production**: `https://zinq-app.com/api`
- **Dev**: `https://zinq-app.com/dev-api`
- Agent API path: `/agent-api/` (authenticated via `X-Agent-Key` header)

## Auth

All API calls are authenticated via the `zak_` API key passed as `X-Agent-Key` header. The SDK handles this automatically.

```python
# From environment variable (recommended)
agent = ZinqAgent()  # reads ZINQ_API_KEY

# Explicit
agent = ZinqAgent(api_key="zak_...")
```

## Running tests

```bash
# Install dev dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[webhook] pytest pytest-timeout

# E2E tests (need a real API key)
export ZINQ_TEST_API_KEY=zak_your_key
export ZINQ_DEV_URL=https://zinq-app.com/api
pytest tests/e2e/test_personal_agent.py -v --timeout=60
```

## Building marketplace (business) agents

Business agents are YAML-driven and run on Zinq's servers. Developers define the agent's personality, tools, and data collections in YAML, then deploy via the SDK.

```python
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin(api_key="zbk_your_key")

# Deploy a YAML agent definition
admin.agent.deploy(open("agent.yaml").read())

# See who's using your agent
print(f"{admin.users.count()} active users")

# Reply to conversations awaiting human response
convos = admin.conversations.list(status="awaiting_human")
for c in convos:
    admin.conversations.reply(c["sessionId"], "Thanks for reaching out!")

# Send broadcast to all users
admin.broadcast("New menu items available!")

# Manage data collections (menus, inventory, etc.)
admin.data.add("menu", {"name": "Espresso", "price": 4.50})
items = admin.data.list("menu")

# Test your agent
admin.test.chat("What are your specials today?")

# Publish to marketplace
admin.agent.publish()
```

### YAML agent definition

```yaml
name: Rosa's Bakery
type: rosas_bakery
display_name: Rosa
bio: Your neighborhood bakery assistant
prompt: |
  You are Rosa, the friendly assistant for Rosa's Bakery.
  Help customers with menu items, hours, and placing orders.
  Be warm and enthusiastic about baked goods.
tools:
  - query_log: Track customer orders
  - structured_log: Save order details
  - request_human_review: Escalate complex orders
collections:
  - name: menu
    description: Bakery menu items with prices
  - name: hours
    description: Store hours and holiday schedule
```

See `docs/dev-guide-marketplace-tier1.md` for no-code agents and `docs/dev-guide-marketplace-tier2.md` for agents with webhook handlers.

## Example agents

| Example | Pattern | What it does |
|---------|---------|-------------|
| **Echo Bot** | Webhook | Repeats everything — simplest possible agent |
| **Daily Digest** | Polling/cron | Summarizes emails, calendar, Slack at 8am |
| **Sentinel** | Polling | Monitors email/Slack, sends priority alerts, saves memories |
| **Fitness Coach** | Webhook + Gemini | Reads health data, gives coaching via Gemini |
| **Email Monitor** | Polling | IMAP check → urgent emails become vibes |
| **Slack Bridge** | Webhook | Forwards Slack channel activity to Zinq |
| **Appointment Booker** | Webhook + interactive | Interactive booking with choice buttons |
| **Personal Shopper** | Webhook + Gemini + memories | Product recommendations using preferences |
| **Joe's Barber** | Marketplace (Tier 1) | YAML-only barber shop agent with booking |
| **Rosa's Bakery** | Marketplace (Tier 1) | YAML-only bakery with menu and orders |
| **Nutrition Coach** | Marketplace (Tier 2) | Webhook + tools for meal planning |
| **Trading Bot** | Marketplace (Tier 2) | Webhook + external API for stock alerts |

All examples are in `docs/examples.md`. E2E tests for Sentinel, Bakery, Barber, Nutrition, and Trading are in `tests/e2e/`.

## Docs

- `docs/getting-started.md` — 5-minute quickstart
- `docs/api-reference.md` — Complete API reference
- `docs/examples.md` — Copy-paste recipes
- `docs/webhooks.md` — Webhook setup and event types
- `docs/deployment.md` — Deploy to GCloud, AWS, Docker, Railway, etc.
- `docs/best-practices.md` — Tips and common pitfalls
- `docs/dev-guide-personal.md` — Personal agent development guide
- `docs/dev-guide-marketplace-tier1.md` — No-code marketplace agents (YAML)
- `docs/dev-guide-marketplace-tier2.md` — Marketplace agents with webhooks
- `docs/dev-guide-testing.md` — Testing with dev/prod agent IDs
- `docs/business-agents.md` — ZinqMarketplaceAdmin API reference

## Webhook events

| Event | When |
|-------|------|
| `vibe.received` | User sends a vibe to the agent |
| `vibe.reply` | User replies to a specific agent vibe |
| `charm.received` | User sends a charm reaction |
| `agent.wave` | User opens the agent chat |

## Common patterns

### Polling agent (cron/scheduled)
```python
agent = ZinqAgent()
# Check for new vibes every 5 minutes
vibes = agent.vibes.received(unread=True)
for vibe in vibes:
    process(vibe)
```

### Webhook agent (real-time)
```python
agent = ZinqAgent()
webhook = ZinqWebhook(secret="dev", skip_signature_check=True  # Signature verification coming soon)

@webhook.on("vibe.received")
def handle(event):
    agent.vibes.send(text=f"Got: {event.data.text}")

webhook.serve(port=8080)
```

### Gemini-powered agent
```python
agent = ZinqAgent()
diary = agent.diary.list(size=10)
context = "\n".join(e.text for e in diary.entries if e.text)

response = agent.gemini.chat(
    messages=[
        {"role": "system", "content": "You are a wellness coach."},
        {"role": "user", "content": f"Based on my diary:\n{context}\n\nHow am I doing?"},
    ],
    model="flash",
)
agent.vibes.send(text=response.text)
```

### Agent with tools (Gemini calls your endpoints)
```python
agent = ZinqAgent()

# Register tools — Gemini will call these when users ask questions
agent.tools.register(
    name="get_positions",
    description="Get current open trading positions",
    webhook_url="https://my-server.com/tools/positions",
)
agent.tools.register(
    name="place_order",
    description="Place a buy or sell order",
    webhook_url="https://my-server.com/tools/order",
    parameters='{"type":"object","properties":{"symbol":{"type":"string"},"side":{"type":"string","enum":["buy","sell"]},"quantity":{"type":"integer"}},"required":["symbol","side","quantity"]}',
)

# That's it — when a user messages this agent, Zinq's Gemini sees the tools,
# decides when to call them, and POSTs to your webhook URLs.
# Your server returns the result, Gemini summarizes it for the user.
```
