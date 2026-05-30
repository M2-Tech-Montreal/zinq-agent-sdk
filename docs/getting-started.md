# Getting Started

Build your first Zinq agent in under 5 minutes.

## Prerequisites

- **Python 3.10 or higher** -- check with `python --version`
- **A Zinq account** -- [download Zinq from the App Store](https://apps.apple.com/us/app/zinq-ai-agent-suite-diary/id6760369400) and sign up
- **An agent API key** -- you'll create this in the next step

## Step 1: Create Your Agent

1. Open the Zinq app → **Agents** tab → tap **+** (create)
2. Name your agent (e.g. "Sentinel") → tap **Create**
3. Copy the `zak_` API key — save it somewhere safe

> Your API key looks like this: `zak_a1b2c3d4e5f6...` (64 characters after the prefix).
> Keep it secret. Anyone with this key can act as your agent.

To **delete** an agent: **Agents** tab → find your agent → long-press → **Delete**. The API key is invalidated immediately.

To **start fresh**: delete the old agent, create a new one, and use the new `zak_` key.

**Assign a zone**: Your agent starts in the default zinq zone. To organize it, go to your **connections** → find the agent → assign it to a zone (e.g. "Agents", "Work", or any custom zone). This controls where it appears in your Presence Bar and chat filters.

## Step 2: Install the SDK

```bash
pip install zinq-agent
```

That's it. The SDK has only two dependencies (`httpx` and `pydantic`) and installs in seconds.

If you want webhook support (to receive events in real time), add the webhook extra:

```bash
pip install zinq-agent[webhook]
```

## Step 3: Set Your API Key

The easiest approach is to set an environment variable:

```bash
export ZINQ_API_KEY=zak_your_key_here
```

The SDK reads this automatically. You can also pass the key directly in code (useful for testing, but don't commit it to version control):

```python
agent = ZinqAgent(api_key="zak_your_key_here")
```

## Step 4: Write Your First Agent

Create a file called `my_agent.py`:

```python
from zinq_agent import ZinqAgent

# Connects using ZINQ_API_KEY from environment
agent = ZinqAgent()

# Say hello
agent.vibes.send(text="Hello from my first agent!")

# Check who we're connected to
ctx = agent.user.context()
print(f"Connected to: {ctx.name}")
print(f"Timezone: {ctx.timezone}")
print(f"Credits remaining: {ctx.credit_status.credits_remaining}")

# Read recent diary entries
page = agent.diary.list(size=5)
for entry in page.entries:
    print(f"  [{entry.created_at.strftime('%b %d')}] {entry.text}")

agent.close()
```

## Step 5: Register Tools (Optional)

Give your agent capabilities that Gemini can call:

```python
agent.tools.register(
    name="check_weather",
    description="Get current weather for a city",
    webhook_url="https://your-server.com/tools/weather",
)
```

When users ask about weather, Gemini will call your endpoint automatically.
See [API Reference — Tools](api-reference.md#agenttools--toolsclient) for full details.

## Step 6: Run It

```bash
python my_agent.py
```

You should see output like:

```
Connected to: Alex
Timezone: America/New_York
Credits remaining: 95
  [Apr 19] Morning run in the park
  [Apr 18] Had a great lunch with friends
  ...
```

## Step 7: Check Your Zinq App

Open the Zinq app on your phone. You should see a new vibe from your agent: **"Hello from my first agent!"**

Congratulations -- your agent is alive!

## What Just Happened?

Here's what each line did:

1. `ZinqAgent()` -- Created a client that authenticates with your API key. It sets up an HTTP connection to the Zinq backend.

2. `agent.vibes.send(text=...)` -- Sent a vibe (message) from your agent to the user. The user sees this in their Zinq app.

3. `agent.user.context()` -- Fetched the user's profile: their name, timezone, notification preferences, and credit balance.

4. `agent.diary.list(size=5)` -- Fetched the 5 most recent diary entries. Diary entries are vibes the user has recorded for themselves.

5. `agent.close()` -- Closed the HTTP connection. You can also use `with ZinqAgent() as agent:` to do this automatically.

## Next Steps

### Make it interactive with webhooks

The example above is a one-shot script. To build an agent that responds to the user in real time, you need webhooks:

```python
from zinq_agent import ZinqAgent, ZinqWebhook

agent = ZinqAgent()
webhook = ZinqWebhook(secret="dev", skip_signature_check=True)

@webhook.on("vibe.received")
def handle_vibe(event):
    text = event.data.transcript or event.data.text or ""
    agent.vibes.send(text=f"You said: {text}")

@webhook.on("agent.wave")
def greet(event):
    agent.vibes.send(text="Hey! I'm your agent. Say something!")

webhook.start(port=8080)
```

See the [Webhooks guide](webhooks.md) for the full setup.

### Make it smart with Gemini

Use Zinq's built-in Gemini proxy to add AI capabilities:

```python
response = agent.gemini.chat(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What's a good post-run snack?"},
    ],
)
agent.vibes.send(text=response.text)
```

See the [API Reference](api-reference.md) for all Gemini options.

### Make it remember with memories

Store persistent preferences and data:

```python
agent.memories.save(key="favorite_food", value="sushi", category="preferences")

# Later, in another run...
mem = agent.memories.get("favorite_food")
print(mem.value)  # "sushi"
```

### Browse the examples

Check out complete working agents in the [Examples Cookbook](examples.md).

### Deploy it

When you're ready to run your agent 24/7, see the [Deployment guide](deployment.md).
