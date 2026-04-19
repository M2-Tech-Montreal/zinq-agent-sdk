# Marketplace Agent Admin

The `ZinqMarketplaceAdmin` client lets marketplace agent owners manage their agent programmatically: deploy YAML definitions, view users, reply to conversations, send broadcasts, and manage data collections.

## Setup

```python
from zinq_agent import ZinqMarketplaceAdmin

# Pass key directly
admin = ZinqMarketplaceAdmin(api_key="zbk_xxxxx")

# Or read from ZINQ_BIZ_KEY environment variable
admin = ZinqMarketplaceAdmin()

# Context manager (auto-closes connections)
with ZinqMarketplaceAdmin() as admin:
    print(admin.agent.status())
```

## Agent Lifecycle (`admin.agent`)

Deploy, update, and manage your agent's marketplace listing.

```python
# Deploy a new agent definition
result = admin.agent.deploy(open("agent.yaml").read())
# {"agentId": 42, "status": "pending_review"}

# Update an existing definition
admin.agent.update(open("agent_v2.yaml").read())

# Check current status
status = admin.agent.status()
# {"status": "active", "name": "My Agent", "createdAt": "..."}

# Get current YAML definition
yaml_str = admin.agent.definition()

# Enable / disable
admin.agent.enable()
admin.agent.disable()
```

### Status Values

| Status | Meaning |
|--------|---------|
| `pending_review` | Submitted, awaiting Zinq team review |
| `approved` | Reviewed and approved, ready to enable |
| `active` | Live in the marketplace, users can enable it |
| `disabled` | Removed from marketplace, existing users keep access |

## Users (`admin.users`)

View pseudonymous information about users who have enabled your agent. For privacy, you see name initials and avatars only -- never full profiles.

```python
# Total count
count = admin.users.count()
print(f"{count} users have enabled this agent")

# List users (paginated)
users = admin.users.list(limit=50, offset=0)
for u in users:
    print(u["sessionId"], u["nameInitial"], u["enabledAt"])

# Get a specific user's public profile
profile = admin.users.profile("sess_abc123")
# {"nameInitial": "J", "avatarUrl": "...", "enabledAt": "...", "lastActiveAt": "..."}
```

## Conversations (`admin.conversations`)

View and manage conversations between your agent and its users. Useful for human-in-the-loop workflows where the AI hands off to a human operator.

```python
# List all conversations
all_convos = admin.conversations.list(limit=20)

# Filter by status
awaiting = admin.conversations.list(status="awaiting_human")
active = admin.conversations.list(status="active")
completed = admin.conversations.list(status="completed")

# Get full conversation history
convo = admin.conversations.get("sess_abc123")
for msg in convo["messages"]:
    print(f"[{msg['role']}] {msg['text']}")

# Send a human reply
admin.conversations.reply("sess_abc123", "Thanks for your patience! Here's what I found...")

# Hand back to AI
admin.conversations.resume_ai("sess_abc123")
```

### Conversation Status Values

| Status | Meaning |
|--------|---------|
| `active` | AI is handling the conversation |
| `awaiting_human` | AI escalated, waiting for human reply |
| `completed` | Conversation ended |

## Reviews (`admin.reviews`)

View user reviews and aggregate rating statistics.

```python
# List reviews
reviews = admin.reviews.list(limit=20, sort="recent")
for r in reviews:
    print(f"{r['rating']}/5: {r['text']}")

# Sort options: "recent" (default), "highest", "lowest"
best = admin.reviews.list(sort="highest", limit=5)

# Aggregate statistics
stats = admin.reviews.stats()
# {
#     "avg_rating": 4.3,
#     "total_count": 50,
#     "distribution": {1: 2, 2: 1, 3: 5, 4: 12, 5: 30}
# }
print(f"Average: {stats['avg_rating']:.1f}/5 ({stats['total_count']} reviews)")
```

## Data Collections (`admin.data`)

Manage structured data that powers your agent (product catalogs, FAQ entries, appointment slots, etc.). Collections are created automatically when you add the first record.

```python
# List all collections
collections = admin.data.collections()
for c in collections:
    print(f"{c['name']}: {c['recordCount']} records")

# Add a record
admin.data.add("products", {
    "name": "Premium Widget",
    "price": 29.99,
    "category": "gadgets",
})

# List records
products = admin.data.list("products", limit=50)
for p in products:
    print(p["name"], p["price"])

# Update a record
admin.data.update("products", "rec_abc123", {
    "name": "Premium Widget v2",
    "price": 34.99,
})

# Delete a single record
admin.data.delete("products", "rec_abc123")

# Clear all records in a collection
admin.data.clear("products")
```

## Broadcasting (`admin.broadcast`)

Send a vibe to all users who have enabled your agent.

```python
# Simple broadcast
admin.broadcast("We just launched a new feature!")

# With options (e.g. scheduling)
admin.broadcast(
    "Weekend sale starts now!",
    options={"schedule": "2026-04-20T10:00:00Z"},
)
```

## Testing (`admin.test`)

Simulate user conversations to test your agent before going live.

```python
# Send a test message and get the agent's response
response = admin.test.chat("What services do you offer?")
print(response["reply"])

# Multi-turn conversation
admin.test.chat("Tell me about pricing")
admin.test.chat("Do you have a free tier?")

# Reset test state (clear conversation history)
admin.test.reset()
```

## Error Handling

All methods raise typed exceptions from `zinq_agent.exceptions`:

```python
from zinq_agent import ZinqMarketplaceAdmin, AuthenticationError, ZinqError

try:
    admin = ZinqMarketplaceAdmin(api_key="bad_key")
    admin.agent.status()
except AuthenticationError:
    print("Invalid business API key")
except ZinqError as e:
    print(f"API error ({e.status_code}): {e.message}")
```

## Environment Variable

Set `ZINQ_BIZ_KEY` so you don't have to pass the key in code:

```bash
export ZINQ_BIZ_KEY=zbk_your_key_here
```

```python
admin = ZinqMarketplaceAdmin()  # reads from env
```
