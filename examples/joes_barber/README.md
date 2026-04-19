# Joe's Barber Shop

A complete marketplace agent example for a barber shop. Customers book haircuts, check availability, and cancel appointments -- all through chat on Zinq.

## What this demonstrates

- **Appointment booking** with conflict detection and slot management
- **Service menu** stored in data collections
- **YAML agent definition** with tool calls for Gemini
- **ZinqBusinessWebhook** for routing tool-call actions to Python handlers
- **ZinqMarketplaceAdmin** for managing data and replying to conversations

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Agent definition -- personality, services, tools, hours |
| `server.py` | Webhook server -- handles check_availability, book_appointment, cancel_appointment |

## Prerequisites

- Python 3.10+
- A Zinq business account (get one at [zinq-app.com/business](https://zinq-app.com/business))
- Your `ZINQ_BIZ_KEY` and `ZINQ_WEBHOOK_SECRET` from the dashboard

## Setup

1. Install dependencies:

```bash
pip install zinq-agent[webhook]
```

2. Set environment variables:

```bash
export ZINQ_BIZ_KEY="zbk_your_key_here"
export ZINQ_WEBHOOK_SECRET="zws_your_secret_here"
```

3. Deploy the agent definition:

```bash
python -c "
from zinq_agent import ZinqMarketplaceAdmin
admin = ZinqMarketplaceAdmin()
result = admin.agent.deploy(open('agent.yaml').read())
print(f'Deployed: {result}')
"
```

4. Start the webhook server:

```bash
python server.py
```

5. Expose your local server (for development):

```bash
# Using ngrok
ngrok http 8080

# Then update your webhook URL in the Zinq dashboard
```

## Local development

For local testing without signature verification:

```bash
export DEV_MODE=1
python server.py
```

Test with curl:

```bash
# Simulate a check_availability action
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "vibe.received",
    "deliveryId": "test-001",
    "timestamp": "2026-04-19T10:00:00Z",
    "agent": {"id": 1, "name": "Joe'\''s Barber Shop"},
    "user": {"id": 42, "name": "Test User"},
    "data": {
      "vibeId": 1,
      "type": "text",
      "text": "__action__:check_availability:{\"date\": \"2026-04-25\"}",
      "createdAt": "2026-04-19T10:00:00Z"
    }
  }'
```

## Sample conversation

```
Customer: Hey, I need a haircut this Saturday
Agent:    Let me check what's available on Saturday for you.
          [calls check_availability with date=2026-04-25]

Agent:    Great news! Saturday April 25 has plenty of openings.
          Here are some available times:
          - 8:00 AM
          - 8:30 AM
          - 9:00 AM
          - 9:30 AM
          - 10:00 AM
          What time works for you?

Customer: 10 AM, classic haircut. Name's Mike.
Agent:    [calls book_appointment with date, time, service, customer_name]

Agent:    You're all set, Mike! Here's your booking:
            Service: Classic Haircut
            Date: Saturday, April 25
            Time: 10:00 AM
            Price: $30
            Appointment ID: JB-1001
          See you then!

Customer: Actually, I need to cancel that.
Agent:    [calls cancel_appointment with appointment_id=JB-1001]

Agent:    Done -- appointment JB-1001 has been cancelled.
          Hope to see you again soon!
```

## Production deployment

For production, use gunicorn instead of the Flask dev server:

```bash
pip install gunicorn

# Create a wsgi.py file:
# from server import webhook
# app = webhook.create_flask_app()

gunicorn wsgi:app --bind 0.0.0.0:8080 --workers 2
```

## Customization

- Edit `agent.yaml` to change the personality, services, and pricing
- Edit `SHOP_HOURS` in `server.py` to match your actual hours
- Replace the in-memory `appointments` dict with a real database (SQLite, PostgreSQL, etc.)
- Add a Google Calendar integration for real availability checking
