# Webhooks

Webhooks let your agent receive real-time events when the user interacts with it in the Zinq app. Without webhooks, your agent would need to poll for new vibes -- webhooks are faster and more efficient.

## How Webhooks Work

1. The user sends a vibe to your agent in the Zinq app
2. Zinq's backend sends an HTTP POST to your webhook URL
3. Your agent processes the event and (optionally) responds

```
User's Phone                Zinq Backend                 Your Agent
    |                           |                            |
    |--- sends vibe ----------->|                            |
    |                           |--- POST /webhook --------->|
    |                           |                            |-- process event
    |                           |                            |-- send reply vibe
    |                           |<--- POST /vibes/send ------|
    |<--- push notification ----|                            |
```

## Setup

### Step 1: Get Your Credentials

When you create your agent in the Zinq app, you get:

- **API Key** (`zak_...`) -- for making API calls

> **Note:** Webhook signing secrets (`zws_...`) are not yet available. Use `skip_signature_check=True` during development. HMAC-SHA256 signature verification will be added in a future release.

### Step 2: Install Webhook Support

```bash
pip install zinq-agent[webhook]
```

This adds Flask as a dependency for the built-in webhook server.

### Step 3: Write Your Webhook Handler

```python
import os
from zinq_agent import ZinqAgent, ZinqWebhook

agent = ZinqAgent(api_key=os.environ["ZINQ_API_KEY"])
webhook = ZinqWebhook(secret="dev", skip_signature_check=True)  # Signature verification coming soon

@webhook.on("vibe.received")
def handle_vibe(event):
    text = event.data.transcript or event.data.text or ""
    agent.vibes.send(text=f"You said: {text}")

@webhook.on("agent.wave")
def greet(event):
    if event.data.is_first_wave:
        agent.vibes.send(text="Hey! I'm your agent. Nice to meet you.")
    else:
        agent.vibes.send(text="Welcome back!")

webhook.start(port=8080)
```

### Step 4: Configure Your Webhook URL

In the Zinq app, go to **My Agents** and set your webhook URL:

- Local development: `http://localhost:8080/webhook` (requires a tunnel -- see below)
- Production: `https://your-server.com/webhook`

### Step 5: Expose Your Local Server (Development)

During development, your agent runs on `localhost`, which Zinq's servers can't reach. Use a tunnel:

```bash
# Using ngrok (free tier works fine)
ngrok http 8080

# Copy the https URL (e.g., https://abc123.ngrok-free.app)
# Set your webhook URL to: https://abc123.ngrok-free.app/webhook
```

Other tunnel options: [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/), [localtunnel](https://theboroer.github.io/localtunnel-www/), [bore](https://github.com/ekzhang/bore).

## Event Types

### `vibe.received`

Fired when the user sends a vibe (message) to the agent.

```python
@webhook.on("vibe.received")
def handle_vibe(event):
    data = event.data  # VibeReceivedData

    print(f"Vibe ID: {data.vibe_id}")
    print(f"Type: {data.type}")              # "TEXT", "VIDEO", "VOICE", "PHOTO"
    print(f"Text: {data.text}")              # Text content (may be None for media)
    print(f"Transcript: {data.transcript}")  # Voice/video transcript
    print(f"Media URL: {data.media_url}")    # URL to media file
    print(f"Duration: {data.duration}")      # Media duration in seconds
```

**Tip:** Voice vibes have a `transcript` but may not have `text`. Always check both:

```python
content = event.data.transcript or event.data.text or "(empty)"
```

### `charm.received`

Fired when the user reacts to a vibe with a charm (emoji reaction).

```python
@webhook.on("charm.received")
def handle_charm(event):
    data = event.data  # CharmReceivedData

    print(f"Charm: {data.emoji}")        # e.g., "thumbs_up", "heart"
    print(f"On vibe: {data.vibe_id}")    # The vibe they reacted to
```

### `agent.wave`

Fired when the user opens the agent chat in the Zinq app. Use this to send a greeting or show a menu.

```python
@webhook.on("agent.wave")
def handle_wave(event):
    data = event.data  # AgentWaveData

    if data.is_first_wave:
        # First time the user opens this agent
        agent.vibes.send(text="Welcome! Here's what I can do...")
    else:
        # Returning user
        time_away = data.last_interaction_at  # datetime or None
        agent.vibes.send(text="Welcome back!")
```

### `vibe.reply`

Fired when the user replies to an agent vibe, or taps a button on an interactive vibe.

```python
@webhook.on("vibe.reply")
def handle_reply(event):
    data = event.data  # VibeReplyData

    print(f"Reply to vibe: {data.reply_to_vibe_id}")
    print(f"Text: {data.text}")
    print(f"Button value: {data.button_value}")  # None if free text reply

    if data.button_value == "view_report":
        agent.vibes.send(text="Here's your report...")
    elif data.button_value == "remind_later":
        agent.memories.save(key="pending_reminder", value="report")
```

## Event Payload Structure

Every webhook event is a `WebhookEvent` object with these fields:

```python
@webhook.on("vibe.received")
def handler(event):
    event.event         # str: "vibe.received"
    event.delivery_id   # str: unique ID for deduplication
    event.timestamp     # datetime: when the event occurred
    event.agent.id      # int: your agent's ID
    event.agent.name    # str: your agent's name
    event.user.id       # int: the user's ID
    event.user.name     # str: the user's name
    event.user.timezone # str | None: "America/New_York"
    event.data          # typed data (varies by event type)
```

## Signature Verification

Every webhook request from Zinq includes two headers for security:

- `X-Zinq-Signature`: HMAC-SHA256 signature of the request body
- `X-Zinq-Timestamp`: Unix timestamp of when the request was sent

The SDK verifies these automatically. If verification fails, the request is rejected with a 401 response.

### How It Works

1. Zinq computes `HMAC-SHA256(webhook_secret, request_body)` and sends it as the signature
2. The SDK computes the same HMAC using your stored secret
3. If they match, the request is authentic
4. The timestamp is also checked -- requests older than 5 minutes are rejected (replay protection)

### Skip Verification (Development Only)

For local testing, you can skip signature verification:

```python
webhook = ZinqWebhook(secret="any_value", skip_signature_check=True)
```

**Never do this in production.** It allows anyone to send fake events to your webhook.

### Manual Verification

If you're using a web framework other than Flask, you can verify signatures manually:

```python
is_valid = webhook.verify_signature(
    payload=request.body,                          # raw bytes
    signature_header=request.headers["X-Zinq-Signature"],
    timestamp_header=request.headers.get("X-Zinq-Timestamp"),
)
```

## Using With Other Web Frameworks

The SDK includes a built-in Flask server, but you can use any framework. The `handle_request()` method is framework-agnostic.

### FastAPI

```python
from fastapi import FastAPI, Request
from zinq_agent import ZinqAgent, ZinqWebhook

app = FastAPI()
agent = ZinqAgent()
webhook = ZinqWebhook(secret="dev", skip_signature_check=True)

@webhook.on("vibe.received")
def handle_vibe(event):
    agent.vibes.send(text=f"You said: {event.data.text}")

@app.post("/webhook")
async def webhook_endpoint(request: Request):
    body = await request.body()
    headers = dict(request.headers)
    response_body, status_code = webhook.handle_request(body, headers)
    return {"ok": True}
```

### Django

```python
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from zinq_agent import ZinqAgent, ZinqWebhook

agent = ZinqAgent()
webhook = ZinqWebhook(secret="dev", skip_signature_check=True)

@webhook.on("vibe.received")
def handle_vibe(event):
    agent.vibes.send(text=f"You said: {event.data.text}")

@csrf_exempt
def webhook_view(request):
    body = request.body
    headers = {k: v for k, v in request.META.items() if k.startswith("HTTP_")}
    # Django uppercases and prefixes headers
    mapped_headers = {
        "X-Zinq-Signature": headers.get("HTTP_X_ZINQ_SIGNATURE", ""),
        "X-Zinq-Timestamp": headers.get("HTTP_X_ZINQ_TIMESTAMP"),
    }
    response_body, status_code = webhook.handle_request(body, mapped_headers)
    return JsonResponse(json.loads(response_body), status=status_code)
```

## Production with Gunicorn

For production deployments, use the `create_flask_app()` method with a production WSGI server:

```python
# my_agent.py
from zinq_agent import ZinqAgent, ZinqWebhook

agent = ZinqAgent()
webhook = ZinqWebhook(secret="dev", skip_signature_check=True)

@webhook.on("vibe.received")
def handle(event):
    agent.vibes.send(text=f"Got: {event.data.text}")

app = webhook.create_flask_app()
```

```bash
pip install gunicorn
gunicorn -b 0.0.0.0:8080 -w 1 my_agent:app
```

> **Important:** Use `-w 1` (single worker) unless your handler is stateless. Multiple workers mean multiple instances of your agent, which can lead to duplicate responses.

## Error Handling

If your handler raises an exception, the webhook server catches it, logs the error, and returns HTTP 200 to Zinq. This prevents Zinq from retrying the delivery (which would cause duplicate processing).

```python
@webhook.on("vibe.received")
def handle_vibe(event):
    try:
        # Your logic here
        process(event)
    except Exception as e:
        # Log the error and send a friendly message
        print(f"Error processing vibe: {e}")
        agent.vibes.send(text="Oops, something went wrong. Try again?")
```

## Health Check

The built-in server includes a health check endpoint at `/health`:

```bash
curl http://localhost:8080/health
# {"status": "ok"}
```

Use this for load balancer health checks or monitoring.

## Multiple Handlers

You can register multiple handlers for the same event type. They all run in order:

```python
@webhook.on("vibe.received")
def log_vibe(event):
    print(f"Received: {event.data.text}")

@webhook.on("vibe.received")
def respond_to_vibe(event):
    agent.vibes.send(text="Got it!")
```

Both `log_vibe` and `respond_to_vibe` will run for every `vibe.received` event.
