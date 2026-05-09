# Marketplace Agent Creation Flow

## Overview

There are two paths to create a marketplace agent:

1. **In-app (Flutter)** — User describes their business in the Zinq app, AI generates the agent, user gets an API key
2. **SDK (Python)** — Developer uses `ZinqMarketplaceAdmin` to generate, refine, and deploy programmatically

Both paths use the same backend endpoints.

## In-App Flow (Flutter)

Screen: `create_marketplace_agent_screen.dart`

### Step 0: Choose Type
- User picks **Personal** or **Business** agent
- Personal → redirected to SDK docs (personal agents run on user's machine)
- Business → proceeds to Step 1

### Step 1: Describe Business
- **Business name** (required) — e.g. "Joe's Barber Shop"
- **Description** (required, free-form text) — e.g. "A barber shop in Brooklyn. We do haircuts, beard trims, and hot towel shaves. Open Tuesday through Saturday 9am to 7pm."
- **Avatar** (optional) — upload a photo
- User taps **"Generate My Agent"**

### Step 2: AI Generation (backend)
1. `POST /marketplace/agents/generate` (no auth required — preview mode)
   - Input: `{ description, businessName }`
   - Backend calls Gemini to generate a YAML agent definition
   - Gemini receives a structured prompt with the business description and outputs:
     - Agent personality and tone
     - Available tools (book_appointment, take_order, answer_faq, etc.)
     - Business hours, services, pricing
     - Safety guardrails and boundaries
   - Backend validates the generated YAML with the marketplace parser
   - Returns: `{ yamlDefinition, summary, validationErrors, isValid }`

2. If valid, `POST /marketplace/agents/create` (requires auth)
   - Input: `{ yamlDefinition, avatarUrl }`
   - Backend creates:
     - System user (is_agent=true, agent_type from YAML)
     - Agent config (bio, category, tools, system prompt)
     - Connection between owner and agent
     - One-time API key (zak_xxx) for the SDK
   - Returns: `{ agentId, apiKey, agentType, displayName }`

### Step 3: Success
- Shows the generated agent preview (name, bio, avatar)
- Displays the **one-time API key** (only shown once)
- Shows SDK code snippet for webhook setup
- Links to documentation

## SDK Flow (Python)

### Generate
```python
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin(api_key="zbk_xxx")

# AI generates YAML from description
result = admin.agent.generate(
    "A barber shop in Brooklyn. Haircuts, beard trims, hot towel shaves. "
    "Open Tue-Sat 9am-7pm.",
    name="Joe's Barber Shop"
)
print(result["yamlDefinition"])  # Full YAML
print(result["summary"])         # Human-readable summary
```

### Review (optional)
```python
review = admin.agent.review(yaml=result["yamlDefinition"])
print(f"Score: {review['score']}/10")
print(f"Issues: {review['issues']}")
print(f"Suggestions: {review['suggestions']}")
```

### Refine (optional)
```python
refined = admin.agent.refine(
    yaml=result["yamlDefinition"],
    feedback="Add a loyalty program tool and change the tone to be more casual"
)
print(refined["yaml"])     # Updated YAML
print(refined["changes"])  # List of what changed
```

### Deploy
```python
# Deploy the YAML definition
admin.agent.deploy(open("agent.yaml").read())
```

### Webhook (for custom integrations)
```python
from zinq_agent.webhook import ZinqBusinessWebhook

webhook = ZinqBusinessWebhook(secret="zws_xxx", admin=admin)

@webhook.action("book_appointment")
def book(params, session_id):
    # Your booking logic
    return {"confirmed": True, "time": params["time"]}

webhook.start(port=8080)
```

## Backend Endpoints

All under `/marketplace/agents`:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/generate` | No | AI generates YAML from business description |
| POST | `/validate` | No | Validates YAML against marketplace parser |
| POST | `/review` | No | AI quality review (score 1-10, issues, suggestions) |
| POST | `/refine` | No | AI improves YAML based on user feedback |
| POST | `/create` | Yes | Creates agent system user, returns API key |

## Two Tiers of Marketplace Agents

### Tier 1: No-Code (AI-only)
- User describes business → AI generates agent → done
- AI handles all conversations using the YAML definition
- No webhook, no server, no code
- Best for: simple businesses (FAQs, hours, services)

### Tier 2: Custom Integrations (Webhook)
- Same generation flow, but developer adds a webhook server
- Webhook handles tool calls (book_appointment, check_inventory, etc.)
- Python SDK provides `ZinqBusinessWebhook` for easy setup
- Best for: businesses with real-time data (availability, orders, payments)

## YAML Agent Definition Format

The generated YAML defines the agent's behavior:

```yaml
name: Joe's Barber Shop
type: barber_shop
bio: Your neighborhood barber. Book cuts, check availability, see our services.
category: services
personality:
  tone: friendly, professional
  greeting: "Hey! Welcome to Joe's. What can I do for you?"
services:
  - name: Haircut
    price: 25
    duration: 30
  - name: Beard Trim
    price: 15
    duration: 15
hours:
  monday: closed
  tuesday: 9:00-19:00
  # ...
tools:
  - book_appointment
  - check_availability
  - list_services
  - cancel_appointment
guardrails:
  - Never discuss competitors
  - Don't give medical advice
  - Redirect complaints to owner
```
