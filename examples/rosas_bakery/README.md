# Rosa's Bakery — Marketplace Agent Example

A complete marketplace agent with static menu, external tools for live specials and orders, human handoff for complex requests, and daily broadcasts.

## What this demonstrates

- **Pickup ordering** — browse menu, check availability, place order via external webhook
- **Daily specials** — external tool fetches live specials from Rosa's server
- **Customer memory** — remembers preferences (oat milk, allergies, usual order)
- **Human handoff** — complex orders (wedding cakes, complaints) escalated to Rosa via `request_human_review`
- **Customer service** — Rosa replies to specific customers via SDK
- **Morning broadcast** — daily specials sent to all customers via `morning_update.py`

## Setup

### 1. Generate SSL cert (for the mock server)

```bash
cd examples/rosas_bakery
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=34.58.243.153"
```

### 2. Start the mock bakery server

```bash
python rosa_server.py
```

Runs on `https://0.0.0.0:8081` with endpoints:
- `/specials` — today's specials
- `/inventory` — item availability
- `/orders` — place an order
- `/wait-time` — estimated wait

### 3. Deploy the agent

```bash
export ZINQ_BIZ_KEY=zbk_your_key
python setup_rosa.py
```

### 4. Test

```python
from zinq_agent import ZinqMarketplaceAdmin
admin = ZinqMarketplaceAdmin(api_key="zbk_...")
admin.test.chat("What do you have?")
admin.test.chat("Any specials today?")
admin.test.chat("I'll take a croissant and a latte")
```

## Human Handoff

When the agent can't handle something — wedding cakes, complaints, large catering orders — it calls `request_human_review`. Rosa gets notified and can jump into the conversation:

```
Customer: I need a 3-tier wedding cake with fondant flowers for 200 guests.
Agent:    This sounds beautiful! Let me connect you with Rosa directly —
          she'll want to discuss the design with you personally.
          [escalated to human]
```

Rosa sees the escalation in her SDK:

```python
# Check conversations needing attention
convos = admin.conversations.list(status="awaiting_human")
for c in convos:
    # See what the customer said
    history = admin.conversations.history(c["userId"], limit=5)
    for msg in history:
        print(f"  {msg['userName']}: {msg['textContent']}")

    # Reply directly to the customer
    admin.conversations.reply(c["sessionId"],
        "Hi! Rosa here. I'd love to make your wedding cake. "
        "Can you tell me more about the design you're envisioning?")
```

The customer sees Rosa's reply as a vibe from the bakery agent — seamless handoff, no context lost.

## Customer Service

Rosa can reach out to any customer who's used the agent:

```python
# Find a customer by conversation history
results = admin.conversations.search(user_id=1147, query="defective croissant")

# Send them a message
admin.conversations.reply(session_id,
    "So sorry about the croissant! Come in for a free replacement anytime today.")
```

## Morning Broadcast

Rosa runs `morning_update.py` each morning (or sets up a cron job):

```bash
python morning_update.py
```

All customers who have the bakery agent enabled receive:

```
Good morning from Rosa's Bakery!

Fresh out of the oven today:
  Lavender Honey Croissant — $6.00 (limited batch, only 20!)
  Rosemary Focaccia — $7.50 (fresh rosemary from the garden)
  Matcha Muffin — $4.50 (new recipe — tell us what you think!)

Order ahead for pickup — just message me!
```

## Architecture

- **Static menu** — stored in Zinq collections via `setup_rosa.py`, never changes
- **Specials** — external tool calls Rosa's server, she updates her database
- **Orders** — external tool POSTs to Rosa's server with userId
- **Memory** — Gemini remembers customer preferences (oat milk, allergies, usual order)
- **Human handoff** — `request_human_review` for complex/sensitive requests
- **Customer service** — `admin.conversations.reply()` for direct replies
- **Broadcasts** — `admin.broadcast()` for daily specials to all customers
- **Two-part prompt** — system prompt (tools/memory) injected by Zinq + Rosa's personality from YAML

## Files

| File | What |
|------|------|
| `rosa.yaml` | Agent definition — personality, tools, collections |
| `rosa_server.py` | Mock bakery backend (specials, inventory, orders) |
| `setup_rosa.py` | Deploy agent + load menu data via SDK |
| `morning_update.py` | Daily specials update + broadcast to all customers |
