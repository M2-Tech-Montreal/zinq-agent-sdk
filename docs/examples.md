# Examples Cookbook

Copy-paste recipes for common agent patterns. Each example is a complete, runnable script.

## Table of Contents

- [Echo Bot](#echo-bot) -- Simplest possible agent
- [Daily Digest](#daily-digest) -- Scheduled summaries
- [Fitness Coach](#fitness-coach) -- Gemini + memories
- [Email Monitor](#email-monitor) -- IMAP + Zinq vibes
- [Slack Bridge](#slack-bridge) -- Forward Slack messages
- [Appointment Booker](#appointment-booker) -- Interactive booking
- [Personal Shopper](#personal-shopper) -- Product recommendations

---

## Echo Bot

The simplest possible agent. Echoes back whatever the user says. Good for testing your setup.

```python
"""Echo Bot -- repeats everything you say."""

import os
from zinq_agent import ZinqAgent, ZinqWebhook

agent = ZinqAgent(api_key=os.environ["ZINQ_API_KEY"])
webhook = ZinqWebhook(secret="dev", skip_signature_check=True  # Signature verification coming soon)


@webhook.on("vibe.received")
def echo(event):
    # Voice vibes have transcript; text vibes have text
    text = event.data.transcript or event.data.text or "(empty)"
    agent.vibes.send(text=f"You said: {text}")


@webhook.on("agent.wave")
def greet(event):
    if event.data.is_first_wave:
        agent.vibes.send(text="Hey! I'm Echo Bot. I repeat everything you say.")
    else:
        agent.vibes.send(text="Welcome back! Say something and I'll echo it.")


@webhook.on("charm.received")
def handle_charm(event):
    agent.vibes.send(text=f"You reacted with {event.data.emoji}")


if __name__ == "__main__":
    print("Starting Echo Bot on port 8080...")
    webhook.start(port=8080)
```

**Setup:**
```bash
pip install zinq-agent[webhook]
export ZINQ_API_KEY=zak_your_key
# ZINQ_WEBHOOK_SECRET — not yet available, use skip_signature_check=True
python echo_bot.py
```

---

## Daily Digest

A scheduled agent that sends a daily summary of the user's diary. Run it with cron or a task scheduler -- no webhooks needed.

```python
"""Daily Digest -- sends a morning summary of yesterday's diary entries."""

import os
from datetime import date, timedelta

from zinq_agent import ZinqAgent, InsufficientCreditsError

agent = ZinqAgent(api_key=os.environ["ZINQ_API_KEY"])


def build_digest():
    """Build a summary of yesterday's diary entries."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today = date.today().isoformat()

    entries = list(agent.diary.iter(start=yesterday, end=today))

    if not entries:
        return None

    # Group by AI tags
    tag_groups = {}
    for entry in entries:
        for tag in entry.ai_tags:
            tag_groups.setdefault(tag, []).append(entry)

    # Build summary text
    lines = [f"Your day yesterday ({yesterday}):"]
    lines.append(f"  {len(entries)} diary entries recorded")
    lines.append("")

    if tag_groups:
        lines.append("Highlights by topic:")
        for tag, tag_entries in sorted(tag_groups.items()):
            lines.append(f"  {tag}: {len(tag_entries)} entries")
            # Show the first entry as a preview
            preview = tag_entries[0].text or tag_entries[0].transcript or ""
            if len(preview) > 80:
                preview = preview[:77] + "..."
            lines.append(f"    \"{preview}\"")
        lines.append("")

    return "\n".join(lines)


def send_ai_summary(entries_text):
    """Use Gemini to generate a natural language summary."""
    try:
        response = agent.gemini.chat(
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the user's day in 2-3 friendly sentences. "
                    "Be warm and encouraging. Mention specific activities.",
                },
                {"role": "user", "content": entries_text},
            ],
            model="flash",
            max_tokens=200,
        )
        return response.text
    except InsufficientCreditsError:
        return None


def main():
    ctx = agent.user.context()
    print(f"Building digest for {ctx.name}...")

    digest = build_digest()
    if not digest:
        print("No entries yesterday, skipping.")
        return

    # Try AI summary first, fall back to structured digest
    ai_summary = send_ai_summary(digest)
    if ai_summary:
        agent.vibes.send(text=f"Good morning! Here's your daily digest:\n\n{ai_summary}")
    else:
        agent.vibes.send(text=f"Good morning! Here's your daily digest:\n\n{digest}")

    print("Digest sent!")
    agent.close()


if __name__ == "__main__":
    main()
```

**Setup:**
```bash
pip install zinq-agent
export ZINQ_API_KEY=zak_your_key

# Run once
python daily_digest.py

# Or schedule with cron (every day at 8am)
# 0 8 * * * cd /path/to/agent && python daily_digest.py
```

---

## Fitness Coach

An agent that acts as a personal fitness coach. Uses Gemini for AI responses and memories for tracking preferences.

```python
"""Fitness Coach -- AI-powered fitness companion."""

import os
from zinq_agent import ZinqAgent, ZinqWebhook, InsufficientCreditsError

agent = ZinqAgent(api_key=os.environ["ZINQ_API_KEY"])
webhook = ZinqWebhook(secret="dev", skip_signature_check=True  # Signature verification coming soon)

SYSTEM_PROMPT = """You are a friendly fitness coach inside the Zinq app.

Rules:
- Keep responses under 150 words
- Be encouraging, not preachy
- Give specific, actionable advice
- Reference the user's preferences and history when available
- Use plain language, no jargon
"""


def get_user_context():
    """Build context from memories and recent diary."""
    parts = []

    # Load saved preferences
    memories = agent.memories.list(category="fitness")
    if memories:
        prefs = "\n".join(f"- {m.key}: {m.value}" for m in memories)
        parts.append(f"User's fitness preferences:\n{prefs}")

    # Search recent diary for fitness entries
    results = agent.diary.search("workout exercise fitness", limit=5)
    if results.results:
        entries = "\n".join(
            f"- [{r.created_at.strftime('%b %d')}] {r.text}" for r in results.results
        )
        parts.append(f"Recent fitness diary entries:\n{entries}")

    return "\n\n".join(parts) if parts else "No fitness history yet."


@webhook.on("vibe.received")
def handle_message(event):
    text = event.data.transcript or event.data.text or ""
    lower = text.lower()

    # Save preferences
    if any(kw in lower for kw in ["i prefer", "my goal", "i usually", "i like to"]):
        key = "goal" if "goal" in lower else "preference"
        agent.memories.save(key=f"fitness_{key}", value=text, category="fitness")
        agent.vibes.send(text="Got it, I'll remember that!")
        return

    # Log a workout
    if any(kw in lower for kw in ["just did", "completed", "finished", "worked out"]):
        agent.memories.save(
            key=f"last_workout",
            value=text,
            category="fitness",
        )
        agent.vibes.send(
            text="Nice work! Keep it up.",
            input_type="choice",
            options=["What should I do tomorrow?", "Log another workout", "Show my history"],
        )
        return

    # AI response
    context = get_user_context()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"My fitness context:\n{context}"},
        {"role": "user", "content": text},
    ]

    try:
        response = agent.gemini.chat(messages=messages, model="flash")
        agent.vibes.send(text=response.text)
    except InsufficientCreditsError:
        agent.vibes.send(
            text="I'm out of AI credits this month, but I can still track your workouts! "
            "Just tell me what you did."
        )


@webhook.on("agent.wave")
def greet(event):
    ctx = agent.user.context()
    last_workout = agent.memories.get("last_workout")

    if event.data.is_first_wave:
        agent.vibes.send(
            text=f"Hey {ctx.name}! I'm your fitness coach. "
            "Tell me about your fitness goals and I'll help you stay on track.",
            input_type="choice",
            options=["Plan a workout", "Log a workout", "Get nutrition advice"],
        )
    elif last_workout:
        agent.vibes.send(
            text=f"Welcome back! Your last workout: {last_workout.value[:100]}. "
            "Ready for another one?"
        )
    else:
        agent.vibes.send(text=f"Hey {ctx.name}! What's on the fitness menu today?")


if __name__ == "__main__":
    print("Starting Fitness Coach on port 8080...")
    webhook.start(port=8080)
```

---

## Email Monitor

A polling-based agent that checks your email and sends you vibes about important messages. No webhooks needed.

```python
"""Email Monitor -- checks IMAP and sends vibes about new emails."""

import email
import imaplib
import os
import time
from datetime import datetime, timezone

from zinq_agent import ZinqAgent

agent = ZinqAgent(api_key=os.environ["ZINQ_API_KEY"])

IMAP_HOST = os.environ["IMAP_HOST"]          # e.g., "imap.gmail.com"
IMAP_USER = os.environ["IMAP_USER"]          # e.g., "you@gmail.com"
IMAP_PASS = os.environ["IMAP_APP_PASSWORD"]  # App-specific password

# Check every 5 minutes
POLL_INTERVAL = 300

# Only notify about emails from these senders (or set to None for all)
IMPORTANT_SENDERS = None  # e.g., ["boss@company.com", "partner@email.com"]


def check_email():
    """Check for unread emails and return summaries."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select("inbox")

        _, message_ids = mail.search(None, "UNSEEN")
        if not message_ids[0]:
            return []

        summaries = []
        for msg_id in message_ids[0].split()[:5]:  # Max 5 per check
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            sender = msg["From"]
            subject = msg["Subject"] or "(no subject)"

            # Filter by important senders if configured
            if IMPORTANT_SENDERS:
                sender_email = email.utils.parseaddr(sender)[1]
                if sender_email not in IMPORTANT_SENDERS:
                    continue

            summaries.append({"from": sender, "subject": subject})

        mail.logout()
        return summaries

    except Exception as e:
        print(f"Email check failed: {e}")
        return []


def main():
    ctx = agent.user.context()
    print(f"Email Monitor started for {ctx.name}")
    print(f"Checking {IMAP_HOST} every {POLL_INTERVAL}s...")

    while True:
        try:
            emails = check_email()

            if emails:
                lines = [f"You have {len(emails)} new email(s):"]
                for em in emails:
                    lines.append(f"  From: {em['from']}")
                    lines.append(f"  Subject: {em['subject']}")
                    lines.append("")

                agent.vibes.send(text="\n".join(lines))
                print(f"Notified about {len(emails)} emails")

        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(POLL_INTERVAL)

    agent.close()


if __name__ == "__main__":
    main()
```

**Setup:**
```bash
pip install zinq-agent
export ZINQ_API_KEY=zak_your_key
export IMAP_HOST=imap.gmail.com
export IMAP_USER=you@gmail.com
export IMAP_APP_PASSWORD=your_app_password  # NOT your regular password
python email_monitor.py
```

---

## Slack Bridge

Forward messages from a Slack channel to Zinq, and let the user reply from Zinq back to Slack.

```python
"""Slack Bridge -- forward Slack messages to Zinq vibes."""

import os
import threading

from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from zinq_agent import ZinqAgent, ZinqWebhook

agent = ZinqAgent(api_key=os.environ["ZINQ_API_KEY"])
webhook = ZinqWebhook(secret="dev", skip_signature_check=True  # Signature verification coming soon)

slack_bot = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
slack_socket = SocketModeClient(
    app_token=os.environ["SLACK_APP_TOKEN"],
    web_client=slack_bot,
)

CHANNEL_ID = os.environ["SLACK_CHANNEL_ID"]  # Channel to bridge


def handle_slack_message(client, req):
    """Forward Slack messages to Zinq."""
    if req.type != "events_api":
        return

    event = req.payload.get("event", {})
    if event.get("type") != "message" or event.get("subtype"):
        return  # Skip bot messages and system messages

    user_info = slack_bot.users_info(user=event["user"])
    name = user_info["user"]["real_name"]
    text = event.get("text", "")

    # Store the Slack thread timestamp so we can reply back
    ts = event.get("ts", "")
    agent.memories.save(
        key="last_slack_ts",
        value=ts,
        category="slack_bridge",
    )

    agent.vibes.send(
        text=f"[Slack - {name}]: {text}",
        buttons=[
            {"label": "Reply in Slack", "value": f"slack_reply:{ts}"},
        ],
    )

    client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))


@webhook.on("vibe.reply")
def handle_zinq_reply(event):
    """Forward Zinq replies back to Slack."""
    if not event.data.button_value:
        return

    if event.data.button_value.startswith("slack_reply:"):
        thread_ts = event.data.button_value.split(":", 1)[1]
        # Ask for the reply text
        agent.vibes.send(
            text="What do you want to reply?",
            input_type="text_input",
            metadata={"slack_thread_ts": thread_ts},
        )


@webhook.on("vibe.received")
def handle_text_reply(event):
    """Send text replies back to Slack."""
    # Check if there's a pending Slack reply
    last_ts = agent.memories.get("last_slack_ts")
    if last_ts and event.data.text:
        slack_bot.chat_postMessage(
            channel=CHANNEL_ID,
            text=event.data.text,
            thread_ts=last_ts.value,
        )
        agent.vibes.send(text="Sent to Slack!")


def start_slack():
    """Start the Slack socket mode client in a background thread."""
    slack_socket.socket_mode_request_listeners.append(handle_slack_message)
    slack_socket.connect()


if __name__ == "__main__":
    print("Starting Slack Bridge...")

    # Start Slack listener in background
    slack_thread = threading.Thread(target=start_slack, daemon=True)
    slack_thread.start()

    # Start Zinq webhook server (blocking)
    webhook.start(port=8080)
```

**Setup:**
```bash
pip install zinq-agent[webhook] slack-sdk
export ZINQ_API_KEY=zak_your_key
# ZINQ_WEBHOOK_SECRET — not yet available, use skip_signature_check=True
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...
export SLACK_CHANNEL_ID=C0123456789
python slack_bridge.py
```

---

## Appointment Booker

A polling-based agent for scheduling appointments. No webhooks needed -- great for environments where inbound HTTP isn't possible.

```python
"""Appointment Booker -- polling-based scheduling agent."""

import os
import time
from datetime import datetime, timezone

from zinq_agent import ZinqAgent

agent = ZinqAgent(api_key=os.environ["ZINQ_API_KEY"])

POLL_INTERVAL = 5  # seconds


def handle_vibe(vibe):
    """Process a user message."""
    text = (vibe.transcript or vibe.text or "").lower()

    if "book" in text or "schedule" in text:
        agent.vibes.send(
            text="When works for you?",
            input_type="choice",
            options=[
                "Tomorrow morning (9-12)",
                "Tomorrow afternoon (1-5)",
                "This weekend",
            ],
            reply_to=vibe.id,
        )

    elif "cancel" in text:
        appointments = agent.memories.list(category="appointments")
        if appointments:
            latest = appointments[-1]
            agent.memories.delete(latest.key)
            agent.vibes.send(text=f"Cancelled: {latest.value}", reply_to=vibe.id)
        else:
            agent.vibes.send(text="No appointments to cancel.", reply_to=vibe.id)

    elif "list" in text or "show" in text:
        appointments = agent.memories.list(category="appointments")
        if appointments:
            lines = [f"- {a.value}" for a in appointments]
            agent.vibes.send(
                text="Your appointments:\n" + "\n".join(lines),
                reply_to=vibe.id,
            )
        else:
            agent.vibes.send(text="No upcoming appointments.", reply_to=vibe.id)

    elif any(slot in text for slot in ["morning", "afternoon", "weekend"]):
        now = datetime.now(timezone.utc)
        key = f"appt_{now.strftime('%Y%m%d_%H%M%S')}"
        agent.memories.save(key=key, value=vibe.text or text, category="appointments")
        agent.vibes.send(text="Booked! Say 'list' to see all appointments.", reply_to=vibe.id)

    else:
        agent.vibes.send(
            text="I can help with appointments! Try:\n"
            "- 'Book an appointment'\n"
            "- 'Show my appointments'\n"
            "- 'Cancel last appointment'",
            reply_to=vibe.id,
        )


def main():
    ctx = agent.user.context()
    print(f"Appointment Bot for {ctx.name} (polling every {POLL_INTERVAL}s)")

    last_seen = datetime.now(timezone.utc).isoformat()

    while True:
        try:
            vibes = agent.vibes.received(since=last_seen, unread=True)
            for vibe in vibes:
                print(f"[{vibe.created_at}] {vibe.text}")
                handle_vibe(vibe)
                last_seen = vibe.created_at.isoformat()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(POLL_INTERVAL)

    agent.close()


if __name__ == "__main__":
    main()
```

---

## Personal Shopper

A full-featured agent that uses AI for product recommendations, memories for preferences, and diary search for context.

```python
"""Personal Shopper -- AI-powered product recommendations."""

import os
from zinq_agent import ZinqAgent, ZinqWebhook, InsufficientCreditsError

agent = ZinqAgent(api_key=os.environ["ZINQ_API_KEY"])
webhook = ZinqWebhook(secret="dev", skip_signature_check=True  # Signature verification coming soon)

SYSTEM_PROMPT = """You are a personal shopping assistant in the Zinq app.
Keep responses under 200 words. Suggest 2-3 options when recommending.
Ask clarifying questions for vague requests. Remember preferences."""


def build_context():
    """Build context from memories and diary."""
    parts = []

    memories = agent.memories.list(category="shopping")
    if memories:
        prefs = "\n".join(f"- {m.key}: {m.value}" for m in memories)
        parts.append(f"Saved preferences:\n{prefs}")

    results = agent.diary.search("shopping clothes style outfit", limit=3)
    if results.results:
        entries = "\n".join(f"- {r.text}" for r in results.results if r.text)
        parts.append(f"Recent mentions:\n{entries}")

    return "\n\n".join(parts) if parts else "No preferences saved yet."


@webhook.on("vibe.received")
def handle_message(event):
    text = event.data.transcript or event.data.text or ""
    lower = text.lower()

    # Detect preference-saving intent
    if any(kw in lower for kw in ["my size is", "i prefer", "i like", "i wear"]):
        if "size" in lower:
            agent.memories.save(key="size", value=text, category="shopping")
        elif "color" in lower:
            agent.memories.save(key="color", value=text, category="shopping")
        else:
            agent.memories.save(key="style", value=text, category="shopping")
        agent.vibes.send(text="Noted! I'll remember that for future recommendations.")
        return

    # AI-powered response
    context = build_context()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context about me:\n{context}"},
        {"role": "user", "content": text},
    ]

    try:
        response = agent.gemini.chat(messages=messages, model="flash")
        agent.vibes.send(text=response.text)
    except InsufficientCreditsError:
        agent.vibes.send(
            text="You're out of AI credits this month. "
            "You can still save preferences -- I'll use them when credits reset!"
        )


@webhook.on("agent.wave")
def greet(event):
    ctx = agent.user.context()
    if event.data.is_first_wave:
        agent.vibes.send(
            text=f"Hey {ctx.name}! I'm your personal shopper. "
            "Tell me what you're looking for or share your style preferences.",
            input_type="choice",
            options=["Find me an outfit", "Save my preferences", "What's trending?"],
        )
    else:
        agent.vibes.send(text=f"Welcome back, {ctx.name}! What are you shopping for?")


if __name__ == "__main__":
    print("Starting Personal Shopper on port 8080...")
    webhook.start(port=8080)
```

---

## Pattern Summary

| Pattern | Use When | Needs Webhooks? |
|---------|----------|----------------|
| **Webhook-based** (Echo, Fitness Coach, Shopper) | You want real-time responses to user messages | Yes |
| **Polling-based** (Appointment, Email Monitor) | Inbound HTTP isn't possible, or you want periodic checks | No |
| **Scheduled** (Daily Digest) | You want to run at specific times (cron) | No |
| **Bridge** (Slack) | You want to connect an external service to Zinq | Yes |

All patterns can be mixed. For example, you could have a webhook-based agent that also runs a periodic check on a background thread.
