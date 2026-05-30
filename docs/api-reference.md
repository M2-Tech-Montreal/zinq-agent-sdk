# API Reference

Complete reference for every class, method, and model in the Zinq Agent Python SDK.

## Table of Contents

- [ZinqAgent](#zinqagent)
- [AsyncZinqAgent](#asynczinqagent)
- [agent.diary](#agentdiary) — read, search, save, star, archive diary entries
- [agent.vibes](#agentvibes) — send vibes, read received vibes
- [agent.feed](#agentfeed) — read the user's vibe feed
- [agent.contacts](#agentcontacts) — list, search, get user's connections
- [agent.zones](#agentzones) — list zones/clubs, get zone vibes, create clubs, invite
- [agent.memories](#agentmemories) — persistent key-value storage
- [agent.user](#agentuser) — user profile and preferences
- [agent.gemini](#agentgemini) — LLM chat and embeddings
- [agent.tools](#agenttools--toolsclient) — register tools that Gemini can call
- [ZinqWebhook](#zinqwebhook) — receive events from Zinq
- [Models](#models)
- [Exceptions](#exceptions)

---

## ZinqAgent

The main entry point for the SDK. Creates an authenticated client with sub-clients for each API domain.

```python
from zinq_agent import ZinqAgent

agent = ZinqAgent(
    api_key="zak_xxxxx",                        # or set ZINQ_API_KEY env var
    base_url="https://zinq-app.com/api",         # default
    max_retries=2,                               # default, retries on transient failures
    timeout=30.0,                                # default, seconds per request
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str \| None` | `None` | Agent API key with `zak_` prefix. If not provided, reads from `ZINQ_API_KEY` environment variable. |
| `base_url` | `str` | `"https://zinq-app.com/api"` | Zinq backend URL. Change this for staging or local development. |
| `max_retries` | `int` | `2` | Number of automatic retries on transient HTTP failures (connection errors, 502/503/504). |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds. Increase for slow connections or large responses. |

### Sub-clients

| Property | Type | Description |
|----------|------|-------------|
| `agent.diary` | `DiaryClient` | Read diary entries and search |
| `agent.vibes` | `VibeClient` | Send and receive vibes |
| `agent.memories` | `MemoryClient` | Persistent key-value storage |
| `agent.user` | `UserClient` | User profile and preferences |
| `agent.gemini` | `GeminiClient` | Gemini LLM proxy |

### Methods

#### `agent.close()`

Close the underlying HTTP connection. Call this when you're done using the agent.

```python
agent = ZinqAgent()
# ... use agent ...
agent.close()
```

#### Context Manager

Automatically closes the connection when the block exits:

```python
with ZinqAgent() as agent:
    agent.vibes.send(text="Hello!")
# Connection is closed here
```

---

## AsyncZinqAgent

Async variant of `ZinqAgent`. Same constructor parameters, same sub-clients, but all methods are `async`.

```python
import asyncio
from zinq_agent import AsyncZinqAgent

async def main():
    async with AsyncZinqAgent() as agent:
        page = await agent.diary.list()
        await agent.vibes.send(text="Async hello!")

asyncio.run(main())
```

The async client also provides `agent.gemini.stream_chat()` for streaming Gemini responses (see [Gemini section](#agentgemini)).

---

## agent.diary

Read the user's diary entries and perform semantic search.

### `diary.list(**kwargs) -> DiaryPage`

Fetch diary entries with optional filters. Returns a paginated result.

```python
page = agent.diary.list(
    start="2026-04-01",       # ISO date, earliest entry (inclusive)
    end="2026-04-19",         # ISO date, latest entry (inclusive)
    tags=["fitness", "food"], # Filter by AI tags
    page=0,                   # Page number (0-indexed)
    size=20,                  # Page size (max 100)
)

for entry in page.entries:
    print(f"{entry.created_at}: {entry.text}")

print(f"Page {page.page + 1} of {page.total_pages}")
print(f"Total entries: {page.total_entries}")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start` | `str \| None` | `None` | ISO date string for earliest entry (e.g., `"2026-04-01"`). |
| `end` | `str \| None` | `None` | ISO date string for latest entry. |
| `tags` | `list[str] \| None` | `None` | Filter by AI tags (e.g., `["fitness", "nutrition"]`). |
| `page` | `int` | `0` | Page number, 0-indexed. |
| `size` | `int` | `20` | Number of entries per page (max 100). |

**Returns:** [`DiaryPage`](#diarypage)

### `diary.iter(**kwargs) -> Iterator[DiaryEntry]`

Auto-paginating iterator. Fetches pages automatically until all matching entries are returned. This is the easiest way to iterate over all entries.

```python
for entry in agent.diary.iter(start="2026-04-01", tags=["fitness"]):
    print(entry.text)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start` | `str \| None` | `None` | ISO date string for earliest entry. |
| `end` | `str \| None` | `None` | ISO date string for latest entry. |
| `tags` | `list[str] \| None` | `None` | Filter by AI tags. |
| `size` | `int` | `50` | Page size per request (max 100). |

**Yields:** [`DiaryEntry`](#diaryentry) objects in reverse chronological order.

> Note: `iter()` is only available on the sync client. The async client does not have an async equivalent yet -- use `await diary.list()` in a loop instead.

### `diary.search(query, **kwargs) -> SearchResults`

Semantic search over the user's diary using embeddings. This uses the user's credits.

```python
results = agent.diary.search(
    "morning workouts",   # Natural language query
    limit=10,             # Max results (default 10, max 50)
    start="2026-04-01",   # Optional date filter
    end="2026-04-19",
)

for r in results.results:
    print(f"[{r.similarity:.0%}] {r.text}")

print(f"Credits used: {results.embedding_credits_used}")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | (required) | Natural language search query. |
| `limit` | `int` | `10` | Maximum number of results (max 50). |
| `start` | `str \| None` | `None` | ISO date string for earliest entry. |
| `end` | `str \| None` | `None` | ISO date string for latest entry. |

**Returns:** [`SearchResults`](#searchresults)

### `agent.diary.save(text, *, mood_score=None)`

Save a new entry to the user's diary.

```python
agent.diary.save("Had a great meditation session today", mood_score=8)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | (required) | The diary entry text. |
| `mood_score` | `int \| None` | `None` | Optional mood score 1-10. |

**Returns:** `dict` with `vibe_id` of the created entry.

### `agent.diary.star(vibe_id, *, rating=1)`

Star/save a vibe to the diary.

```python
agent.diary.star(vibe_id=4127)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `vibe_id` | `int` | (required) | The vibe to star. |
| `rating` | `int` | `1` | Star rating. |

**Returns:** `dict` confirmation.

### `agent.diary.archive(vibe_id)`

Archive a vibe (soft delete from diary).

```python
agent.diary.archive(vibe_id=4127)
```

**Returns:** `dict` confirmation.

---

## agent.feed

Read the user's vibe feed — vibes from their connections.

```python
vibes = agent.feed.list(limit=10)
for v in vibes:
    print(f"{v.user_name}: {v.text or v.transcript_summary}")
```

### `agent.feed.list(*, limit=20, offset=0)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | `int` | `20` | Max results per page. |
| `offset` | `int` | `0` | Pagination offset. |

**Returns:** `list[`[`Vibe`](#vibe)`]`

---

## agent.contacts

Read the user's connections. Requires the `contacts` data access permission.

```python
contacts = agent.contacts.list()
for c in contacts:
    print(f"{c.name} — {c.presence_status}")

# Search by name
results = agent.contacts.search("Glenn")
```

### `agent.contacts.list(*, limit=50, offset=0)`

List the user's connections.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | `int` | `50` | Max results (max 200). |
| `offset` | `int` | `0` | Pagination offset. |

**Returns:** `list[`[`Contact`](#contact)`]`

### `agent.contacts.search(query, *, limit=10)`

Search contacts by name (case-insensitive partial match).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | (required) | Name to search for. |
| `limit` | `int` | `10` | Max results. |

**Returns:** `list[`[`Contact`](#contact)`]`

### `agent.contacts.get(contact_id)`

Get a single contact by ID.

**Returns:** [`Contact`](#contact)

---

## agent.zones

Read and manage the user's zones (life zones and clubs).

```python
# List all zones
zones = agent.zones.list()
for z in zones:
    print(f"{z.name} ({z.zone_type}) — {z.member_count} members")

# Get vibes from a club
vibes = agent.zones.vibes(zone_id=42, limit=20)

# Create a club
new_club = agent.zones.create("Book Club", description="Monthly reads")

# Invite members
agent.zones.invite(zone_id=new_club.id, user_ids=[1130, 1129])
```

### `agent.zones.list()`

List all of the user's zones (life zones + clubs).

**Returns:** `list[`[`Zone`](#zone)`]`

### `agent.zones.vibes(zone_id, *, limit=20, offset=0)`

Get vibes from a specific zone or club.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `zone_id` | `int` | (required) | The zone/club ID. |
| `limit` | `int` | `20` | Max results. |
| `offset` | `int` | `0` | Pagination offset. |

**Returns:** `list[`[`Vibe`](#vibe)`]`

### `agent.zones.create(name, *, zone_type="club", description=None)`

Create a new zone or club.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | (required) | Display name. |
| `zone_type` | `str` | `"club"` | `"life"`, `"club"`, or `"event"`. |
| `description` | `str \| None` | `None` | Optional description. |

**Returns:** [`Zone`](#zone)

### `agent.zones.invite(zone_id, user_ids)`

Invite users to a club/zone.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `zone_id` | `int` | (required) | The club/zone ID. |
| `user_ids` | `list[int]` | (required) | User IDs to invite. |

**Returns:** `dict` confirmation.

---

## agent.vibes

Send vibes to the user and read vibes they sent to the agent.

### `vibes.send(text, **kwargs) -> VibeSendResult`

Send a vibe (message) from the agent to the user. The user sees this in their Zinq app.

```python
# Simple text vibe
result = agent.vibes.send(text="Time for your walk!")
print(f"Vibe ID: {result.vibe_id}")
print(f"Push notification sent: {result.push_sent}")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | (required) | Vibe text content (max 10,000 characters). |
| `vibe_type` | `str` | `"TEXT"` | `"TEXT"` (default) or `"NOTIFICATION"`. |
| `input_type` | `str \| None` | `None` | Interactive input: `"yes_no"`, `"choice"`, `"text_input"`, or `"rating"`. |
| `options` | `list[str] \| None` | `None` | Options for `"choice"` input type. |
| `buttons` | `list[dict] \| None` | `None` | Up to 4 buttons, each with `"label"` and `"value"` keys. |
| `reply_to` | `int \| None` | `None` | Vibe ID to reply to (creates a threaded reply). |
| `metadata` | `dict \| None` | `None` | Arbitrary JSON stored with the vibe (max 4KB). |

**Returns:** [`VibeSendResult`](#vibesendresult)

#### Interactive vibes

Interactive vibes let the user respond with structured input:

```python
# Yes/No question
agent.vibes.send(text="Did you work out today?", input_type="yes_no")

# Multiple choice
agent.vibes.send(
    text="Which workout?",
    input_type="choice",
    options=["Upper body", "Lower body", "Cardio", "Rest day"],
)

# Free text input
agent.vibes.send(text="What did you eat for lunch?", input_type="text_input")

# Star rating
agent.vibes.send(text="Rate your sleep last night:", input_type="rating")

# Custom buttons
agent.vibes.send(
    text="Your weekly report is ready.",
    buttons=[
        {"label": "View Report", "value": "view_report"},
        {"label": "Remind Me Later", "value": "remind_later"},
    ],
)
```

When the user responds, you get a `vibe.reply` webhook event with the `button_value` or response text.

#### Threaded replies

Reply to a specific vibe to create a conversation thread:

```python
# Reply to a user's vibe
vibes = agent.vibes.received(unread=True)
for vibe in vibes:
    agent.vibes.send(text=f"Got it: {vibe.text}", reply_to=vibe.id)
```

### `vibes.received(**kwargs) -> list[Vibe]`

Get vibes sent to this agent by the user.

```python
# Get all unread vibes
vibes = agent.vibes.received(unread=True)

# Get vibes since a specific time
vibes = agent.vibes.received(since="2026-04-19T12:00:00Z", limit=50)

for vibe in vibes:
    print(f"[{vibe.created_at}] {vibe.text or vibe.transcript}")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `since` | `str \| None` | `None` | ISO datetime string. Only return vibes after this timestamp. |
| `limit` | `int` | `20` | Maximum number of results (max 100). |
| `unread` | `bool` | `False` | If `True`, only return unread vibes. |

**Returns:** `list[`[`Vibe`](#vibe)`]`

---

## agent.memories

Persistent key-value storage scoped to this agent and user. Use memories to store preferences, history, state, or anything your agent needs to remember between runs.

Limits: max 500 memories per agent per user, max 100-char keys, max 10KB values.

### `memories.list(**kwargs) -> list[Memory]`

List all memories, optionally filtered by category.

```python
# All memories
all_mems = agent.memories.list()

# Filter by category
health_mems = agent.memories.list(category="health")

for mem in health_mems:
    print(f"{mem.key}: {mem.value} (updated {mem.updated_at})")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | `str \| None` | `None` | Filter by category string. |

**Returns:** `list[`[`Memory`](#memory)`]`

### `memories.get(key) -> Memory | None`

Get a specific memory by key. Returns `None` if the key doesn't exist.

```python
mem = agent.memories.get("diet")
if mem:
    print(f"Diet preference: {mem.value}")
else:
    print("No diet preference saved")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | The memory key to look up. |

**Returns:** [`Memory`](#memory) or `None`

### `memories.save(key, value, **kwargs) -> MemorySaveResult`

Save or update a memory (upsert). If the key exists, its value is overwritten.

```python
result = agent.memories.save(
    key="diet",
    value="vegetarian",
    category="health",
)

if result.created:
    print("New memory created")
else:
    print(f"Memory updated at {result.updated_at}")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | (required) | Memory key (max 100 chars, unique per agent+user). |
| `value` | `str` | (required) | Memory value (max 10KB). |
| `category` | `str \| None` | `None` | Optional category for grouping (max 50 chars). |

**Returns:** [`MemorySaveResult`](#memorysaveresult)

### `memories.delete(key) -> None`

Delete a specific memory by key.

```python
agent.memories.delete("old_preference")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | The memory key to delete. |

**Raises:** [`NotFoundError`](#notfounderror) if the key doesn't exist.

---

## agent.user

Read the user's profile information and preferences.

### `user.context() -> UserContext`

Get the user's profile, preferences, and credit status.

```python
ctx = agent.user.context()

# Basic profile
print(f"Name: {ctx.name}")
print(f"Timezone: {ctx.timezone}")
print(f"Locale: {ctx.locale}")

# Credit status
credits = ctx.credit_status
print(f"Credits: {credits.credits_remaining}/{credits.monthly_limit}")
print(f"Tier: {credits.tier}")
print(f"Resets: {credits.reset_date}")

# Agent preferences (may be None)
if ctx.agent_preferences:
    hours = ctx.agent_preferences.notification_hours
    if hours:
        print(f"Notify between: {hours.start}:00-{hours.end}:00")
    print(f"Response length: {ctx.agent_preferences.preferred_response_length}")
```

**Returns:** [`UserContext`](#usercontext)

### `user.profile() -> dict`

Get the agent's own profile.

```python
profile = agent.user.profile()
print(f"Name: {profile['name']}")
print(f"Bio: {profile.get('bio', '')}")
print(f"Key: {profile.get('apiKeyPrefix', '')}...")
```

### `user.update_profile(**kwargs) -> dict`

Update the agent's own profile. Only provided fields are changed.

| Parameter | Type | Description |
|-----------|------|-------------|
| name | str | Display name (3-50 chars) |
| nickname | str | Short name |
| bio | str | One-line description (max 200 chars) |
| avatar_url | str | Profile image URL |

```python
agent.user.update_profile(
    name="Budget Buddy",
    bio="Tracks your spending habits",
    nickname="BB",
)
```

---

## agent.gemini

Call Zinq's managed Gemini LLM proxy. This is optional -- you can use any AI provider you want. When you use Zinq's proxy, credits are deducted from the user's account.

### `gemini.chat(messages, **kwargs) -> GeminiResponse | Iterator[str]`

Send a conversation to Gemini and get a response.

```python
# Non-streaming
response = agent.gemini.chat(
    messages=[
        {"role": "system", "content": "You are a fitness coach."},
        {"role": "user", "content": "What should I eat after a run?"},
    ],
    model="flash",          # "flash" (cheap) or "pro" (better)
    temperature=0.7,         # 0.0 = deterministic, 1.0 = creative
    max_tokens=2048,         # Max response length
)

print(response.text)
print(f"Model: {response.model}")
print(f"Tokens: {response.usage.total_tokens}")
print(f"Credits: {response.usage.credits_used}")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `messages` | `list[dict]` | (required) | Conversation history. Each dict has `"role"` (`"system"`, `"user"`, or `"assistant"`) and `"content"` (string). |
| `stream` | `bool` | `False` | If `True`, return a streaming iterator of text chunks (sync client only). |
| `model` | `str` | `"flash"` | `"flash"` (faster, cheaper) or `"pro"` (higher quality). |
| `temperature` | `float` | `0.7` | Sampling temperature, 0.0-1.0. |
| `max_tokens` | `int` | `2048` | Maximum response tokens (max 8192). |
| `tools` | `list[dict] \| None` | `None` | Function-calling tool definitions in Gemini format. |

**Returns:** [`GeminiResponse`](#geminiresponse) if `stream=False`, or `Iterator[str]` if `stream=True`.

#### Streaming (sync)

```python
for chunk in agent.gemini.chat(
    messages=[{"role": "user", "content": "Write a haiku about Python"}],
    stream=True,
):
    print(chunk, end="", flush=True)
print()  # Final newline
```

#### Streaming (async)

The async client has a separate `stream_chat()` method:

```python
async for chunk in agent.gemini.stream_chat(
    messages=[{"role": "user", "content": "Write a haiku"}],
):
    print(chunk, end="", flush=True)
```

### `gemini.embed(text, **kwargs) -> EmbeddingResponse`

Generate an embedding vector for semantic search or similarity comparison.

```python
result = agent.gemini.embed("morning yoga routine")

print(f"Dimensions: {result.dimensions}")       # 768
print(f"Vector length: {len(result.embedding)}") # 768
print(f"Credits used: {result.credits_used}")    # 1
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | (required) | Text to embed (max 2048 chars). |
| `task_type` | `str` | `"RETRIEVAL_QUERY"` | `"RETRIEVAL_QUERY"` for search queries, `"RETRIEVAL_DOCUMENT"` for documents to search over. |

**Returns:** [`EmbeddingResponse`](#embeddingresponse)

---

## `agent.tools` — ToolsClient

Register tools that Zinq's Gemini can call on behalf of users. When a user messages your agent, Gemini sees the registered tools and calls them when appropriate. The backend POSTs to your webhook URL with the extracted arguments.

### `agent.tools.register(*, name, description, webhook_url, parameters=None)`

Register a tool.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | Yes | Tool name (e.g. `"get_weather"`) |
| `description` | `str` | Yes | What the tool does. Gemini uses this to decide when to call it. |
| `webhook_url` | `str` | Yes | HTTPS URL that receives tool call POSTs. |
| `parameters` | `str` | No | JSON schema string for parameters. |

Returns: `dict` with `id` and `name`.

### `agent.tools.list()`

List all registered tools.

Returns: `list[dict]` with `id`, `name`, `description`, `webhookUrl`, `parameters`.

### `agent.tools.remove(tool_id)`

Remove a registered tool.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool_id` | `int` | Yes | Tool ID from `register()` or `list()`. |

### Tool webhook payload

When Gemini calls your tool, your webhook receives a POST:

```json
{
  "userId": 1147,
  "symbol": "AAPL",
  "side": "buy",
  "quantity": 10
}
```

Your server should return a JSON response with the result:

```json
{
  "status": "filled",
  "price": 195.50,
  "orderId": "ORD-1234"
}
```

Gemini receives this result and summarizes it for the user.

### Reserved tool name: `wave`

If you register a tool named `wave`, it gets called automatically when a user **opens the chat** (wave). This is the agent's first impression — show current state.

**No Gemini involved for waves.** The backend calls your `status` endpoint directly and sends the response as a vibe.

```python
agent.tools.register(
    name="wave",
    description="Current agent status summary",
    webhook_url="https://my-server.com/tools/status",
)
```

Your server receives:

```json
{
  "userId": 1147,
  "event": "wave"
}
```

Return a `message` field with the greeting:

```json
{
  "message": "Kaspr running. +1 ESM6 overnight, entered 5450.25. Next flatten: Mon 09:29 ET."
}
```

This becomes the wave response. If you don't register a `wave` tool, the agent sends a generic "Hi! How can I help?"

**Important:** The `wave` tool is for waves only. It is NOT called by Gemini during regular conversations. Register your other tools separately for Gemini to use during chat.

---

## ZinqWebhook

Webhook server for receiving real-time events from the Zinq platform.

```python
from zinq_agent import ZinqWebhook

webhook = ZinqWebhook(
    secret="dev",
    skip_signature_check=True,    # Signature verification coming soon
)
```

> **Note:** Webhook signing secrets (`zws_...`) are not yet available. Use `skip_signature_check=True` for now. HMAC-SHA256 signature verification will be added in a future release.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `secret` | `str` | (required) | Any string value. `zws_` webhook secrets are not yet available — use `skip_signature_check=True`. |
| `skip_signature_check` | `bool` | `False` | Skip signature verification. Set to `True` (required until webhook secrets are available). |

### `webhook.on(event_type) -> decorator`

Register a handler for a specific event type. Use as a decorator.

```python
@webhook.on("vibe.received")
def handle_vibe(event):
    print(f"User said: {event.data.text}")
```

Valid event types:

| Event Type | When It Fires | Data Model |
|------------|---------------|------------|
| `"vibe.received"` | User sends a vibe to the agent | [`VibeReceivedData`](#vibereceiveddata) |
| `"charm.received"` | User reacts with a charm (emoji) | [`CharmReceivedData`](#charmreceiveddata) |
| `"agent.wave"` | User opens the agent chat | [`AgentWaveData`](#agentwavedata) |
| `"vibe.reply"` | User replies to an agent vibe or taps a button | [`VibeReplyData`](#vibereplydata) |

You can register multiple handlers for the same event type -- they all run.

### `webhook.start(**kwargs)`

Start the built-in Flask development server. This is a blocking call.

```python
webhook.start(
    host="0.0.0.0",    # Bind address
    port=8080,          # Listen port
    path="/webhook",    # Webhook URL path
    debug=False,        # Flask debug mode
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | `str` | `"0.0.0.0"` | Host to bind to. |
| `port` | `int` | `8080` | Port to listen on. |
| `path` | `str` | `"/webhook"` | URL path for the webhook endpoint. |
| `debug` | `bool` | `False` | Enable Flask debug mode. |

### `webhook.create_flask_app(**kwargs) -> Flask`

Create a Flask app with the webhook endpoint configured. Use this for production deployments with a WSGI server.

```python
webhook = ZinqWebhook(secret="dev", skip_signature_check=True)

@webhook.on("vibe.received")
def handle(event):
    pass

app = webhook.create_flask_app(path="/webhook")
# Run with: gunicorn -b 0.0.0.0:8080 my_agent:app
```

### `webhook.verify_signature(payload, signature_header, timestamp_header) -> bool`

Manually verify a webhook signature. Useful if you're integrating with a non-Flask web framework.

```python
is_valid = webhook.verify_signature(
    payload=request_body_bytes,
    signature_header=headers["X-Zinq-Signature"],
    timestamp_header=headers.get("X-Zinq-Timestamp"),
)
```

### `webhook.handle_request(body, headers) -> tuple[str, int]`

Process a raw webhook request. Framework-agnostic -- works with any web server.

```python
response_body, status_code = webhook.handle_request(
    body=raw_bytes,
    headers={"X-Zinq-Signature": "sha256=...", "X-Zinq-Timestamp": "1234567890"},
)
```

**Returns:** Tuple of `(response_body_string, http_status_code)`.

---

## Models

All API responses are parsed into Pydantic models. Field names use `snake_case` (Python convention); the API returns `camelCase`, and the SDK handles the conversion automatically.

### DiaryEntry

A single diary vibe entry.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Entry ID |
| `text` | `str \| None` | Text content |
| `transcript` | `str \| None` | Voice transcript |
| `media_type` | `str \| None` | Media type (e.g., `"VIDEO"`, `"PHOTO"`) |
| `media_url` | `str \| None` | URL to media file |
| `ai_tags` | `list[str]` | AI-generated tags (e.g., `["fitness", "outdoor"]`) |
| `created_at` | `datetime` | When the entry was created |

### DiaryPage

Paginated diary response.

| Field | Type | Description |
|-------|------|-------------|
| `entries` | `list[DiaryEntry]` | Diary entries on this page |
| `page` | `int` | Current page number (0-indexed) |
| `total_pages` | `int` | Total number of pages |
| `total_entries` | `int` | Total number of matching entries |

### SearchResult

A single result from diary semantic search.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Entry ID |
| `text` | `str \| None` | Text content |
| `ai_tags` | `list[str]` | AI tags |
| `similarity` | `float` | Similarity score (0.0 to 1.0, higher is more relevant) |
| `created_at` | `datetime` | When the entry was created |

### SearchResults

Container for diary search results.

| Field | Type | Description |
|-------|------|-------------|
| `results` | `list[SearchResult]` | Ranked search results |
| `query` | `str` | The original search query |
| `embedding_credits_used` | `int` | Credits consumed by this search |

### Vibe

A vibe sent to the agent by the user.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Vibe ID |
| `type` | `str` | Vibe type (e.g., `"TEXT"`, `"VIDEO"`) |
| `text` | `str \| None` | Text content |
| `transcript` | `str \| None` | Voice/video transcript |
| `media_url` | `str \| None` | URL to media file |
| `charm_emoji` | `str \| None` | Charm (emoji reaction) if any |
| `reply_to_vibe_id` | `int \| None` | ID of the vibe this replies to |
| `created_at` | `datetime` | When the vibe was created |

### VibeSendResult

Result of sending a vibe to the user.

| Field | Type | Description |
|-------|------|-------------|
| `vibe_id` | `int` | ID of the sent vibe |
| `delivered_at` | `datetime` | Delivery timestamp |
| `push_sent` | `bool` | Whether a push notification was sent |

### Memory

A persistent key-value memory.

| Field | Type | Description |
|-------|------|-------------|
| `key` | `str` | Memory key |
| `value` | `str` | Memory value |
| `category` | `str \| None` | Category for grouping |
| `updated_at` | `datetime` | Last update timestamp |

### MemorySaveResult

Result of saving or updating a memory.

| Field | Type | Description |
|-------|------|-------------|
| `key` | `str` | Memory key |
| `created` | `bool` | `True` if this was a new key, `False` if updated |
| `updated_at` | `datetime` | Timestamp of the save |

### UserContext

User profile and preferences.

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | `int` | User ID |
| `name` | `str` | Display name |
| `nickname` | `str \| None` | Nickname |
| `timezone` | `str` | IANA timezone (e.g., `"America/New_York"`) |
| `locale` | `str \| None` | Locale code (e.g., `"en-US"`) |
| `country_code` | `str \| None` | ISO country code (e.g., `"US"`) |
| `agent_preferences` | `AgentPreferences \| None` | Agent interaction preferences |
| `credit_status` | `CreditStatus` | Credit balance and tier |

### Contact

A user's connection.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Connection ID |
| `name` | `str` | Display name |
| `nickname` | `str \| None` | Nickname |
| `avatar_url` | `str \| None` | Avatar image URL |
| `zone_name` | `str \| None` | Zone this connection belongs to |
| `zone_type` | `str \| None` | `"life"`, `"club"`, `"event"` |
| `connection_type` | `str \| None` | How connected (`"nfc_tap"`, `"tap_link"`, etc.) |
| `last_active` | `datetime \| None` | Last activity timestamp |
| `presence_status` | `str \| None` | `"online"`, `"away"`, `"grey"` |
| `is_system` | `bool` | Whether this is a system/agent connection |

### Zone

A user's zone (life zone or club).

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Zone ID |
| `name` | `str` | Display name |
| `zone_type` | `str` | `"life"`, `"club"`, or `"event"` |
| `member_count` | `int` | Number of active members |
| `is_owner` | `bool` | Whether the user owns this zone |
| `description` | `str \| None` | Zone description |
| `avatar_url` | `str \| None` | Zone avatar URL |

### AgentPreferences

User's agent interaction preferences.

| Field | Type | Description |
|-------|------|-------------|
| `notification_hours` | `NotificationHours \| None` | Preferred hours for notifications |
| `preferred_response_length` | `str \| None` | Preferred response length (e.g., `"concise"`, `"detailed"`) |

### NotificationHours

Preferred notification window.

| Field | Type | Description |
|-------|------|-------------|
| `start` | `int` | Start hour (0-23, inclusive) |
| `end` | `int` | End hour (0-23, inclusive) |

### CreditStatus

User's credit balance and subscription tier.

| Field | Type | Description |
|-------|------|-------------|
| `credits_remaining` | `int` | Credits available this month |
| `monthly_limit` | `int` | Monthly credit cap |
| `tier` | `str` | Subscription tier (e.g., `"free"`, `"pro"`) |
| `reset_date` | `datetime` | When credits reset |

### GeminiResponse

Response from the Gemini LLM proxy.

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Generated text content |
| `tool_calls` | `list[dict]` | Function call results (if tools were provided) |
| `usage` | `GeminiUsage` | Token usage and credit cost |
| `model` | `str` | Model used (e.g., `"gemini-2.0-flash"`) |

### GeminiUsage

Token usage for a Gemini call.

| Field | Type | Description |
|-------|------|-------------|
| `prompt_tokens` | `int` | Tokens in the prompt |
| `completion_tokens` | `int` | Tokens in the response |
| `total_tokens` | `int` | Total tokens used |
| `credits_used` | `int` | Credits deducted from user's account |

### EmbeddingResponse

Response from the embedding endpoint.

| Field | Type | Description |
|-------|------|-------------|
| `embedding` | `list[float]` | The embedding vector |
| `dimensions` | `int` | Vector dimensionality (e.g., 768) |
| `credits_used` | `int` | Credits consumed |

### WebhookEvent

A parsed webhook event.

| Field | Type | Description |
|-------|------|-------------|
| `event` | `str` | Event type (e.g., `"vibe.received"`) |
| `delivery_id` | `str` | Unique delivery ID for deduplication |
| `timestamp` | `datetime` | When the event occurred |
| `agent` | `WebhookAgent` | Agent identity |
| `user` | `WebhookUser` | User identity |
| `data` | varies | Typed data payload (see below) |

### WebhookAgent

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Agent ID |
| `name` | `str` | Agent name |

### WebhookUser

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | User ID |
| `name` | `str` | User name |
| `timezone` | `str \| None` | User's timezone |

### VibeReceivedData

Data for `vibe.received` events.

| Field | Type | Description |
|-------|------|-------------|
| `vibe_id` | `int` | Vibe ID |
| `type` | `str` | Vibe type (`"TEXT"`, `"VIDEO"`, etc.) |
| `text` | `str \| None` | Text content |
| `transcript` | `str \| None` | Voice/video transcript |
| `media_url` | `str \| None` | Media URL |
| `media_type` | `str \| None` | Media type |
| `duration` | `int \| None` | Media duration in seconds |
| `created_at` | `datetime` | Creation time |

### CharmReceivedData

Data for `charm.received` events.

| Field | Type | Description |
|-------|------|-------------|
| `charm_id` | `int` | Charm ID |
| `emoji` | `str` | Emoji identifier |
| `vibe_id` | `int` | Vibe the charm was applied to |
| `created_at` | `datetime` | Creation time |

### AgentWaveData

Data for `agent.wave` events.

| Field | Type | Description |
|-------|------|-------------|
| `is_first_wave` | `bool` | `True` if this is the user's first time opening the agent chat |
| `last_interaction_at` | `datetime \| None` | Last interaction timestamp, or `None` if first wave |

### VibeReplyData

Data for `vibe.reply` events.

| Field | Type | Description |
|-------|------|-------------|
| `vibe_id` | `int` | Reply vibe ID |
| `type` | `str` | Reply type |
| `text` | `str \| None` | Reply text |
| `reply_to_vibe_id` | `int \| None` | ID of the vibe being replied to |
| `button_value` | `str \| None` | Value of the button that was tapped (if interactive vibe) |
| `created_at` | `datetime` | Creation time |

---

## Exceptions

All SDK exceptions inherit from `ZinqError`, so you can catch broadly or narrowly.

### ZinqError

Base exception for all SDK errors.

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Human-readable error description |
| `status_code` | `int \| None` | HTTP status code (if applicable) |

### AuthenticationError

Raised when the API key is invalid, revoked, or missing (HTTP 401).

```python
from zinq_agent import AuthenticationError

try:
    agent = ZinqAgent(api_key="zak_bad_key")
    agent.diary.list()
except AuthenticationError as e:
    print(f"Bad API key: {e.message}")
```

### RateLimitError

Raised when the agent exceeds the rate limit (HTTP 429).

| Attribute | Type | Description |
|-----------|------|-------------|
| `retry_after` | `float` | Seconds until the next request is allowed |

```python
from zinq_agent import RateLimitError

try:
    agent.vibes.send(text="spam")
except RateLimitError as e:
    print(f"Slow down! Retry in {e.retry_after} seconds.")
```

### InsufficientCreditsError

Raised when the user doesn't have enough credits for a Gemini call (HTTP 402).

| Attribute | Type | Description |
|-----------|------|-------------|
| `credits_remaining` | `int` | Credits the user currently has |
| `credits_required` | `int` | Credits needed for the operation |

```python
from zinq_agent import InsufficientCreditsError

try:
    agent.gemini.chat(messages=[...])
except InsufficientCreditsError as e:
    print(f"Need {e.credits_required}, have {e.credits_remaining}")
    agent.vibes.send(text="Sorry, you're out of AI credits this month!")
```

### NotFoundError

Raised when a requested resource doesn't exist (HTTP 404).

### ValidationError

Raised when request parameters are invalid (HTTP 422).

### ServerError

Raised when the Zinq backend returns a 5xx error. This is usually transient -- retry after a moment.
