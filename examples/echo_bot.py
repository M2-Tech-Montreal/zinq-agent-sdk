"""
⚠️  REFERENCE CODE — not tested end-to-end. See examples/sentinel/ and examples/rosas_bakery/ for working agents.
Echo Bot -- the simplest possible Zinq agent.

Echoes back whatever the user says. Demonstrates:
- Receiving vibes via webhook
- Sending vibes back to the user
- Handling voice transcripts

Setup:
    pip install zinq-agent[webhook]

    export ZINQ_API_KEY="zak_your_key_here"
    # ZINQ_WEBHOOK_SECRET — not yet available, use skip_signature_check=True

    python echo_bot.py
"""

import os

from zinq_agent import ZinqAgent, ZinqWebhook

api_key = os.environ["ZINQ_API_KEY"]
webhook_secret = os.environ["ZINQ_WEBHOOK_SECRET"]

agent = ZinqAgent(api_key=api_key)
webhook = ZinqWebhook(secret=webhook_secret)


@webhook.on("vibe.received")
def echo(event):
    """Echo back whatever the user sent."""
    # Voice vibes have a transcript; text vibes have text
    text = event.data.transcript or event.data.text or "(empty vibe)"
    agent.vibes.send(text=f"You said: {text}")


@webhook.on("agent.wave")
def greet(event):
    """Greet the user when they open the agent chat."""
    if event.data.is_first_wave:
        agent.vibes.send(text="Hey! I'm Echo Bot. I repeat everything you say.")
    else:
        agent.vibes.send(text="Welcome back! Say something and I'll echo it.")


@webhook.on("charm.received")
def handle_charm(event):
    """Respond to charm reactions."""
    agent.vibes.send(text=f"You reacted with {event.data.emoji}")


if __name__ == "__main__":
    print("Starting Echo Bot on port 8080...")
    webhook.start(port=8080)
