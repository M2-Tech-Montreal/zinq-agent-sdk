# Zinq Agent SDK for Python

### Build private AI agents for yourself — or publish business agents to the Zinq Marketplace and get paying customers without building an app.

**Personal agents** run anywhere — your phone, your desktop, or the cloud. Monitor email, automate Slack, track crypto, send daily briefings — anything Python can do, your agent can do, and it pushes results straight to your pocket.

**Marketplace agents** let you build an AI agent for a business and publish it to the Zinq Marketplace. Customers find your agent, enable it, and interact through chat. You handle tool calls (bookings, orders, inventory) with a Python webhook server.

<!-- TODO: Add logo/banner image here -->
<!-- ![Zinq Agent SDK](https://zinq-app.com/assets/sdk-banner.png) -->

[![PyPI version](https://img.shields.io/pypi/v/zinq-agent)](https://pypi.org/project/zinq-agent/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Zinq Agent SDK** lets you build personal AI agents in Python that connect to the [Zinq](https://zinq-app.com) platform. Your agent gets its own chat thread, can read the user's diary, send messages (vibes), remember preferences, and use Google Gemini for AI-powered responses — all through a clean, async-ready Python API.

### What is Zinq?

[Zinq](https://zinq-app.com) is a mobile app where every interaction happens through **vibes** — short voice, video, photo, or text messages. Users connect with people they know, keep a private diary, and talk to AI agents that understand their actual life.

**The diary is the key.** Every vibe a user shares — every voice note, every photo, every conversation — gets transcribed, classified, and stored as a searchable private diary. This diary is what makes Zinq agents different from every other AI assistant: your agent doesn't start from zero. It reads the user's diary. It knows their habits, their mood patterns, their goals, their relationships. The more they use Zinq, the smarter every agent gets.

Your personal agent gets full access to this diary through the SDK — semantic search, date browsing, context injection. This is the context layer that no other agent platform has.

Every voice and video vibe is **automatically transcribed and summarized** by Gemini — so your agent can read what users said, not just what they typed.

Zinq ships with built-in AI agents that users already interact with daily:

| Agent | What It Does |
|-------|-------------|
| **Veritas** | Fraud and scam detection — paste any message, document, or profile and get a risk report |
| **Aura** | Mental wellness — CBT techniques, mood tracking, stress management |
| **Atlas** | Fitness & nutrition — workouts, meal plans, recovery |
| **Diary** | Private life database — ask anything about your own life |
| **Cue** | Task manager — conversational todo lists |
| **Radar** | Travel concierge — trips, restaurants, experiences |
| **Vantage** | Meeting prep and negotiation coach |
| **Astra** | Personalised astrology grounded in your diary patterns |
| + 18 more | Games (chess, word puzzles, trivia), finance, movies, relationship manager |

Your agent joins this ecosystem. It has its own profile, avatar, and chat thread — just like a real contact. Users interact with your agent the same way they interact with the built-in agents: by sending vibes.

### Why Zinq Agents?

- **Full desktop power** — Your agent runs on your machine. Screen control, file access, browser automation, shell commands — anything Python can do.
- **Connected to a social network** — Unlike isolated desktop AI assistants, Zinq agents are connected to users through vibes, memories, and a built-in marketplace.
- **Gemini built-in** — Call Google Gemini through our API, or bring your own LLM (OpenAI, Claude, local Llama).
- **Deploy anywhere** — Your laptop, GCloud free tier, AWS, Docker, Railway. No vendor lock-in.
- **Open source** — MIT licensed. Build what you want.

### Two real examples

**[Sentinel](examples/sentinel/)** — a personal agent that monitors your Gmail and Slack from a $0/month GCloud instance. Every 5 minutes it checks for new emails, uses Gemini to score importance and generate a summary, and sends you a vibe. You read a one-line summary on your phone instead of opening your inbox. Runs 24/7, costs nothing. This is what a personal agent looks like.

**[Rosa's Bakery](examples/rosas_bakery/)** — a marketplace agent for a neighborhood bakery. Customers open Zinq, find Rosa's, and chat. The agent knows today's specials, takes pickup orders, handles custom cake requests with human handoff, and sends morning broadcast vibes to regulars. Rosa doesn't need a website, an app, or a Shopify subscription — just an AI agent that talks to her customers. This is what a marketplace agent looks like.

---

## Install

```bash
pip install zinq-agent
```

For webhook support (receiving real-time events from users):

```bash
pip install zinq-agent[webhook]
```

## Quick Start

Five lines to send your first vibe:

```python
from zinq_agent import ZinqAgent

agent = ZinqAgent(api_key="zak_your_key_here")
agent.vibes.send(text="Hey! Your agent is alive.")
agent.close()
```

Or even shorter with a context manager:

```python
from zinq_agent import ZinqAgent

with ZinqAgent(api_key="zak_your_key_here") as agent:
    agent.vibes.send(text="Hey! Your agent is alive.")
```

## Build Sentinel in 10 Minutes

**Sentinel** is the flagship example — a personal agent that monitors your Gmail and Slack, then sends you Zinq vibes when something important comes in.

```python
from zinq_agent import ZinqAgent
from apscheduler.schedulers.blocking import BlockingScheduler
import imaplib, os

agent = ZinqAgent()  # reads ZINQ_API_KEY from env

def check_email():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
    mail.select("inbox")
    _, msgs = mail.search(None, "UNSEEN")
    count = len(msgs[0].split()) if msgs[0] else 0
    if count > 0:
        # Use Gemini to summarize
        summary = agent.gemini.chat(messages=[
            {"role": "user", "content": f"Summarize: {count} new emails"}
        ])
        agent.vibes.send(text=f"📬 {count} new emails\n{summary.text}")
    mail.logout()

scheduler = BlockingScheduler()
scheduler.add_job(check_email, "interval", minutes=5)
print("Sentinel is watching...")
scheduler.start()
```

Deploy to GCloud free tier and it runs 24/7. Full Sentinel with Slack integration, importance scoring, and reply support: **[examples/sentinel/](examples/sentinel/)**

---

## What Can Your Agent Do?

### Read the user's diary

```python
# Browse entries
for entry in agent.diary.iter(start="2026-04-01"):
    print(f"{entry.created_at}: {entry.text}")

# Semantic search
results = agent.diary.search("morning workouts", limit=5)
for r in results.results:
    print(f"[{r.similarity:.0%}] {r.text}")
```

### Send vibes (messages)

```python
# Simple text
agent.vibes.send(text="Time for your afternoon walk!")

# Interactive choices
agent.vibes.send(
    text="Which workout today?",
    input_type="choice",
    options=["Upper body", "Lower body", "Cardio", "Rest day"],
)

# Yes/no question
agent.vibes.send(text="Did you drink water today?", input_type="yes_no")

# Custom buttons
agent.vibes.send(
    text="Your weekly report is ready.",
    buttons=[
        {"label": "View Report", "value": "view_report"},
        {"label": "Skip", "value": "skip"},
    ],
)
```

### Remember things

```python
# Save a preference
agent.memories.save(key="diet", value="vegetarian", category="health")

# Read it back
mem = agent.memories.get("diet")
print(mem.value)  # "vegetarian"

# List all memories in a category
health_mems = agent.memories.list(category="health")
```

### Know your user

```python
ctx = agent.user.context()
print(f"Name: {ctx.name}")
print(f"Timezone: {ctx.timezone}")
print(f"Credits remaining: {ctx.credit_status.credits_remaining}")
```

### Use Gemini AI (optional)

```python
response = agent.gemini.chat(
    messages=[
        {"role": "system", "content": "You are a fitness coach."},
        {"role": "user", "content": "What should I eat after a run?"},
    ],
    model="flash",  # or "pro" for higher quality
)
print(response.text)
print(f"Credits used: {response.usage.credits_used}")
```

### Receive real-time events via webhooks

```python
from zinq_agent import ZinqAgent, ZinqWebhook

agent = ZinqAgent()
webhook = ZinqWebhook(secret="zws_your_secret_here")

@webhook.on("vibe.received")
def handle_vibe(event):
    text = event.data.transcript or event.data.text
    agent.vibes.send(text=f"You said: {text}")

@webhook.on("agent.wave")
def greet(event):
    agent.vibes.send(text="Hey! I'm your agent.")

webhook.start(port=8080)
```

### Marketplace Agent Admin

If you published a marketplace agent, use `ZinqMarketplaceAdmin` to manage it:

```python
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin(api_key="zbk_xxxxx")  # or set ZINQ_BIZ_KEY env var

# Deploy your agent definition
admin.agent.deploy(open("agent.yaml").read())

# Check how many users have enabled your agent
print(f"{admin.users.count()} users")

# Reply to conversations awaiting human response
for convo in admin.conversations.list(status="awaiting_human"):
    admin.conversations.reply(convo["sessionId"], "Thanks for reaching out!")

# Send a broadcast to all users
admin.broadcast("We just launched a new feature!")

# Manage data collections (product catalogs, FAQ, etc.)
admin.data.add("products", {"name": "Widget", "price": 9.99})
products = admin.data.list("products")

# Test your agent without a real user
response = admin.test.chat("What services do you offer?")
print(response["reply"])
```

Full reference: **[docs/business-agents.md](docs/business-agents.md)**

---

## Marketplace Agents

Build an AI agent for a business, deploy it to the Zinq Marketplace, and handle customer interactions with a Python webhook.

### 1. Generate your agent definition

```python
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin()

# AI generates a YAML agent definition from your description
result = admin.agent.generate(
    "A bakery in Park Slope. Sourdough, croissants, custom cakes. "
    "Open Tue-Sun 7am-6pm. Custom cakes need 48h notice.",
    name="Rosa's Bakery"
)

# Review and refine
review = admin.agent.review(yaml=result["yamlDefinition"])
refined = admin.agent.refine(
    yaml=result["yamlDefinition"],
    feedback="Add a daily specials tool and human handoff for wedding cakes"
)

# Deploy
admin.agent.deploy(refined["yaml"])
```

### 2. Handle tool calls with a webhook

```python
from zinq_agent.webhook import ZinqBusinessWebhook

webhook = ZinqBusinessWebhook(secret="zws_xxx", admin=admin)

@webhook.action("request_pickup")
def handle_order(params, session_id):
    # Your order logic
    return {"confirmed": True, "pickup_time": params["time"]}

@webhook.action("request_custom_cake")
def handle_cake(params, session_id):
    if params.get("occasion") == "wedding":
        return {"escalated": True, "message": "Connecting you with Rosa for your wedding cake."}
    return {"confirmed": True, "price": "$45"}

webhook.start(port=8080)
```

### 3. Handle human handoffs

When the AI escalates a conversation, you handle it through the SDK:

```python
# Check for conversations waiting on a human
for convo in admin.conversations.list(status="awaiting_human"):
    details = admin.conversations.get(convo["sessionId"])
    for msg in details["messages"]:
        print(f"  {msg['userName']}: {msg['textContent']}")

    # Reply to the customer (appears as a vibe from the agent)
    admin.conversations.reply(convo["sessionId"],
        "Hi! Rosa here. I'd love to make your wedding cake.")
```

### Marketplace examples

**Working examples** — fully tested and runnable:

| Example | What It Does | Key Features |
|---------|-------------|--------------|
| **[Rosa's Bakery](examples/rosas_bakery/)** | Daily specials, pickup orders, custom cakes | Morning broadcasts, order management, human handoff for custom requests |
| **[Sentinel](examples/sentinel/)** | Gmail + Slack monitoring with AI summaries | Email digest, importance scoring, reply support, GCloud deployment |

**Starter templates** — code scaffolding for common business types (not yet fully tested):

| Example | What It Shows |
|---------|--------------|
| [Joe's Barber Shop](examples/joes_barber/) | Appointment booking, service menu, cancellation |
| [Dr. Sarah Nutrition](examples/dr_sarah_nutrition/) | Professional booking, intake forms, safety guardrails |

### Use cases for marketplace agents

| Industry | Use Case |
|----------|----------|
| Barber shops, salons, spas | Appointment booking and reminders |
| Bakeries, restaurants, cafes | Ordering, daily specials, reservations |
| Nutritionists, therapists, coaches | Consultations, intake forms, follow-ups |
| Plumbers, electricians, cleaners | Service quotes and scheduling |
| Fashion designers, artists | Personal shopping and commissions |
| Tutors, music teachers | Lesson scheduling and progress tracking |

---

## Environment Variables

The SDK reads these automatically so you don't have to pass them in code:

```bash
export ZINQ_API_KEY=zak_your_key_here        # Required for ZinqAgent
export ZINQ_WEBHOOK_SECRET=zws_your_secret   # Only for webhooks
export ZINQ_BIZ_KEY=zbk_your_key_here        # Only for ZinqMarketplaceAdmin
```

```python
# No arguments needed -- reads ZINQ_API_KEY from environment
agent = ZinqAgent()

# Webhook secret must be passed explicitly
webhook = ZinqWebhook(secret="zws_your_secret_here")
```

## Async Support

Every method has an async equivalent:

```python
import asyncio
from zinq_agent import AsyncZinqAgent

async def main():
    async with AsyncZinqAgent() as agent:
        await agent.vibes.send(text="Async vibe!")

        response = await agent.gemini.chat(
            messages=[{"role": "user", "content": "Tell me a joke"}],
        )
        print(response.text)

asyncio.run(main())
```

## Error Handling

All errors are typed so you can handle them precisely:

```python
from zinq_agent import (
    ZinqError,                 # Base -- catch everything
    AuthenticationError,       # 401 -- bad API key
    RateLimitError,            # 429 -- slow down
    InsufficientCreditsError,  # 402 -- user out of credits
    NotFoundError,             # 404 -- resource missing
    ValidationError,           # 422 -- bad request params
    ServerError,               # 5xx -- Zinq backend issue
)

try:
    agent.gemini.chat(messages=[...])
except InsufficientCreditsError as e:
    print(f"Need {e.credits_required} credits, have {e.credits_remaining}")
except RateLimitError as e:
    print(f"Rate limited. Retry in {e.retry_after} seconds.")
except ZinqError as e:
    print(f"Something went wrong: {e.message}")
```

## Examples

See the [`examples/`](examples/) directory:

### Working examples

| Example | Description | Type |
|---------|-------------|------|
| [`sentinel/`](examples/sentinel/) | Gmail + Slack monitor with AI summaries — deploy to GCloud free tier | Personal |
| [`rosas_bakery/`](examples/rosas_bakery/) | Bakery ordering, daily specials, human handoff | Marketplace |

### Starter templates (ideas — not fully tested)

| Example | Description | Type |
|---------|-------------|------|
| [`echo_bot.py`](examples/echo_bot.py) | Echoes back everything the user says | Personal |
| [`appointment_bot.py`](examples/appointment_bot.py) | Polling-based appointment scheduler | Personal |
| [`personal_shopper.py`](examples/personal_shopper.py) | Gemini + memories for recommendations | Personal |
| [`trading_bot.py`](examples/trading_bot.py) | Crypto portfolio monitoring via Binance | Personal |
| [`joes_barber/`](examples/joes_barber/) | Barber shop appointment booking | Marketplace |
| [`dr_sarah_nutrition/`](examples/dr_sarah_nutrition/) | Nutrition consultations and meal plans | Marketplace |

## Developer Guides

Three paths depending on what you are building. Everything is done through the SDK -- there is no web dashboard.

| Guide | For | Time |
|-------|-----|------|
| **[Personal Agent](docs/dev-guide-personal.md)** | Developers building agents for themselves | 10 min |
| **[Marketplace Tier 1](docs/dev-guide-marketplace-tier1.md)** | Businesses creating AI agents (no webhook server) | 30 min |
| **[Marketplace Tier 2](docs/dev-guide-marketplace-tier2.md)** | Businesses with custom integrations (webhook server) | 1 hour |

## Reference Documentation

Detailed reference docs are in the [`docs/`](docs/) directory:

- **[Getting Started](docs/getting-started.md)** -- Build your first agent in 5 minutes
- **[API Reference](docs/api-reference.md)** -- Every class, method, and parameter
- **[Webhooks](docs/webhooks.md)** -- Receive real-time events from users
- **[Business Agents](docs/business-agents.md)** -- Marketplace admin client reference
- **[Examples Cookbook](docs/examples.md)** -- Copy-paste recipes for common agents
- **[Deployment](docs/deployment.md)** -- Run your agent in production
- **[Best Practices](docs/best-practices.md)** -- Tips for building great agents

## Pricing

The SDK is free. Building agents is free. Publishing to the marketplace is free. Zinq never charges developers.

Users pay for their own credits — either per-use or through a subscription. Credits are inexpensive. As a developer, you pay nothing.

Marketplace agent developers are eligible for a profit-sharing arrangement on the credits your agent generates. Contact Vincent Mayeski at v@m2te.ch for details.

## Requirements

- Python 3.10+
- [`httpx`](https://www.python-httpx.org/) -- HTTP client
- [`pydantic`](https://docs.pydantic.dev/) -- Data validation
- [`flask`](https://flask.palletsprojects.com/) -- Webhook server (optional)

## Build a Crypto Trading Agent in 10 Minutes

Monitor your Binance portfolio from your phone. Get alerts when coins move 5%+.

```bash
pip install zinq-agent ccxt apscheduler
export ZINQ_API_KEY=zak_your_key
export BINANCE_API_KEY=your_binance_key
export BINANCE_SECRET=your_binance_secret
```

```python
from zinq_agent import ZinqAgent
from apscheduler.schedulers.blocking import BlockingScheduler
import ccxt, os

agent = ZinqAgent()
exchange = ccxt.binance({
    "apiKey": os.environ["BINANCE_API_KEY"],
    "secret": os.environ["BINANCE_SECRET"],
})

last_prices = {}

def check_prices():
    balance = exchange.fetch_balance()
    alerts = []
    for coin, amount in balance["total"].items():
        if amount > 0 and coin not in ("USDT", "USD"):
            try:
                ticker = exchange.fetch_ticker(f"{coin}/USDT")
                price = ticker["last"]
                if coin in last_prices:
                    change = (price - last_prices[coin]) / last_prices[coin]
                    if abs(change) >= 0.05:
                        emoji = "🚀" if change > 0 else "📉"
                        alerts.append(f"{emoji} {coin} {change:+.1%}: ${price:,.2f}")
                last_prices[coin] = price
            except Exception:
                pass
    if alerts:
        agent.vibes.send(text="Price alerts:\n" + "\n".join(alerts))

def hourly_summary():
    balance = exchange.fetch_balance()
    total = balance["total"].get("USDT", 0)
    lines = []
    for coin, amount in balance["total"].items():
        if amount > 0 and coin not in ("USDT", "USD"):
            try:
                price = exchange.fetch_ticker(f"{coin}/USDT")["last"]
                value = amount * price
                total += value
                lines.append(f"  {coin}: ${value:,.2f}")
            except Exception:
                pass
    agent.vibes.send(text=f"📊 Portfolio: ${total:,.2f}\n" + "\n".join(lines[:8]))

scheduler = BlockingScheduler()
scheduler.add_job(check_prices, "interval", minutes=5)
scheduler.add_job(hourly_summary, "cron", minute=0)
hourly_summary()
print("Trading agent watching your portfolio...")
scheduler.start()
```

Deploy to GCloud free tier → portfolio alerts on your phone 24/7. Full version with natural language queries ("BTC price?", "how's my portfolio?") and Gemini-powered analysis: **[examples/trading_bot.py](examples/trading_bot.py)**

---

## Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feat/my-feature`)
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Run linter: `ruff check .`
6. Run type checker: `mypy zinq_agent`
7. Open a pull request

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Use Cases

The Zinq Agent SDK is perfect for building:

| Use Case | Description | Status |
|----------|-------------|--------|
| **Email AI Assistant** | Monitor Gmail/Outlook, summarize, auto-reply | Working — [Sentinel](examples/sentinel/) |
| **Bakery / Restaurant** | Ordering, daily specials, human handoff | Working — [Rosa's Bakery](examples/rosas_bakery/) |
| **Slack Bot** | Bridge Slack mentions to mobile, summarize channels | Idea |
| **Personal Shopper** | AI product recommendations for online stores | Starter template |
| **Appointment Scheduler** | Automated booking for service businesses | Starter template |
| **Crypto Trading Agent** | Portfolio monitoring, price alerts via Binance | Starter template |
| **Fitness Coach** | Personalized workouts using diary data + Gemini | Idea |
| **Daily Digest** | Morning briefing from email, calendar, news | Idea |
| **Customer Support** | AI-first support with human handoff | Idea |

## Keywords

`ai-agent` `python-sdk` `personal-ai-assistant` `chatbot-framework` `gemini-api` `llm-agent` `conversational-ai` `email-automation` `slack-integration` `ai-shopping-assistant` `appointment-booking` `webhook-server` `agent-framework` `autonomous-agent` `ai-coach`

## Star History

If this project helps you build something cool, give it a star! It helps others discover it.

## License

MIT — do whatever you want with it.
