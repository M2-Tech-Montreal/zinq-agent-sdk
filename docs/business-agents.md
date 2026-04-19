# Business Agents & Marketplace

Build an AI agent for your business. Publish it to the Zinq marketplace. Customers find you and start chatting.

```
Describe your business  -->  AI generates your agent  -->  Publish to marketplace  -->  Customers find you on Zinq
```

No website needed. No app to build. No Shopify subscription. Just an AI agent that talks to your customers.

## Complete Examples

Three working examples you can clone and customize:

| Example | Business Type | Key Features |
|---------|--------------|--------------|
| **[Joe's Barber Shop](../examples/joes_barber/)** | Barber shop | Appointment booking, availability checking, service menu, cancellation |
| **[Rosa's Bakery](../examples/rosas_bakery/)** | Bakery | Pickup orders, daily specials broadcasts, custom cake requests, human handoff |
| **[Dr. Sarah Nutrition](../examples/dr_sarah_nutrition/)** | Nutrition practice | Consultation booking, meal plan intake, AI-powered advice, safety guardrails |

Each example includes:
- `agent.yaml` -- Full agent definition (personality, services, tools)
- `server.py` -- Working webhook server with `ZinqBusinessWebhook`
- `README.md` -- Setup guide with sample conversations

## Architecture Overview

A marketplace business agent has three parts:

1. **YAML definition** (`agent.yaml`) -- Describes your business to the AI: personality, services, menu, tools, escalation rules. Gemini reads this to generate responses.

2. **Webhook server** (`server.py`) -- Handles tool calls from the AI. When a customer says "book me a haircut at 10am", Gemini extracts the parameters and calls your `book_appointment` webhook. You run the logic and return the result.

3. **Admin client** (`ZinqMarketplaceAdmin`) -- Deploy your agent, manage data collections (menus, products), send broadcasts, reply to escalated conversations, view analytics.

```
Customer on Zinq app
        |
        v
   Zinq Platform (Gemini AI)
        |
        |-- reads agent.yaml for personality and tools
        |-- extracts parameters from user messages
        |
        v
   Your Webhook Server (ZinqBusinessWebhook)
        |
        |-- @webhook.action("book_appointment")
        |-- @webhook.action("check_availability")
        |
        v
   Your Business Logic (database, calendar, etc.)
```

## Quick Start

### 1. Install

```bash
pip install zinq-agent[webhook]
```

### 2. Write your agent definition

```yaml
# agent.yaml
name: "My Business"
tagline: "What you do, in one line."
description: "Longer description of your business."
category: "your_category"

personality: |
  You are friendly and professional. Keep responses concise.

greeting: |
  Welcome! How can I help you today?

services:
  - name: "Basic Service"
    price: 50
    duration_minutes: 30

tools:
  - name: book_service
    description: "Book a service for the customer."
    parameters:
      - name: service
        type: string
        required: true
      - name: date
        type: string
        required: true
      - name: customer_name
        type: string
        required: true

webhook_url: "https://your-server.com/webhook"
```

### 3. Build your webhook server

```python
# server.py
import os
from zinq_agent import ZinqMarketplaceAdmin
from zinq_agent.webhook import ZinqBusinessWebhook

admin = ZinqMarketplaceAdmin()
webhook = ZinqBusinessWebhook(
    secret=os.environ["ZINQ_WEBHOOK_SECRET"],
    admin=admin,
)

@webhook.action("book_service")
def book_service(params, session_id):
    # Your booking logic here
    return {
        "confirmed": True,
        "service": params["service"],
        "date": params["date"],
        "message": f"Booked {params['service']} for {params['date']}!",
    }

@webhook.on("agent.wave")
def greet(event):
    admin.conversations.reply(
        str(event.user.id),
        "Welcome! What can I help you with?",
    )

if __name__ == "__main__":
    admin.agent.deploy(open("agent.yaml").read())
    webhook.start(port=8080)
```

### 4. Deploy and go live

```bash
export ZINQ_BIZ_KEY="zbk_your_key_here"
export ZINQ_WEBHOOK_SECRET="zws_your_secret_here"

python server.py
```

## ZinqBusinessWebhook

`ZinqBusinessWebhook` extends `ZinqWebhook` with action routing for tool calls. When Gemini invokes a tool defined in your YAML, Zinq sends a webhook event with the action name and parameters. `ZinqBusinessWebhook` routes it to the correct handler.

### Action handlers

```python
from zinq_agent.webhook import ZinqBusinessWebhook

webhook = ZinqBusinessWebhook(secret="zws_xxx", admin=admin)

@webhook.action("check_availability")
def check_availability(params, session_id):
    """
    params: dict of extracted parameters from the user's message
    session_id: the user's session identifier
    returns: dict that the AI uses to compose its response
    """
    date = params.get("date")
    slots = get_open_slots(date)
    return {"available": bool(slots), "slots": slots}

@webhook.action("book_appointment")
def book_appointment(params, session_id):
    save_to_calendar(params["date"], params["time"], params["name"])
    return {"confirmed": True, "time": params["time"]}
```

### Standard event handlers

`ZinqBusinessWebhook` inherits all event handlers from `ZinqWebhook`:

```python
@webhook.on("agent.wave")       # User opens your agent chat
@webhook.on("vibe.received")    # User sends a message
@webhook.on("vibe.reply")       # User taps a button or replies
@webhook.on("charm.received")   # User sends an emoji reaction
```

## ZinqMarketplaceAdmin

The admin client for managing your marketplace agent programmatically.

### Setup

```python
from zinq_agent import ZinqMarketplaceAdmin

# Pass key directly
admin = ZinqMarketplaceAdmin(api_key="zbk_xxxxx")

# Or read from ZINQ_BIZ_KEY environment variable
admin = ZinqMarketplaceAdmin()

# Context manager (auto-closes connections)
with ZinqMarketplaceAdmin() as admin:
    print(admin.agent.status())
```

### Agent Lifecycle (`admin.agent`)

Deploy, update, and manage your agent's marketplace listing.

```python
# Deploy a new agent definition
result = admin.agent.deploy(open("agent.yaml").read())
# {"agentId": 42, "status": "pending_review"}

# Update an existing definition
admin.agent.update(open("agent_v2.yaml").read())

# Check current status
status = admin.agent.status()
# {"status": "active", "name": "My Agent", "createdAt": "..."}

# Get current YAML definition
yaml_str = admin.agent.definition()

# Enable / disable
admin.agent.enable()
admin.agent.disable()
```

#### Status Values

| Status | Meaning |
|--------|---------|
| `pending_review` | Submitted, awaiting Zinq team review |
| `approved` | Reviewed and approved, ready to enable |
| `active` | Live in the marketplace, users can enable it |
| `disabled` | Removed from marketplace, existing users keep access |

### Users (`admin.users`)

View pseudonymous information about users who have enabled your agent. For privacy, you see name initials and avatars only -- never full profiles.

```python
# Total count
count = admin.users.count()
print(f"{count} users have enabled this agent")

# List users (paginated)
users = admin.users.list(limit=50, offset=0)
for u in users:
    print(u["sessionId"], u["nameInitial"], u["enabledAt"])

# Get a specific user's public profile
profile = admin.users.profile("sess_abc123")
# {"nameInitial": "J", "avatarUrl": "...", "enabledAt": "...", "lastActiveAt": "..."}
```

### Conversations (`admin.conversations`)

View and manage conversations between your agent and its users. Useful for human-in-the-loop workflows where the AI hands off to a human operator.

```python
# List all conversations
all_convos = admin.conversations.list(limit=20)

# Filter by status
awaiting = admin.conversations.list(status="awaiting_human")
active = admin.conversations.list(status="active")
completed = admin.conversations.list(status="completed")

# Get full conversation history
convo = admin.conversations.get("sess_abc123")
for msg in convo["messages"]:
    print(f"[{msg['role']}] {msg['text']}")

# Send a human reply
admin.conversations.reply("sess_abc123", "Thanks for your patience! Here's what I found...")

# Hand back to AI
admin.conversations.resume_ai("sess_abc123")
```

#### Conversation Status Values

| Status | Meaning |
|--------|---------|
| `active` | AI is handling the conversation |
| `awaiting_human` | AI escalated, waiting for human reply |
| `completed` | Conversation ended |

### Reviews (`admin.reviews`)

View user reviews and aggregate rating statistics.

```python
# List reviews
reviews = admin.reviews.list(limit=20, sort="recent")
for r in reviews:
    print(f"{r['rating']}/5: {r['text']}")

# Sort options: "recent" (default), "highest", "lowest"
best = admin.reviews.list(sort="highest", limit=5)

# Aggregate statistics
stats = admin.reviews.stats()
# {
#     "avg_rating": 4.3,
#     "total_count": 50,
#     "distribution": {1: 2, 2: 1, 3: 5, 4: 12, 5: 30}
# }
print(f"Average: {stats['avg_rating']:.1f}/5 ({stats['total_count']} reviews)")
```

### Data Collections (`admin.data`)

Manage structured data that powers your agent (product catalogs, FAQ entries, appointment slots, etc.). Collections are created automatically when you add the first record.

```python
# List all collections
collections = admin.data.collections()
for c in collections:
    print(f"{c['name']}: {c['recordCount']} records")

# Add a record
admin.data.add("products", {
    "name": "Premium Widget",
    "price": 29.99,
    "category": "gadgets",
})

# List records
products = admin.data.list("products", limit=50)
for p in products:
    print(p["name"], p["price"])

# Update a record
admin.data.update("products", "rec_abc123", {
    "name": "Premium Widget v2",
    "price": 34.99,
})

# Delete a single record
admin.data.delete("products", "rec_abc123")

# Clear all records in a collection
admin.data.clear("products")
```

### Broadcasting (`admin.broadcast`)

Send a vibe to all users who have enabled your agent.

```python
# Simple broadcast
admin.broadcast("We just launched a new feature!")

# With options (e.g. scheduling)
admin.broadcast(
    "Weekend sale starts now!",
    options={"schedule": "2026-04-20T10:00:00Z"},
)
```

See [Rosa's Bakery morning_update.py](../examples/rosas_bakery/morning_update.py) for a complete broadcasting example.

### Testing (`admin.test`)

Simulate user conversations to test your agent before going live.

```python
# Send a test message and get the agent's response
response = admin.test.chat("What services do you offer?")
print(response["reply"])

# Multi-turn conversation
admin.test.chat("Tell me about pricing")
admin.test.chat("Do you have a free tier?")

# Reset test state (clear conversation history)
admin.test.reset()
```

## Error Handling

All methods raise typed exceptions from `zinq_agent.exceptions`:

```python
from zinq_agent import ZinqMarketplaceAdmin, AuthenticationError, ZinqError

try:
    admin = ZinqMarketplaceAdmin(api_key="bad_key")
    admin.agent.status()
except AuthenticationError:
    print("Invalid business API key")
except ZinqError as e:
    print(f"API error ({e.status_code}): {e.message}")
```

## Environment Variable

Set `ZINQ_BIZ_KEY` so you don't have to pass the key in code:

```bash
export ZINQ_BIZ_KEY=zbk_your_key_here
```

```python
admin = ZinqMarketplaceAdmin()  # reads from env
```

## What businesses are building

| Industry | Use Case | Example |
|----------|----------|---------|
| Barber shops, salons, spas | Appointment booking and reminders | [Joe's Barber](../examples/joes_barber/) |
| Bakeries, restaurants, cafes | Ordering, daily specials, reservations | [Rosa's Bakery](../examples/rosas_bakery/) |
| Nutritionists, therapists, coaches | Consultations, intake forms, follow-ups | [Dr. Sarah](../examples/dr_sarah_nutrition/) |
| Plumbers, electricians, cleaners | Service quotes and scheduling | Adapt Joe's Barber |
| Fashion designers, artists | Personal shopping and commissions | Adapt Dr. Sarah |
| Tutors, music teachers | Lesson scheduling and progress tracking | Adapt Joe's Barber |
