"""
⚠️  REFERENCE CODE — not tested end-to-end. See examples/sentinel/ and examples/rosas_bakery/ for working agents.
Personal Shopper -- an agent that uses Gemini and memories.

Demonstrates:
- Reading and saving memories for persistent preferences
- Using Zinq's Gemini proxy for AI responses
- Reading diary entries for context
- Interactive buttons for user choices
- Handling insufficient credits gracefully

Setup:
    pip install zinq-agent[webhook]

    export ZINQ_API_KEY="zak_your_key_here"
    export ZINQ_WEBHOOK_SECRET="zws_your_secret_here"

    python personal_shopper.py
"""

import os

from zinq_agent import (
    InsufficientCreditsError,
    ZinqAgent,
    ZinqWebhook,
)

api_key = os.environ["ZINQ_API_KEY"]
webhook_secret = os.environ["ZINQ_WEBHOOK_SECRET"]

agent = ZinqAgent(api_key=api_key)
webhook = ZinqWebhook(secret=webhook_secret)

SYSTEM_PROMPT = """You are a personal shopping assistant inside the Zinq app.

Your personality: helpful, concise, and style-aware. You remember the user's
preferences and make recommendations based on their history.

Rules:
- Keep responses under 200 words
- Always suggest 2-3 options when recommending products
- Ask clarifying questions if the request is vague
- Remember preferences the user mentions (sizes, brands, colors)
"""


def build_context():
    """Build context from memories and recent diary entries."""
    parts = []

    # Load saved preferences
    memories = agent.memories.list(category="shopping")
    if memories:
        prefs = "\n".join(f"- {m.key}: {m.value}" for m in memories)
        parts.append(f"User's saved preferences:\n{prefs}")

    # Check recent diary for relevant context
    diary_results = agent.diary.search("shopping outfit clothes style", limit=3)
    if diary_results.results:
        entries = "\n".join(
            f"- [{r.created_at.strftime('%b %d')}] {r.text}" for r in diary_results.results
        )
        parts.append(f"Recent diary mentions:\n{entries}")

    return "\n\n".join(parts) if parts else "No preferences saved yet."


@webhook.on("vibe.received")
def handle_message(event):
    """Process a shopping-related message from the user."""
    text = event.data.transcript or event.data.text or ""

    # Check if user is saving a preference
    lower = text.lower()
    if any(keyword in lower for keyword in ["my size is", "i prefer", "i like", "i wear"]):
        # Extract and save the preference
        if "size" in lower:
            agent.memories.save(key="clothing_size", value=text, category="shopping")
        elif "color" in lower:
            agent.memories.save(key="color_preference", value=text, category="shopping")
        else:
            agent.memories.save(key="general_preference", value=text, category="shopping")
        agent.vibes.send(text="Got it! I've saved that preference.")
        return

    # Build context and ask Gemini
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
            text="I'd love to help, but you're out of AI credits for this month. "
            "You can still tell me your preferences and I'll save them for later!"
        )


@webhook.on("agent.wave")
def greet(event):
    """Greet the user and show their saved preferences."""
    ctx = agent.user.context()
    memories = agent.memories.list(category="shopping")

    if event.data.is_first_wave:
        agent.vibes.send(
            text=f"Hey {ctx.name}! I'm your personal shopping assistant. "
            "Tell me what you're looking for, or share your style preferences "
            "and I'll remember them for future recommendations.",
            input_type="choice",
            options=["Find me an outfit", "Save my preferences", "What's trending?"],
        )
    elif memories:
        pref_summary = ", ".join(m.key.replace("_", " ") for m in memories[:3])
        agent.vibes.send(
            text=f"Welcome back, {ctx.name}! I remember your preferences: {pref_summary}. "
            "What are you shopping for today?"
        )
    else:
        agent.vibes.send(text=f"Hey {ctx.name}! What can I help you find today?")


@webhook.on("vibe.reply")
def handle_reply(event):
    """Handle button taps from interactive vibes."""
    if event.data.button_value == "show_plan":
        agent.vibes.send(text="Here's what I'd recommend based on your style...")
    elif event.data.button_value:
        # Treat button value as a new message
        handle_message(event)


if __name__ == "__main__":
    print("Starting Personal Shopper on port 8080...")
    webhook.start(port=8080)
