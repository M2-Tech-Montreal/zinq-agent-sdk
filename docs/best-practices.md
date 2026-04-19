# Best Practices

Tips for building agents that are reliable, respectful, and pleasant to use.

## Keep Vibes Concise

Nobody wants a wall of text on their phone. Keep your vibes short and scannable.

```python
# Good -- short and actionable
agent.vibes.send(text="Time for your afternoon walk! 20 min around the block.")

# Bad -- too much text
agent.vibes.send(
    text="Based on my analysis of your recent diary entries and fitness goals, "
    "I've determined that the optimal time for cardiovascular exercise is now. "
    "Research suggests that a 20-minute walk at a moderate pace can improve "
    "your metabolic rate by up to 15% and reduce stress hormones by..."
)
```

If you need to send a lot of information, break it into multiple vibes or use a summary with a "show more" button:

```python
agent.vibes.send(
    text="Your weekly fitness summary is ready. 4 workouts, 2 rest days.",
    buttons=[
        {"label": "Show Details", "value": "weekly_detail"},
        {"label": "Sounds Good", "value": "dismiss"},
    ],
)
```

## Use Interactive Vibes

Buttons and choices make it easier for users to respond. They also give you structured data instead of free text that you'd need to parse.

```python
# Good -- structured response
agent.vibes.send(
    text="How was your sleep last night?",
    input_type="rating",
)

# Good -- predefined options
agent.vibes.send(
    text="What should we focus on today?",
    input_type="choice",
    options=["Workout plan", "Meal ideas", "Check progress", "Just chat"],
)

# Less ideal -- free text that you have to parse
agent.vibes.send(text="How was your sleep? Rate it 1-5.")
```

## Remember User Preferences

Use memories to avoid asking the same questions twice. Users appreciate agents that learn.

```python
@webhook.on("vibe.received")
def handle(event):
    text = event.data.text or ""

    # Check if we already know this
    diet = agent.memories.get("diet_preference")
    if diet:
        # Use the saved preference
        messages = [
            {"role": "system", "content": f"User is {diet.value}."},
            {"role": "user", "content": text},
        ]
    else:
        # Ask and save for later
        if "vegetarian" in text.lower() or "vegan" in text.lower():
            agent.memories.save(key="diet_preference", value=text, category="food")
            agent.vibes.send(text="Got it, I'll remember that!")
            return
```

### Organize memories with categories

```python
# Group related memories
agent.memories.save(key="diet", value="vegetarian", category="food")
agent.memories.save(key="allergies", value="nuts", category="food")
agent.memories.save(key="workout_time", value="morning", category="fitness")
agent.memories.save(key="fitness_level", value="intermediate", category="fitness")

# Retrieve by category
food_prefs = agent.memories.list(category="food")
fitness_prefs = agent.memories.list(category="fitness")
```

## Handle Errors Gracefully

Your agent should never crash silently. If something goes wrong, send a friendly message to the user.

```python
@webhook.on("vibe.received")
def handle(event):
    try:
        # Your main logic
        response = agent.gemini.chat(messages=[...])
        agent.vibes.send(text=response.text)

    except InsufficientCreditsError:
        # User-facing explanation
        agent.vibes.send(
            text="I'd love to help, but you're out of AI credits this month. "
            "They reset on the 1st!"
        )

    except RateLimitError as e:
        # Don't spam retries -- just acknowledge
        agent.vibes.send(text="I'm a bit overwhelmed right now. Try again in a minute?")

    except Exception as e:
        # Catch-all -- log for debugging, send friendly message
        print(f"Unexpected error: {e}")
        agent.vibes.send(text="Something went wrong on my end. Try again?")
```

### Never swallow exceptions silently

```python
# Bad -- error disappears, agent seems broken
try:
    result = do_something()
except Exception:
    pass

# Good -- log it and tell the user
try:
    result = do_something()
except Exception as e:
    print(f"do_something failed: {e}")
    agent.vibes.send(text="Hit a snag, but I'm still here. Try again?")
```

## Respect Rate Limits

The Zinq API has rate limits to protect both the platform and users. Be a good citizen:

```python
import time
from zinq_agent import RateLimitError

def send_with_backoff(text, max_retries=3):
    """Send a vibe with automatic retry on rate limit."""
    for attempt in range(max_retries):
        try:
            return agent.vibes.send(text=text)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                print(f"Rate limited, waiting {e.retry_after}s...")
                time.sleep(e.retry_after)
            else:
                raise
```

### Don't send too many vibes at once

```python
# Bad -- 50 vibes in a burst
for item in items:
    agent.vibes.send(text=f"Item: {item}")

# Good -- batch into one vibe
summary = "\n".join(f"- {item}" for item in items)
agent.vibes.send(text=f"Here are your items:\n{summary}")
```

## Monitor Credit Usage

Gemini calls use credits from the user's account. Be transparent about usage and check before expensive operations.

```python
def check_credits_before_ai(min_credits=5):
    """Check if the user has enough credits for an AI call."""
    ctx = agent.user.context()
    remaining = ctx.credit_status.credits_remaining

    if remaining < min_credits:
        agent.vibes.send(
            text=f"You have {remaining} credits left. "
            f"AI responses need about {min_credits}. "
            f"Credits reset on {ctx.credit_status.reset_date.strftime('%b %d')}."
        )
        return False
    return True


@webhook.on("vibe.received")
def handle(event):
    if check_credits_before_ai():
        response = agent.gemini.chat(messages=[...])
        agent.vibes.send(text=response.text)
```

### Choose the right model

```python
# Use "flash" for simple tasks (cheaper, faster)
response = agent.gemini.chat(messages=[...], model="flash")

# Use "pro" only when you need higher quality (more expensive)
response = agent.gemini.chat(messages=[...], model="pro")
```

## Respect Notification Preferences

Check the user's preferred notification hours before sending vibes:

```python
from datetime import datetime
import pytz

def is_notification_ok():
    """Check if it's within the user's preferred notification hours."""
    ctx = agent.user.context()

    if not ctx.agent_preferences or not ctx.agent_preferences.notification_hours:
        return True  # No preference set, default to OK

    hours = ctx.agent_preferences.notification_hours
    tz = pytz.timezone(ctx.timezone)
    current_hour = datetime.now(tz).hour

    return hours.start <= current_hour <= hours.end


# Use before sending non-urgent vibes
if is_notification_ok():
    agent.vibes.send(text="Time for your afternoon check-in!")
else:
    # Save for later
    agent.memories.save(key="pending_vibe", value="afternoon check-in")
```

## Test Locally Before Deploying

### Use skip_signature_check for local testing

```python
# Local development
webhook = ZinqWebhook(secret="dev", skip_signature_check=True)

# Production
webhook = ZinqWebhook(secret=os.environ["ZINQ_WEBHOOK_SECRET"])
```

### Test with curl

```bash
# Send a fake webhook event to your local server
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "vibe.received",
    "deliveryId": "test_123",
    "timestamp": "2026-04-19T12:00:00Z",
    "agent": {"id": 1, "name": "Test"},
    "user": {"id": 42, "name": "Alex", "timezone": "America/New_York"},
    "data": {
      "vibeId": 1,
      "type": "TEXT",
      "text": "Hello test!",
      "createdAt": "2026-04-19T12:00:00Z"
    }
  }'
```

### Check the health endpoint

```bash
curl http://localhost:8080/health
# {"status": "ok"}
```

## Use Context Managers

Always use `with` or `async with` to ensure connections are properly closed:

```python
# Good -- connection is closed automatically
with ZinqAgent() as agent:
    agent.vibes.send(text="Hello!")

# Good -- async variant
async with AsyncZinqAgent() as agent:
    await agent.vibes.send(text="Hello!")

# OK but easy to forget -- remember to call close()
agent = ZinqAgent()
try:
    agent.vibes.send(text="Hello!")
finally:
    agent.close()
```

## Structure Your Agent Code

As your agent grows, keep it organized:

```python
"""My Agent -- a well-structured Zinq agent."""

import os
from zinq_agent import ZinqAgent, ZinqWebhook, InsufficientCreditsError

# --- Config ---
agent = ZinqAgent(api_key=os.environ["ZINQ_API_KEY"])
webhook = ZinqWebhook(secret=os.environ["ZINQ_WEBHOOK_SECRET"])

# --- Helpers ---

def get_context():
    """Build context for AI calls."""
    # ...

def process_command(text):
    """Handle structured commands."""
    # ...

# --- Event Handlers ---

@webhook.on("vibe.received")
def handle_vibe(event):
    # ...

@webhook.on("agent.wave")
def greet(event):
    # ...

@webhook.on("vibe.reply")
def handle_reply(event):
    # ...

# --- Entry Point ---

if __name__ == "__main__":
    webhook.start(port=int(os.environ.get("PORT", 8080)))
```

## Common Pitfalls

### 1. Forgetting to handle voice vibes

Voice vibes have `transcript` but might not have `text`. Always check both:

```python
content = event.data.transcript or event.data.text or "(empty vibe)"
```

### 2. Sending vibes in a webhook handler that calls Gemini

Gemini calls can be slow (2-5 seconds). This is fine -- Zinq waits for your webhook response and doesn't re-send.

### 3. Not handling the `is_first_wave` flag

The `agent.wave` event tells you if it's the user's first time. Send an intro for new users:

```python
@webhook.on("agent.wave")
def greet(event):
    if event.data.is_first_wave:
        agent.vibes.send(text="Welcome! Here's how I work...")
    else:
        agent.vibes.send(text="Hey again!")
```

### 4. Hardcoding the API key

Always use environment variables:

```python
# Bad
agent = ZinqAgent(api_key="zak_actual_secret_key")

# Good
agent = ZinqAgent()  # reads ZINQ_API_KEY from environment
```

### 5. Not closing the client

If you're running a one-shot script (not a long-running server), close the client:

```python
with ZinqAgent() as agent:
    agent.vibes.send(text="One-shot message!")
# Automatically closed
```
