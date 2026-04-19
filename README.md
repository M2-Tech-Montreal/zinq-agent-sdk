# Zinq Agent SDK for Python

### Build AI agents that do real work — monitor email, automate Slack, run a personal shopping assistant, book appointments — all in Python.

<!-- TODO: Add logo/banner image here -->
<!-- ![Zinq Agent SDK](https://zinq-app.com/assets/sdk-banner.png) -->

[![PyPI version](https://img.shields.io/pypi/v/zinq-agent)](https://pypi.org/project/zinq-agent/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Zinq Agent SDK** lets you build personal AI agents in Python that connect to the [Zinq](https://zinq-app.com) platform. Your agent gets its own chat thread, can read the user's diary, send messages (vibes), remember preferences, and use Google Gemini for AI-powered responses — all through a clean, async-ready Python API.

### What is Zinq?

[Zinq](https://zinq-app.com) is a social app where every interaction happens through **vibes** — short voice, video, photo, or text messages. Think WhatsApp meets a personal diary, with AI agents built in. Users connect with people and businesses, keep a private diary, and chat with AI agents that understand their context.

Every voice and video vibe is **automatically transcribed and summarized** by Gemini — so your agent can read what users said, not just what they typed. The user's diary builds a rich personal context over time that your agent can search and learn from.

Zinq ships with **14 built-in AI agents** that users already interact with daily:

| Agent | What It Does |
|-------|-------------|
| **Aura** | Mental wellness coach — guided meditation, CBT exercises, mood tracking |
| **Atlas** | Fitness & nutrition — workout plans, fasting protocols, supplement tracking |
| **Cue** | Personal task manager — todo lists organized into projects |
| **Compass** | Travel concierge — trip planning, restaurant recommendations |
| **Flick** | Movie advisor — personalized recommendations |
| **Nexus** | Relationship manager — connection insights, intro suggestions |
| **Vantage** | Pitch & negotiation prep coach |
| **Astra** | Astrology — birth charts, daily horoscopes |
| + 6 more | Games (chess, word games), diary assistant, support, finance |

Your agent joins this ecosystem. It has its own profile, avatar, and chat thread — just like a real contact. Users interact with your agent the same way they interact with these built-in agents: by sending vibes (voice, video, text, photos).

### Why Zinq Agents?

- **Full desktop power** — Your agent runs on your machine. Screen control, file access, browser automation, shell commands — anything Python can do.
- **Connected to a social network** — Unlike isolated desktop AI assistants, Zinq agents are connected to users through vibes, memories, and a built-in marketplace.
- **Gemini built-in** — Call Google Gemini through our API, or bring your own LLM (OpenAI, Claude, local Llama).
- **Deploy anywhere** — Your laptop, GCloud free tier, AWS, Docker, Railway. No vendor lock-in.
- **Open source** — MIT licensed. Build what you want.

### What people are building

- **Email monitors** — Get AI-summarized email digests in your pocket
- **Slack bridges** — Important mentions forwarded as mobile notifications
- **Personal shoppers** — AI-powered product recommendations for small businesses
- **Appointment bookers** — Automated scheduling for barbers, restaurants, clinics
- **Fitness coaches** — Personalized workout plans using diary data
- **Crypto trading agents** — Portfolio monitoring, price alerts, P&L summaries via Binance/Coinbase
- **Daily digest agents** — Morning briefings from multiple data sources

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

## Environment Variables

The SDK reads these automatically so you don't have to pass them in code:

```bash
export ZINQ_API_KEY=zak_your_key_here        # Required
export ZINQ_WEBHOOK_SECRET=zws_your_secret   # Only for webhooks
```

```python
# No arguments needed -- reads from environment
agent = ZinqAgent()
webhook = ZinqWebhook(secret=os.environ["ZINQ_WEBHOOK_SECRET"])
```

## Async Support

Every method has an async equivalent:

```python
import asyncio
from zinq_agent import AsyncZinqAgent

async def main():
    async with AsyncZinqAgent() as agent:
        await agent.vibes.send(text="Async vibe!")

        # Streaming Gemini
        async for chunk in agent.gemini.stream_chat(
            messages=[{"role": "user", "content": "Tell me a joke"}],
        ):
            print(chunk, end="", flush=True)

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

| Example | Description | Requires Webhooks? |
|---------|-------------|-------------------|
| [`echo_bot.py`](examples/echo_bot.py) | Echoes back everything the user says | Yes |
| [`appointment_bot.py`](examples/appointment_bot.py) | Polling-based appointment scheduler | No |
| [`personal_shopper.py`](examples/personal_shopper.py) | Uses Gemini + memories for personalized recommendations | Yes |

## Documentation

Detailed guides are in the [`docs/`](docs/) directory:

- **[Getting Started](docs/getting-started.md)** -- Build your first agent in 5 minutes
- **[API Reference](docs/api-reference.md)** -- Every class, method, and parameter
- **[Webhooks](docs/webhooks.md)** -- Receive real-time events from users
- **[Examples Cookbook](docs/examples.md)** -- Copy-paste recipes for common agents
- **[Deployment](docs/deployment.md)** -- Run your agent in production
- **[Best Practices](docs/best-practices.md)** -- Tips for building great agents

Full platform docs: [docs.zinq-app.com](https://docs.zinq-app.com)

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

| Use Case | Description | Example |
|----------|-------------|---------|
| **Email AI Assistant** | Monitor Gmail/Outlook, summarize, auto-reply | [Sentinel](examples/sentinel/) |
| **Slack Bot** | Bridge Slack mentions to mobile, summarize channels | [examples/](docs/examples.md) |
| **Personal Shopper** | AI product recommendations for online stores | [personal_shopper.py](examples/personal_shopper.py) |
| **Appointment Scheduler** | Automated booking for service businesses | [appointment_bot.py](examples/appointment_bot.py) |
| **Crypto Trading Agent** | Portfolio monitoring, price alerts, P&L summaries via Binance | [trading_bot.py](examples/trading_bot.py) |
| **Fitness Coach** | Personalized workouts using diary data + Gemini | [examples](docs/examples.md) |
| **Daily Digest** | Morning briefing from email, calendar, news | [examples](docs/examples.md) |
| **IoT Monitor** | Smart home alerts via Zinq vibes | Build your own! |
| **Customer Support** | AI-first support with human handoff (Business Agent) | [docs/business-agents.md](docs/business-agents.md) |
| **Online Shop** | AI personal shopper for your brand (Business Agent) | [docs/business-agents.md](docs/business-agents.md) |
| **Appointment Booking** | Barber, spa, clinic scheduling (Business Agent) | [docs/business-agents.md](docs/business-agents.md) |

## Keywords

`ai-agent` `python-sdk` `personal-ai-assistant` `chatbot-framework` `gemini-api` `llm-agent` `conversational-ai` `email-automation` `slack-integration` `ai-shopping-assistant` `appointment-booking` `webhook-server` `agent-framework` `autonomous-agent` `ai-coach`

## Star History

If this project helps you build something cool, give it a star! It helps others discover it.

## License

MIT — do whatever you want with it.
