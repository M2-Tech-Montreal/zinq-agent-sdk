"""Appointment Bot -- a polling-based agent (no webhook required).

Demonstrates:
- Polling for new vibes instead of using webhooks
- Interactive choice buttons for scheduling
- Memory-based appointment storage
- No external dependencies beyond the SDK

This pattern is useful for:
- Quick scripts and cron jobs
- Environments where inbound webhooks are not possible
- Simple agents that check periodically

Setup:
    pip install zinq-agent

    export ZINQ_API_KEY="zak_your_key_here"

    python appointment_bot.py
"""

import os
import time
from datetime import datetime, timezone

from zinq_agent import ZinqAgent

api_key = os.environ["ZINQ_API_KEY"]
agent = ZinqAgent(api_key=api_key)

POLL_INTERVAL = 5  # seconds


def handle_vibe(vibe):
    """Process a single vibe from the user."""
    text = (vibe.transcript or vibe.text or "").lower()

    if "book" in text or "appointment" in text or "schedule" in text:
        agent.vibes.send(
            text="Sure! When would you like to schedule?",
            input_type="choice",
            options=[
                "Tomorrow morning (9-12)",
                "Tomorrow afternoon (1-5)",
                "Tomorrow evening (6-9)",
                "This weekend",
            ],
            reply_to=vibe.id,
        )
    elif "cancel" in text:
        appointments = agent.memories.list(category="appointments")
        if appointments:
            latest = appointments[-1]
            agent.memories.delete(latest.key)
            agent.vibes.send(
                text=f"Cancelled your appointment: {latest.value}",
                reply_to=vibe.id,
            )
        else:
            agent.vibes.send(
                text="You don't have any upcoming appointments.",
                reply_to=vibe.id,
            )
    elif "list" in text or "show" in text or "upcoming" in text:
        appointments = agent.memories.list(category="appointments")
        if appointments:
            lines = [f"- {a.value}" for a in appointments]
            agent.vibes.send(
                text="Your upcoming appointments:\n" + "\n".join(lines),
                reply_to=vibe.id,
            )
        else:
            agent.vibes.send(
                text="No upcoming appointments. Say 'book' to schedule one!",
                reply_to=vibe.id,
            )
    elif any(
        slot in text
        for slot in ["morning", "afternoon", "evening", "weekend"]
    ):
        # User selected a time slot -- save the appointment
        now = datetime.now(timezone.utc)
        key = f"appt_{now.strftime('%Y%m%d_%H%M%S')}"
        agent.memories.save(
            key=key,
            value=f"Appointment: {vibe.text or vibe.transcript}",
            category="appointments",
        )
        agent.vibes.send(
            text=f"Booked! I've saved your appointment for {vibe.text or vibe.transcript}. "
            "Say 'list' to see all upcoming appointments.",
            reply_to=vibe.id,
        )
    else:
        agent.vibes.send(
            text="I can help with appointments! Try:\n"
            "- 'Book an appointment'\n"
            "- 'Show upcoming appointments'\n"
            "- 'Cancel last appointment'",
            reply_to=vibe.id,
        )


def main():
    """Main polling loop."""
    print(f"Appointment Bot started (polling every {POLL_INTERVAL}s)...")

    ctx = agent.user.context()
    print(f"Connected to user: {ctx.name} ({ctx.timezone})")

    last_seen = datetime.now(timezone.utc).isoformat()

    while True:
        try:
            vibes = agent.vibes.received(since=last_seen, unread=True)

            for vibe in vibes:
                print(f"[{vibe.created_at}] User: {vibe.text or vibe.transcript}")
                handle_vibe(vibe)
                last_seen = vibe.created_at.isoformat()

        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
