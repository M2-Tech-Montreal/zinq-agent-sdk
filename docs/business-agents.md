# Business Agents (Coming Soon)

> **Status:** Spec only — implementation follows marketplace launch. See [PR tracking](https://github.com/M2-Tech-Montreal/tap/pull/884).

## Overview

The Zinq Agent SDK supports two types of agents:

| Type | Who Builds It | Where It Runs | Who Uses It |
|------|--------------|---------------|-------------|
| **Personal Agent** | Developer for themselves | Developer's machine | One user |
| **Business Agent** | Business owner / consultant | Zinq's servers (AI loop) + developer's server (webhooks) | Many users |

**Personal agents** are fully supported today via `ZinqAgent`. **Business agents** will be supported via `ZinqBusinessClient` once the Zinq Marketplace launches.

## What is a Business Agent?

A business agent represents a real business on Zinq — a bakery, barber shop, restaurant, clothing brand, plumber, nutritionist. Customers enable the agent in the Zinq app and chat with it to browse products, book appointments, place orders, or ask questions.

The AI conversation loop runs on Zinq's servers (powered by Gemini). But when the AI needs to do something business-specific — check a calendar, process an order, look up inventory — it calls your server via webhooks. And when you need to reply manually (custom cake request, complex order), you do it through the business dashboard API.

```
Customer (Zinq app)
     ↕ vibes
Zinq Server (AI loop — Gemini)
     ↕ webhooks (tool calls)
Your Server (calendar, inventory, booking logic)
     ↕ dashboard API
Business Owner (web dashboard or SDK)
```

## ZinqBusinessClient (Planned)

```python
from zinq_agent import ZinqBusinessClient

biz = ZinqBusinessClient(api_key="zbk_xxxxx")
```

### Clients — See who's using your agent

```python
# List all clients who enabled your agent
clients = biz.clients.list()
for c in clients:
    print(f"{c.display_name} — enabled {c.enabled_at}")

# Client count
print(f"Total clients: {biz.clients.count()}")
```

### Conversations — Read and reply to customer chats

```python
# List conversations needing your attention
pending = biz.conversations.list(status="awaiting_human")
for convo in pending:
    print(f"{convo.client_name}: {convo.summary}")
    print(f"  Urgency: {convo.urgency}")
    print(f"  Last message: {convo.last_message}")

# Read full conversation history
history = biz.conversations.get(session_id="sess_abc123")
for msg in history.messages:
    print(f"  [{msg.sender}] {msg.text}")

# Reply to a customer (sent as a vibe from your agent)
biz.conversations.reply(
    session_id="sess_abc123",
    text="Your order is ready for pickup! See you at noon."
)

# Hand back to AI after your reply
biz.conversations.resume_ai(session_id="sess_abc123")
```

### Broadcasts — Send messages to all clients

```python
# Simple text broadcast
biz.broadcast("Fresh sourdough just came out of the oven!")

# Broadcast with action buttons
biz.broadcast(
    text="Empty slot at 3pm today! Want to come in?",
    options=["Book it", "Not today"]
)

# Check remaining broadcasts (rate limited: 2/day)
print(f"Broadcasts remaining today: {biz.broadcasts_remaining}")
```

### Data Management — Update your agent's data

```python
# Add today's specials
biz.data.add("daily_specials", {
    "name": "Blueberry Muffins",
    "price": 3.50,
    "notes": "Fresh batch at 7am"
})

# List all items in a collection
items = biz.data.list("menu_items")
for item in items:
    print(f"{item['name']} — ${item['price']}")

# Update an item
biz.data.update("menu_items", item_id="abc123", data={
    "price": 4.00  # price increase
})

# Clear collection (start fresh for tomorrow)
biz.data.clear("daily_specials")
```

### Webhook Handler — Receive tool calls from the AI

When the AI agent needs to do something on your server (check calendar, process payment), it calls your webhook:

```python
from zinq_agent import ZinqBusinessWebhook

webhook = ZinqBusinessWebhook(secret="zws_xxxxx")

@webhook.on_tool("check_availability")
def check_availability(params):
    date = params["date"]
    service = params["service"]
    # Check your Google Calendar, database, etc.
    slots = my_calendar.get_available(date, service)
    return {"slots": slots}

@webhook.on_tool("book_appointment")
def book_appointment(params):
    slot_id = params["slot_id"]
    # Book in your system
    booking = my_calendar.book(slot_id)
    return {"confirmed": True, "booking_id": booking.id}

@webhook.on_tool("request_human_review")
def human_needed(params):
    # Notification — business owner will reply via dashboard
    send_push_notification(f"Customer needs help: {params['summary']}")
    return {"acknowledged": True}

webhook.start(port=8080)
```

## Example: Rosa's Bakery Agent Server

Complete example of a bakery's webhook server:

```python
from zinq_agent import ZinqBusinessClient, ZinqBusinessWebhook
import os

biz = ZinqBusinessClient(api_key=os.environ["ZINQ_BIZ_KEY"])
webhook = ZinqBusinessWebhook(secret=os.environ["ZINQ_WEBHOOK_SECRET"])

@webhook.on_tool("check_availability")
def check_pickup_slots(params):
    """AI asks: can the customer pick up at this time?"""
    time = params.get("time")
    # Simple: bakery is open 7am-6pm
    hour = int(time.split(":")[0])
    available = 7 <= hour <= 18
    return {"available": available, "message": "We're open!" if available else "Sorry, we close at 6pm"}

@webhook.on_tool("request_pickup")
def handle_order(params):
    """Customer placed an order — notify Rosa"""
    items = params.get("items", "")
    pickup_time = params.get("pickup_time", "")

    # Send Rosa a vibe about the new order
    biz.conversations.reply(
        session_id=params.get("session_id"),
        text=f"New pickup order received: {items} at {pickup_time}. I'll have it ready!"
    )
    return {"confirmed": True}

# Morning routine: update today's specials
def update_specials():
    biz.data.clear("daily_specials")
    biz.data.add("daily_specials", {"name": "Sourdough Loaf", "price": 6.50})
    biz.data.add("daily_specials", {"name": "Croissants", "price": 3.50})
    biz.broadcast("Good morning! Fresh sourdough and croissants today.")

if __name__ == "__main__":
    update_specials()
    print("Rosa's bakery server running...")
    webhook.start(port=8080)
```

## Example: Maya's Kids Knits Agent Server

Complete example of an online fashion shop:

```python
from zinq_agent import ZinqBusinessClient, ZinqBusinessWebhook
import os

biz = ZinqBusinessClient(api_key=os.environ["ZINQ_BIZ_KEY"])
webhook = ZinqBusinessWebhook(secret=os.environ["ZINQ_WEBHOOK_SECRET"])

@webhook.on_tool("request_order")
def handle_order(params):
    """Customer wants to buy — Maya follows up personally"""
    items = params.get("items", "")
    # Maya will reply via dashboard with payment link
    return {"acknowledged": True, "message": "Maya will follow up with payment details!"}

@webhook.on_tool("request_custom")
def handle_custom(params):
    """Custom request — needs Maya's expertise"""
    description = params.get("description", "")
    return {"acknowledged": True, "message": "Maya will get back to you about this custom piece!"}

# Add new products
def add_product(name, price, sizes, photo_url):
    biz.data.add("products", {
        "name": name,
        "price": price,
        "sizes": sizes,
        "photo_url": photo_url,
        "available": True
    })

if __name__ == "__main__":
    print("Maya's knits server running...")
    webhook.start(port=8080)
```

## Comparison: Personal vs Business SDK

| Feature | `ZinqAgent` | `ZinqBusinessClient` |
|---------|------------|---------------------|
| **Import** | `from zinq_agent import ZinqAgent` | `from zinq_agent import ZinqBusinessClient` |
| **API key prefix** | `zak_` (agent key) | `zbk_` (business key) |
| **Send vibes** | `agent.vibes.send()` | `biz.conversations.reply()` |
| **Read diary** | `agent.diary.search()` | Not available (privacy) |
| **Memories** | `agent.memories.save()` | Managed by Zinq |
| **Gemini** | `agent.gemini.chat()` | Managed by Zinq |
| **Broadcasts** | Not applicable | `biz.broadcast()` |
| **Data management** | Not applicable | `biz.data.add/update/clear()` |
| **Client list** | Not applicable | `biz.clients.list()` |
| **Conversations** | Not applicable | `biz.conversations.list/reply()` |
| **Webhooks** | `ZinqWebhook` (receive vibes) | `ZinqBusinessWebhook` (receive tool calls) |
| **Runs on** | Your machine | Your machine (webhooks) + Zinq (AI loop) |

## Timeline

- **Now:** Personal agents via `ZinqAgent` — fully supported
- **Next:** Marketplace launch with YAML-based agent creation
- **Then:** `ZinqBusinessClient` for Tier 2 connected agents
