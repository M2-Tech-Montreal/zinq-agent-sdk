# Testing Marketplace Agents

## The Problem

You have a bakery agent serving 50 real customers. You want to change the prompt, add a new tool, fix a bug. How do you test without breaking the live agent?

## The Solution: Agent Versions + Visibility Controls

### Two Agent IDs, One Business

Every marketplace agent gets TWO IDs — a prod ID and a dev ID. Same business, same developer, but completely isolated:

```
Agent ID 42 — "Rosa's Bakery" (prod)
├── Visibility: public
├── Users: 230 installs
├── Reviews: 47 reviews, 4.3 avg
├── YAML: v3 (stable, tested)
└── Conversations: 1,200 total

Agent ID 43 — "Rosa's Bakery Dev" (dev)
├── Visibility: private (or testers: [1129, 1130])
├── Users: 3 testers
├── Reviews: 0
├── YAML: v7 (experimental, might be broken)
└── Conversations: 50 test conversations
```

**The dev agent is disposable.** Break it, reset it, try crazy things. The prod agent's reviews, users, and history are completely untouched.

```python
from zinq_agent import ZinqMarketplaceAdmin

# Prod admin — handles the live agent
admin_prod = ZinqMarketplaceAdmin(api_key="zbk_prod_xxxxx")

# Dev admin — handles the test agent
admin_dev = ZinqMarketplaceAdmin(api_key="zbk_dev_xxxxx")

# Work on dev freely
admin_dev.agent.update(experimental_yaml)
admin_dev.test.chat("Does this new feature work?")  # safe to break

# When ready, promote to prod
dev_yaml = admin_dev.agent.definition()
admin_prod.agent.update(dev_yaml)  # prod gets the tested YAML
# Reviews (47), users (230), history — all preserved on agent ID 42
```

### Why Two IDs Instead of One?

| | One ID (visibility toggle) | Two IDs (dev + prod) |
|---|---|---|
| **Safety** | Risky — testing on live agent | Safe — dev is isolated |
| **Reviews** | Preserved | Preserved (on prod ID) |
| **Rollback** | Must roll back on live | Just don't promote |
| **Testers** | See the same agent as real users | See a separate agent |
| **Data** | Shared (specials, menu) | Separate (test data won't affect prod) |

**Recommended: Two IDs.** Use one ID with visibility toggle only for quick hotfixes (set prod to private → fix → flip back to public, like a maintenance window).

### Setting Up Dev + Prod

```python
# Step 1: Create both agents
prod = admin.agent.create(name="Rosa's Bakery", visibility="public")
dev = admin.agent.create(name="Rosa's Bakery Dev", visibility="private")

# Step 2: Store both API keys
# ZINQ_BIZ_KEY_PROD=zbk_prod_xxxxx
# ZINQ_BIZ_KEY_DEV=zbk_dev_xxxxx

# Step 3: Use dev for all development
admin_dev = ZinqMarketplaceAdmin(api_key=os.environ["ZINQ_BIZ_KEY_DEV"])
admin_dev.agent.update(yaml)
admin_dev.test.chat("test test test")

# Step 4: Promote to prod when ready
admin_prod = ZinqMarketplaceAdmin(api_key=os.environ["ZINQ_BIZ_KEY_PROD"])
admin_prod.agent.update(admin_dev.agent.definition())
```

### Visibility Modes

| Mode | Who Can See It | Use Case |
|------|---------------|----------|
| `public` | Everyone in marketplace | Production agent |
| `private` | Only the owner | Solo development |
| `testers` | Owner + specific user IDs | Team testing before release |

```python
# Private — only you can see it
admin.agent.set_visibility(agent_id=43, mode="private")

# Add testers — they can enable and interact with the agent
admin.agent.set_visibility(agent_id=43, mode="testers", user_ids=[1129, 1130, 1151])

# Go public — everyone can see it
admin.agent.set_visibility(agent_id=43, mode="public")
```

### The Development Workflow

```
1. Create dev agent (private)
2. Upload YAML, test with admin.test.chat()
3. Add testers → they interact with dev agent on their real Zinq app
4. Fix bugs based on tester feedback
5. When ready: copy YAML to prod agent
6. If broken: roll back prod agent to previous YAML version
```

## Test Users (Mock Users)

For automated testing, you need fake users that can send vibes to your agent and receive responses.

### Creating Test Users

```python
# Create up to 10 test users per developer (hard limit)
test_user_1 = admin.test.create_user(name="Test Customer Alice")
test_user_2 = admin.test.create_user(name="Test Customer Bob")
test_user_3 = admin.test.create_user(name="Test Customer Carol")

print(f"Test user ID: {test_user_1['userId']}")
print(f"Test user session: {test_user_1['sessionId']}")

# List your test users
users = admin.test.list_users()
print(f"You have {len(users)} test users (max 10)")
```

### What Test Users Can Do

```python
# Test user sends a vibe to the agent
admin.test.send_vibe(
    user_id=test_user_1['userId'],
    text="What are your specials today?"
)

# Check what the agent replied
replies = admin.test.get_replies(user_id=test_user_1['userId'], limit=5)
for r in replies:
    print(f"Agent: {r['text']}")

# Test user sends a charm
admin.test.send_charm(
    user_id=test_user_1['userId'],
    charm_type="thumbs_up"
)

# Check if agent responded to charm
replies = admin.test.get_replies(user_id=test_user_1['userId'], limit=1)
```

### What Test Users CANNOT Do

- Appear in any real user's feed, presence bar, or contacts
- Send vibes to real users
- Show up in marketplace install counts or stats
- Persist beyond 30 days (auto-deleted)

### Limits

| Resource | Limit | Why |
|----------|-------|-----|
| Test users per developer | 10 | Prevent system abuse |
| Test agents per developer | 5 | Keep DB clean |
| Test conversations per agent | 100 | Prevent unbounded storage |
| Test user lifetime | 30 days | Auto-cleanup |

## Automated Testing with pytest

### Basic Test: Agent Responds Correctly

```python
import pytest
from zinq_agent import ZinqMarketplaceAdmin

@pytest.fixture
def admin():
    return ZinqMarketplaceAdmin()

@pytest.fixture
def dev_agent(admin):
    """Create a dev agent for testing, clean up after."""
    result = admin.agent.create(name="Test Bakery", visibility="private")
    agent_id = result['agentId']

    # Upload YAML
    with open("agent.yaml") as f:
        admin.agent.update(f.read())

    # Add test data
    admin.data.add("daily_specials", {"name": "Sourdough", "price": 6.50})
    admin.data.add("menu_items", {"name": "Croissant", "price": 3.50})

    yield agent_id

    # Cleanup
    admin.data.clear("daily_specials")
    admin.data.clear("menu_items")

@pytest.fixture
def test_customer(admin):
    """Create a test user, clean up after."""
    user = admin.test.create_user(name="Test Customer")
    yield user
    admin.test.delete_user(user['userId'])


class TestBakeryAgent:

    def test_specials_response(self, admin, dev_agent, test_customer):
        """Customer asks for specials → agent returns them."""
        admin.test.send_vibe(
            user_id=test_customer['userId'],
            text="What are your specials?"
        )
        replies = admin.test.get_replies(
            user_id=test_customer['userId'],
            limit=1,
            timeout=10  # wait up to 10s for agent to respond
        )
        assert len(replies) > 0
        assert "Sourdough" in replies[0]['text']

    def test_order_escalation(self, admin, dev_agent, test_customer):
        """Customer orders → agent escalates to human."""
        admin.test.send_vibe(
            user_id=test_customer['userId'],
            text="I want to order a sourdough for pickup at noon"
        )

        # Wait for escalation
        import time
        time.sleep(5)

        convos = admin.conversations.list(status="awaiting_human")
        assert any("sourdough" in c.get('summary', '').lower() for c in convos)

    def test_unknown_question(self, admin, dev_agent, test_customer):
        """Customer asks something unexpected → agent handles gracefully."""
        admin.test.send_vibe(
            user_id=test_customer['userId'],
            text="Do you have vegan options?"
        )
        replies = admin.test.get_replies(
            user_id=test_customer['userId'],
            limit=1,
            timeout=10
        )
        assert len(replies) > 0
        # Should NOT crash or return empty
        assert len(replies[0]['text']) > 10

    def test_charm_response(self, admin, dev_agent, test_customer):
        """Customer sends thumbs up → agent acknowledges."""
        # First, have a conversation
        admin.test.send_vibe(
            user_id=test_customer['userId'],
            text="Thanks for the great service!"
        )
        import time
        time.sleep(3)

        # Send charm
        admin.test.send_charm(
            user_id=test_customer['userId'],
            charm_type="heart"
        )
        time.sleep(3)

        # Agent should respond positively
        replies = admin.test.get_replies(
            user_id=test_customer['userId'],
            limit=1
        )
        assert len(replies) > 0
```

### Running Tests

```bash
# Against dev agent
export ZINQ_BIZ_KEY=zbk_your_dev_key
pytest tests/test_bakery.py -v

# Against staging
export ZINQ_DEV_URL=https://zinq-app.com/dev-api
pytest tests/test_bakery.py -v
```

## Version Management

### YAML Versioning

Every time you update the YAML, the version increments automatically:

```python
# Check current version
status = admin.agent.status()
print(f"Version: {status['definitionVersion']}")  # 1

# Update YAML
admin.agent.update(new_yaml)
status = admin.agent.status()
print(f"Version: {status['definitionVersion']}")  # 2

# Update again
admin.agent.update(newer_yaml)
status = admin.agent.status()
print(f"Version: {status['definitionVersion']}")  # 3
```

### Rolling Back

```python
# Get version history
versions = admin.agent.versions()
for v in versions:
    print(f"v{v['version']} — {v['updatedAt']} — {v['summary']}")

# Roll back to a previous version
admin.agent.rollback(version=2)

# Or roll back to the version before the last update
admin.agent.rollback(version=status['definitionVersion'] - 1)
```

### Promoting Dev → Prod

```python
# Get the dev agent's current YAML
dev_yaml = admin.agent.definition()  # from dev agent

# Switch to prod admin
admin_prod = ZinqMarketplaceAdmin(api_key="zbk_prod_key")

# Update prod with dev's YAML
admin_prod.agent.update(dev_yaml)

# If something goes wrong
admin_prod.agent.rollback(version=previous_version)
```

## Complete Testing Workflow

```
Day 1: Build
├── Create dev agent (private)
├── Generate YAML from description
├── Validate → fix errors
├── Review → fix quality issues
├── admin.test.chat() → quick sanity check
└── Commit YAML to git

Day 2: Automated Tests
├── Create test users (3-5)
├── Run pytest suite against dev agent
├── Fix failures → update YAML → re-run
└── All tests pass

Day 3: Human Testing
├── Set visibility to testers + add team
├── Testers interact on their Zinq apps
├── Collect feedback
├── Refine YAML based on feedback
└── Re-run automated tests

Day 4: Launch
├── Final review + validate
├── Copy YAML to prod agent
├── Set prod visibility to public
├── Monitor: admin.users.count(), admin.reviews.stats()
└── If issues: rollback prod, fix in dev, repeat

Ongoing:
├── Monitor conversations for escalations
├── Update data (specials, menu) via admin.data.*
├── Periodic YAML refinements
└── Version management with rollback safety net
```
