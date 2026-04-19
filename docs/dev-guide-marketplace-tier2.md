# Marketplace Tier 2: Connected Agent

Build a marketplace agent with a webhook server that connects to your business systems -- Google Calendar, Stripe, your database, inventory, anything with an API.

**Time to published agent: 1 hour.**

---

## Overview

A Tier 2 agent has everything from Tier 1 (YAML definition, data collections, broadcasts) plus a webhook server that handles tool calls. When a customer says "book me a haircut at 10am", Gemini extracts the parameters and calls your webhook. You run the logic (check calendar, create booking, charge payment) and return the result.

```
Customer on Zinq
      |
      v
Zinq Platform (Gemini AI)
      |
      |-- reads your YAML for personality + tools
      |-- extracts parameters from user messages
      |
      v
Your Webhook Server (ZinqBusinessWebhook)
      |
      |-- @webhook.action("book_appointment")
      |-- @webhook.action("check_availability")
      |
      v
Your Business Logic (database, calendar, Stripe, etc.)
```

You manage everything through the `ZinqMarketplaceAdmin` Python SDK. There is no web dashboard.

---

## Prerequisites

Before starting, complete [Marketplace Tier 1](dev-guide-marketplace-tier1.md) steps 1-8. You should already have:

- The SDK installed (`pip install zinq-agent[webhook]`)
- A business API key (`ZINQ_BIZ_KEY`)
- A working YAML definition
- A tested agent (via `admin.test.chat()`)

## Step 1: Define Tools in Your YAML

Tools are actions the AI can invoke. Define them in your `agent.yaml`:

```yaml
name: "Joe's Barber Shop"
tagline: "Classic cuts, no wait"

personality: |
  You are Joe, a friendly neighborhood barber. Keep it casual.
  When a customer wants to book, collect their name, preferred
  date, and service type before calling the tool.

services:
  - name: "Classic Haircut"
    price: 30
    duration_minutes: 30
  - name: "Beard Trim"
    price: 20
    duration_minutes: 15
  - name: "Hot Shave"
    price: 35
    duration_minutes: 45

tools:
  - name: check_availability
    description: "Check available appointment slots for a given date"
    parameters:
      - name: date
        type: string
        required: true
        description: "Date in YYYY-MM-DD format"

  - name: book_appointment
    description: "Book an appointment"
    parameters:
      - name: date
        type: string
        required: true
      - name: time
        type: string
        required: true
        description: "Time in HH:MM format (24h)"
      - name: service
        type: string
        required: true
      - name: customer_name
        type: string
        required: true

  - name: cancel_appointment
    description: "Cancel an existing appointment"
    parameters:
      - name: appointment_id
        type: string
        required: true

webhook_url: "https://your-server.com/webhook"
```

## Step 2: Write Your Webhook Server

```python
# server.py
import os
from datetime import datetime
from zinq_agent import ZinqMarketplaceAdmin
from zinq_agent.webhook import ZinqBusinessWebhook

admin = ZinqMarketplaceAdmin()
webhook = ZinqBusinessWebhook(
    secret=os.environ["ZINQ_WEBHOOK_SECRET"],
    admin=admin,
)

# In-memory store (use a real database in production)
appointments = {}
next_id = 1000

SHOP_HOURS = {
    "start": 8,   # 8 AM
    "end": 18,    # 6 PM
    "slot_minutes": 30,
}


@webhook.action("check_availability")
def check_availability(params, session_id):
    """Check open slots for a date."""
    date_str = params["date"]
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    if date.weekday() == 6:  # Sunday
        return {"available": False, "message": "We're closed on Sundays."}

    # Find booked slots
    booked = set()
    for appt in appointments.values():
        if appt["date"] == date_str:
            booked.add(appt["time"])

    # Generate available slots
    slots = []
    for hour in range(SHOP_HOURS["start"], SHOP_HOURS["end"]):
        for minute in (0, 30):
            time_str = f"{hour:02d}:{minute:02d}"
            if time_str not in booked:
                slots.append(time_str)

    return {
        "available": len(slots) > 0,
        "date": date_str,
        "slots": slots[:8],  # Show first 8
        "total_available": len(slots),
    }


@webhook.action("book_appointment")
def book_appointment(params, session_id):
    """Book an appointment slot."""
    global next_id

    appointment_id = f"JB-{next_id}"
    next_id += 1

    appointments[appointment_id] = {
        "id": appointment_id,
        "date": params["date"],
        "time": params["time"],
        "service": params["service"],
        "customer": params["customer_name"],
        "session_id": session_id,
    }

    return {
        "confirmed": True,
        "appointment_id": appointment_id,
        "date": params["date"],
        "time": params["time"],
        "service": params["service"],
    }


@webhook.action("cancel_appointment")
def cancel_appointment(params, session_id):
    """Cancel an appointment."""
    appt_id = params["appointment_id"]

    if appt_id not in appointments:
        return {"error": f"Appointment {appt_id} not found."}

    del appointments[appt_id]
    return {"cancelled": True, "appointment_id": appt_id}


@webhook.on("agent.wave")
def greet(event):
    """Send a custom greeting when someone opens the chat."""
    admin.conversations.reply(
        str(event.user.id),
        "Welcome to Joe's! Need a cut, trim, or shave?",
    )


if __name__ == "__main__":
    # Deploy the YAML definition
    admin.agent.deploy(open("agent.yaml").read())
    print("Starting webhook server on port 8080...")
    webhook.start(port=8080)
```

## Step 3: Test Locally

```bash
export ZINQ_BIZ_KEY=zbk_your_key
export ZINQ_WEBHOOK_SECRET=zws_your_secret

# Start the server
python server.py
```

In another terminal, test with `admin.test.chat()`:

```python
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin()

# This will trigger tool calls to your webhook server
response = admin.test.chat("Do you have anything open next Saturday?")
print(response["reply"])

response = admin.test.chat("Book me at 10am, classic haircut, name is Mike")
print(response["reply"])

response = admin.test.chat("Cancel appointment JB-1000")
print(response["reply"])
```

### Testing the webhook directly with curl

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "vibe.received",
    "deliveryId": "test-001",
    "timestamp": "2026-04-19T10:00:00Z",
    "agent": {"id": 1, "name": "Test"},
    "user": {"id": 42, "name": "Test User"},
    "data": {
      "vibeId": 1,
      "type": "TEXT",
      "text": "I need a haircut",
      "createdAt": "2026-04-19T10:00:00Z"
    }
  }'
```

For local testing, skip signature verification:

```python
webhook = ZinqBusinessWebhook(
    secret="dev",
    admin=admin,
    skip_signature_check=True,  # DEV ONLY
)
```

## Step 4: Register Your Webhook URL

During development, use ngrok to expose your local server:

```bash
ngrok http 8080
# Copy the HTTPS URL (e.g., https://abc123.ngrok-free.app)
```

Register it via the SDK:

```python
admin.agent.set_webhook("https://abc123.ngrok-free.app/webhook")
```

For production, use your server's real URL:

```python
admin.agent.set_webhook("https://my-server.com/webhook")
```

## Step 5: Deploy Your Webhook Server

Your webhook server is a Python HTTP server. Deploy it the same way you would deploy any web application.

### Quick deployment with Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py agent.yaml ./
EXPOSE 8080
CMD ["python", "server.py"]
```

```bash
docker build -t joes-barber-agent .
docker run -d \
  -p 8080:8080 \
  -e ZINQ_BIZ_KEY=zbk_your_key \
  -e ZINQ_WEBHOOK_SECRET=zws_your_secret \
  --restart unless-stopped \
  joes-barber-agent
```

### Production: use gunicorn

```python
# wsgi.py
from server import webhook
app = webhook.create_flask_app()
```

```bash
pip install gunicorn
gunicorn wsgi:app --bind 0.0.0.0:8080 --workers 1
```

Use `--workers 1` to avoid duplicate processing. If you need multiple workers, make your handlers idempotent.

See [deployment.md](deployment.md) for full guides (GCloud, AWS, Railway, Render, Fly.io).

## Step 6: Publish

```python
admin.agent.publish()
# {"status": "pending_review", "estimated_review_time": "24-48 hours"}
```

---

## Monitoring Conversations

View and manage conversations through the SDK:

```python
# List all conversations
all_convos = admin.conversations.list(limit=20)

# Filter by status
awaiting = admin.conversations.list(status="awaiting_human")
print(f"{len(awaiting)} conversations need attention")

# Read a conversation
convo = admin.conversations.get("sess_abc123")
for msg in convo["messages"]:
    print(f"  [{msg['role']}] {msg['text']}")

# Reply to an escalated conversation
admin.conversations.reply("sess_abc123", "Your appointment is confirmed!")

# Hand back to AI
admin.conversations.resume_ai("sess_abc123")
```

### Automated monitoring script

```python
# monitor.py -- run every few minutes via cron
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin()

awaiting = admin.conversations.list(status="awaiting_human")
if awaiting:
    print(f"{len(awaiting)} conversations need attention:")
    for c in awaiting:
        convo = admin.conversations.get(c["sessionId"])
        last_msg = convo["messages"][-1]
        print(f"  {c['sessionId']}: {last_msg['text'][:80]}")
else:
    print("No conversations need attention.")

admin.close()
```

---

## Debugging Tool Calls

When a tool call fails, the AI tells the customer something went wrong. To debug:

### 1. Check your webhook server logs

Your server.py should log incoming requests:

```python
@webhook.action("book_appointment")
def book_appointment(params, session_id):
    print(f"book_appointment called: params={params}, session={session_id}")
    # ... your logic ...
```

### 2. Test individual actions with curl

```bash
# Simulate a tool call
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "action.invoked",
    "action": "check_availability",
    "params": {"date": "2026-04-25"},
    "sessionId": "test-session"
  }'
```

### 3. Verify your YAML tool definitions match your handlers

The `name` in YAML must match the string in `@webhook.action("name")`. If they do not match, the tool call silently fails.

### 4. Test the full flow

```python
admin.test.reset()
response = admin.test.chat("Book me for Saturday at 10am, name is Test")
print(response)
# Check if tool_calls appear in the response metadata
```

---

## Advanced Patterns

### Human handoff

When the AI encounters something it cannot handle, escalate to a human:

```yaml
# In agent.yaml
escalation_rules:
  - trigger: "wedding cake"
    reason: "Wedding cakes need personal consultation"
  - trigger: "complaint"
    reason: "Complaints need human attention"
```

On your side, poll for escalated conversations:

```python
awaiting = admin.conversations.list(status="awaiting_human")
for c in awaiting:
    # Read, decide, reply
    admin.conversations.reply(c["sessionId"], "Let me help you personally...")
```

### External API integration

Connect your webhook to any external service:

```python
import requests

@webhook.action("check_availability")
def check_availability(params, session_id):
    # Call Google Calendar API
    response = requests.get(
        "https://www.googleapis.com/calendar/v3/freeBusy",
        headers={"Authorization": f"Bearer {GOOGLE_TOKEN}"},
        json={"timeMin": params["date"] + "T08:00:00Z",
              "timeMax": params["date"] + "T18:00:00Z"},
    )
    # Parse and return available slots
    return {"slots": parse_free_slots(response.json())}
```

### Payment processing

```python
import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

@webhook.action("process_payment")
def process_payment(params, session_id):
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(params["amount"] * 100),
            currency="usd",
            description=params["description"],
        )
        return {"success": True, "payment_id": intent.id}
    except stripe.error.CardError as e:
        return {"success": False, "error": str(e)}
```

---

## Common Pitfalls

### 1. Webhook URL not reachable

During development, your `localhost` is not reachable by Zinq's servers. Use ngrok or deploy to a cloud server. Register the URL via the SDK:

```python
admin.agent.set_webhook("https://abc123.ngrok-free.app/webhook")
```

### 2. Tool name mismatch

The `name` in your YAML tools must exactly match the `@webhook.action()` decorator:

```yaml
# YAML
tools:
  - name: check_availability  # <-- this name
```

```python
# Python
@webhook.action("check_availability")  # <-- must match
def check_availability(params, session_id):
```

### 3. Returning errors without context

When a tool call fails, return a useful error message that the AI can relay to the customer:

```python
@webhook.action("book_appointment")
def book(params, session_id):
    if params["time"] not in available_slots:
        # Good: specific error the AI can explain
        return {"error": f"Sorry, {params['time']} is already booked. Try 10:30 or 11:00."}

    # Bad: generic error
    # return {"error": "Failed"}
```

### 4. Not handling webhook replay

Zinq may retry webhook delivery if your server does not respond. Make your handlers idempotent:

```python
processed_deliveries = set()

@webhook.on("vibe.received")
def handle(event):
    if event.delivery_id in processed_deliveries:
        return  # Already processed
    processed_deliveries.add(event.delivery_id)
    # ... handle event ...
```

### 5. Skipping signature verification in production

Never do this:

```python
# ONLY for local development
webhook = ZinqBusinessWebhook(secret="dev", admin=admin, skip_signature_check=True)
```

In production, always verify signatures:

```python
webhook = ZinqBusinessWebhook(
    secret=os.environ["ZINQ_WEBHOOK_SECRET"],
    admin=admin,
)
```

---

## Next Steps

- [Business Agents reference](business-agents.md) -- full `ZinqMarketplaceAdmin` and `ZinqBusinessWebhook` docs.
- [Webhooks guide](webhooks.md) -- event types, signature verification, framework integration.
- [Deployment guide](deployment.md) -- production deployment for your webhook server.
- [Examples](../examples/) -- complete working agents:
  - [Joe's Barber Shop](../examples/joes_barber/) -- appointment booking
  - [Rosa's Bakery](../examples/rosas_bakery/) -- ordering and broadcasts
  - [Dr. Sarah Nutrition](../examples/dr_sarah_nutrition/) -- consultations with safety guardrails
