# Marketplace Tier 1: No-Code Agent

Build and publish a marketplace agent for your business without writing a webhook server. Describe your business, let AI generate the agent, edit the YAML, test it, and go live.

**Time to published agent: 30 minutes.**

---

## Overview

A Tier 1 marketplace agent runs entirely on the Zinq platform. You define your business in YAML, and Gemini handles all customer conversations based on your definition. No webhook server, no hosting, no infrastructure.

```
Customer on Zinq
      |
      v
Zinq Platform (Gemini AI)
      |
      |-- reads your YAML definition
      |-- answers questions, takes orders
      |-- escalates to you when needed
      |
You manage everything via Python SDK
```

There is no web dashboard. You manage your agent entirely through the `ZinqMarketplaceAdmin` Python SDK.

---

## Step 1: Install the SDK

```bash
pip install zinq-agent
```

## Step 2: Get Your Business API Key

Sign up at [zinq-app.com/business](https://zinq-app.com/business). You will receive a business API key (`zbk_...`).

Set it as an environment variable:

```bash
export ZINQ_BIZ_KEY=zbk_your_key_here
```

## Step 3: Generate Your Agent from a Description

Open a Python shell or write a script:

```python
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin()  # reads ZINQ_BIZ_KEY from env

# Describe your business in plain English
result = admin.agent.generate(
    "I run a bakery called Rosa's in downtown Portland. "
    "We make sourdough, croissants, focaccia, and custom cakes. "
    "Customers can place pickup orders and ask about daily specials. "
    "We're open Tuesday through Sunday, 6am to 3pm."
)

# Review the generated YAML
print(result["yaml"])

# See what the AI understood
print(result["summary"])
# {"capabilities": ["pickup_orders", "daily_specials", "custom_cakes"],
#  "collections": ["menu_items", "daily_specials"]}
```

You can also provide the business name explicitly:

```python
result = admin.agent.generate(
    "Neighborhood barber shop with walk-ins and appointments",
    name="Joe's Barber Shop",
)
```

## Step 4: Review and Edit the YAML

Save the generated YAML, review it, and edit anything that is not right:

```python
yaml_text = result["yaml"]

# Save to file for editing
with open("agent.yaml", "w") as f:
    f.write(yaml_text)
```

Open `agent.yaml` in your editor. Here is what a typical definition looks like:

```yaml
name: "Rosa's Bakery"
tagline: "Fresh bread and pastries, baked daily in Portland"
description: |
  Rosa's Bakery is a neighborhood bakery in downtown Portland.
  We bake sourdough, croissants, focaccia, and custom cakes.
  Open Tuesday through Sunday, 6am to 3pm.

category: "food_and_drink"

personality: |
  You are Rosa, a warm and enthusiastic baker who loves talking
  about bread. Keep responses friendly and concise. Use "we" not "I"
  when talking about the bakery.

greeting: |
  Welcome to Rosa's Bakery! What can I get for you today?

services:
  - name: "Sourdough Loaf"
    price: 8.00
  - name: "Croissant"
    price: 4.50
  - name: "Focaccia"
    price: 7.50

hours:
  tuesday_to_friday: "6:00 AM - 3:00 PM"
  saturday_sunday: "7:00 AM - 2:00 PM"
  monday: "Closed"
```

Edit the personality, fix prices, add services, adjust hours -- make it yours.

## Step 5: Deploy the Edited YAML

```python
# Deploy (first time)
admin.agent.deploy(open("agent.yaml").read())

# Or update (if already deployed)
admin.agent.update(open("agent.yaml").read())
```

## Step 6: Test Your Agent

Test conversations without a real user:

```python
# Send a test message
response = admin.test.chat("What do you sell?")
print(response["reply"])

# Multi-turn conversation
response = admin.test.chat("How much is a sourdough loaf?")
print(response["reply"])

response = admin.test.chat("Can I order 3 for pickup tomorrow at 10am?")
print(response["reply"])

# Reset test state (clear conversation history)
admin.test.reset()
```

### Debugging bad responses

If the agent says something wrong, the fix is in the YAML:

```python
# 1. Check what the agent thinks it knows
print(admin.agent.definition())

# 2. Edit agent.yaml to fix the issue

# 3. Update
admin.agent.update(open("agent.yaml").read())

# 4. Reset and test again
admin.test.reset()
response = admin.test.chat("Same question that got a bad answer")
print(response["reply"])
```

Common fixes:
- **Wrong tone?** Edit the `personality` section.
- **Wrong prices/hours?** Edit the `services` or `hours` section.
- **Answering questions it should not?** Add an `escalation_rules` section.
- **Too verbose?** Add "Keep responses under 100 words" to the personality.

## Step 7: Upload an Avatar

```python
admin.agent.upload_avatar("rosa_avatar.png")
```

The image should be PNG or JPG, max 5MB. It appears as the agent's profile picture in the Zinq app.

## Step 8: Add Data Collections

Data collections let you manage structured data that powers your agent -- product catalogs, menus, FAQs, specials.

```python
# Add menu items
admin.data.add("menu_items", {
    "name": "Sourdough Loaf",
    "price": 8.00,
    "category": "bread",
    "description": "Our signature sourdough, 24-hour ferment",
})

admin.data.add("menu_items", {
    "name": "Croissant",
    "price": 4.50,
    "category": "pastry",
    "description": "Buttery, flaky, classic French style",
})

# Add daily specials
admin.data.add("daily_specials", {
    "name": "Lavender Honey Croissant",
    "price": 6.00,
    "note": "Limited batch -- only 20 made today!",
})

# List what you have
for item in admin.data.list("menu_items"):
    print(f"  {item['name']}: ${item['price']}")

# See all collections
for coll in admin.data.collections():
    print(f"  {coll['name']}: {coll['recordCount']} records")

# Update a record
admin.data.update("menu_items", "rec_abc123", {
    "name": "Sourdough Loaf",
    "price": 9.00,  # price increase
})

# Delete a record
admin.data.delete("menu_items", "rec_abc123")

# Clear all records in a collection
admin.data.clear("daily_specials")
```

## Step 9: Publish

When you are happy with the agent, submit it for review:

```python
result = admin.agent.publish()
print(result)
# {"status": "pending_review", "estimated_review_time": "24-48 hours"}
```

The Zinq team reviews agents before they go live in the marketplace. Once approved, customers can find and enable your agent.

## Step 10: Monitor Your Agent

After publishing, use the SDK to monitor performance:

```python
# How many customers?
print(f"{admin.users.count()} users")

# List users (pseudonymous -- you see initials, not full names)
for u in admin.users.list():
    print(f"  {u['nameInitial']} -- enabled {u['enabledAt']}")

# Reviews
stats = admin.reviews.stats()
print(f"Rating: {stats['avg_rating']:.1f}/5 ({stats['total_count']} reviews)")

for review in admin.reviews.list(sort="recent", limit=5):
    print(f"  {review['rating']}/5: {review['text']}")

# Earnings
earnings = admin.billing.earnings()
print(f"Total earned: ${earnings['total_earned_usd']}")
print(f"This month: ${earnings['this_month_usd']}")

# Usage
usage = admin.billing.usage()
print(f"Active users: {usage['active_users']}")
print(f"Conversations: {usage['total_conversations']}")
```

---

## The Full Iteration Loop

This is the workflow you will use repeatedly:

```
1. Edit agent.yaml
2. admin.agent.update(open("agent.yaml").read())
3. admin.test.reset()
4. admin.test.chat("test question")
5. If bad -> go to 1
6. If good -> admin.agent.publish()
```

Or as a script:

```python
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin()

# Update definition
admin.agent.update(open("agent.yaml").read())

# Reset test state
admin.test.reset()

# Run test scenarios
tests = [
    "What do you sell?",
    "How much is sourdough?",
    "Can I order 2 loaves for pickup at 10am?",
    "Are you open on Monday?",
    "I need a wedding cake",  # should escalate
]

for question in tests:
    response = admin.test.chat(question)
    print(f"Q: {question}")
    print(f"A: {response['reply']}")
    print()

admin.test.reset()
```

---

## Sending Broadcasts

Send a message to all users who have enabled your agent:

```python
# Simple broadcast
admin.broadcast("We just launched a new flavor -- try our Matcha Muffin!")

# Scheduled broadcast
admin.broadcast(
    "Weekend sale starts now!",
    options={"schedule": "2026-04-20T10:00:00Z"},
)
```

A common pattern is a daily morning update script:

```python
# morning_update.py -- run with cron at 6am
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin()

# Clear yesterday's specials
admin.data.clear("daily_specials")

# Add today's specials
specials = [
    {"name": "Lavender Honey Croissant", "price": 6.00},
    {"name": "Rosemary Focaccia", "price": 7.50},
]
for s in specials:
    admin.data.add("daily_specials", s)

# Broadcast to customers
lines = ["Fresh out of the oven today:"]
for s in specials:
    lines.append(f"  {s['name']} -- ${s['price']:.2f}")
lines.append("\nOrder ahead for pickup -- just message me!")

admin.broadcast("\n".join(lines))
admin.close()
```

---

## Handling Escalated Conversations

When the AI cannot handle a conversation (complex requests, complaints, custom orders), it escalates. You handle these through the SDK:

```python
# Check for conversations awaiting your reply
convos = admin.conversations.list(status="awaiting_human")
for c in convos:
    print(f"Session: {c['sessionId']}")
    print(f"Status: {c['status']}")

# Read the full conversation
convo = admin.conversations.get(c["sessionId"])
for msg in convo["messages"]:
    print(f"  [{msg['role']}] {msg['text']}")

# Reply
admin.conversations.reply(c["sessionId"], "Thanks for reaching out! Your cake order is confirmed.")

# Hand back to AI
admin.conversations.resume_ai(c["sessionId"])
```

You can automate this with a polling script or build it into your daily workflow.

---

## Common Pitfalls

### 1. Personality too vague

Be specific in the personality section. "Be helpful" is too generic. Instead:

```yaml
personality: |
  You are Rosa, owner of Rosa's Bakery. You are warm, enthusiastic,
  and love talking about bread. Keep responses under 100 words.
  Always mention pickup availability. Never discuss competitors.
  If asked about wedding cakes, escalate to human.
```

### 2. Missing escalation rules

Without escalation rules, the AI tries to handle everything -- including things it should not:

```yaml
escalation_rules:
  - trigger: "wedding cake"
    reason: "Wedding cakes need personal consultation"
  - trigger: "complaint"
    reason: "Complaints need human attention"
  - trigger: "refund"
    reason: "Refund requests need owner approval"
```

### 3. Not testing enough edge cases

Test questions the AI might get wrong:

```python
# Test edge cases
admin.test.chat("Are you open on Christmas?")
admin.test.chat("Can I return bread?")
admin.test.chat("Tell me about your competitors")
admin.test.chat("What's your address?")
```

### 4. Forgetting to update data collections

If your prices change, update both the YAML and the data collections:

```python
# Update YAML
admin.agent.update(open("agent.yaml").read())

# Update data collection
admin.data.update("menu_items", record_id, {"price": 9.00})
```

---

## Next Steps

- Ready for webhook integrations? See [Marketplace Tier 2](dev-guide-marketplace-tier2.md).
- [Business Agents reference](business-agents.md) -- full `ZinqMarketplaceAdmin` documentation.
- [Examples](../examples/) -- complete working marketplace agents (Joe's Barber, Rosa's Bakery, Dr. Sarah Nutrition).

---

## How Agent Generation Works

When you call `admin.agent.generate()`, here's what happens under the hood:

```
You (SDK)                    Zinq Backend                    Gemini AI
   |                              |                              |
   |-- generate("I run a         |                              |
   |   bakery with daily          |                              |
   |   specials...")           -->|                              |
   |                              |-- meta-prompt + your      -->|
   |                              |   description                |
   |                              |                              |
   |                              |<-- complete YAML definition--|
   |                              |   (prompt, tools, collections|
   |                              |    first contact message)    |
   |                              |                              |
   |<-- {yaml, summary} ---------|                              |
   |                                                             |
   |   You review the YAML...                                    |
   |   Edit if needed...                                         |
   |                                                             |
   |-- update(edited_yaml) ----->|  (saves new version)         |
   |                              |                              |
   |-- test.chat("What are    -->|-- runs YAML agent loop    -->|
   |   your specials?")           |                              |
   |                              |<-- "Today we have..."    ---|
   |<-- {reply: "Today we...} ---|                              |
   |                                                             |
   |   Iterate until happy...                                    |
   |                                                             |
   |-- publish() --------------->|  (submits for review)        |
```

### The Development Loop

This is the real workflow — it's NOT one-shot:

```python
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin()

# Step 1: Generate initial YAML from your description
result = admin.agent.generate(
    "I run Rosa's Bakery. We sell fresh bread, pastries, and custom cakes. "
    "We have daily specials that change every morning. "
    "Customers can order for pickup. Custom cakes need my personal attention."
)

# Step 2: Review what Gemini created
print(result['summary']['name'])         # "Rosa's Bakery"
print(result['summary']['capabilities']) # ["Show specials", "Browse menu", ...]
print(result['summary']['collections'])  # ["daily_specials", "menu_items"]

# Step 3: Look at the raw YAML
yaml_str = result['yaml']
print(yaml_str)  # Full YAML definition

# Step 4: Save it locally, edit in your favorite editor
with open("agent.yaml", "w") as f:
    f.write(yaml_str)

# ... edit agent.yaml in VS Code, vim, whatever ...
# Maybe tweak the personality, add a tool, change the bio

# Step 5: Upload your edited version
with open("agent.yaml") as f:
    admin.agent.update(f.read())

# Step 6: Test it
response = admin.test.chat("What are your specials today?")
print(response['reply'])
# Hmm, it says "I don't have any specials loaded yet" — need to add data

# Step 7: Add some test data
admin.data.add("daily_specials", {"name": "Sourdough Loaf", "price": 6.50})
admin.data.add("daily_specials", {"name": "Blueberry Muffins", "price": 8.00})

# Step 8: Test again
response = admin.test.chat("What are your specials today?")
print(response['reply'])
# "Today's specials: Sourdough Loaf ($6.50), Blueberry Muffins ($8.00)!"
# 

# Step 9: Test edge cases
admin.test.chat("I want to order for pickup")
admin.test.chat("Can you make a custom wedding cake?")
admin.test.chat("What time do you close?")  # Does it handle this gracefully?

# Step 10: Upload avatar
admin.agent.upload_avatar("rosa_avatar.png")

# Step 11: When you're happy, publish
admin.agent.publish()
# {"status": "pending_review", "estimated_review_time": "24-48 hours"}

# Step 12: Monitor after launch
admin.users.count()           # How many people enabled your agent
admin.reviews.stats()         # Average rating
admin.billing.earnings()      # How much you've earned
```

### Common Iteration Patterns

**"The agent is too formal"**
```python
# Read the current YAML
yaml_str = admin.agent.definition()
# Edit the system_prompt to be more casual
# Re-upload and test
```

**"It doesn't know about my hours"**
```python
# Add to your YAML's system_prompt:
# "Our hours are Mon-Sat 7am-6pm, closed Sundays."
# Or add an FAQ collection:
admin.data.add("faq", {"question": "What are your hours?", "answer": "Mon-Sat 7am-6pm"})
```

**"The tool isn't working right"**
```python
# Test the specific tool
response = admin.test.chat("I want to order for pickup")
# Check the tool call details
print(response.get('tool_calls'))  # See what tools were invoked
```

**"I want to start over"**
```python
result = admin.agent.generate("New description with more detail...")
admin.agent.update(result['yaml'])
admin.test.reset()  # Clear test conversation
```

---

## How Tools Work (No Code Required)

The most important thing to understand: **tools are NOT code.** They're data operations declared in YAML. You never write tool logic for a Tier 1 agent.

### The Tool Execution Chain

```
1. YAML declares the tool
   ↓
2. Gemini sees it as a callable function
   ↓
3. Customer asks a question → Gemini decides to call the tool
   ↓
4. MarketplaceToolExecutor routes by tool type
   ↓
5. Executor performs the database operation
   ↓
6. Result returned to Gemini → Gemini formulates response
```

### Concrete Example: "What are your specials?"

**Step 1 — Your YAML declares:**
```yaml
tools:
  - name: get_specials
    type: query_log              # tells executor: "read from database"
    collection: daily_specials   # tells executor: "this collection"
    description: "Get today's specials"
```

**Step 2 — You upload data via SDK:**
```python
admin.data.add("daily_specials", {"name": "Sourdough Loaf", "price": 6.50})
admin.data.add("daily_specials", {"name": "Blueberry Muffins", "price": 8.00})
admin.data.add("daily_specials", {"name": "Croissants", "price": 3.50})
```

**Step 3 — Customer sends a vibe:** "Hey, what's fresh today?"

**Step 4 — Gemini thinks:** "The user wants to know about specials. I have a `get_specials` tool. Let me call it."

**Step 5 — Zinq's executor runs:**
```sql
SELECT data FROM marketplace_agent_data 
WHERE agent_type = 'rosas_bakery' 
  AND collection = 'daily_specials'
```

**Step 6 — Returns to Gemini:**
```json
[
  {"name": "Sourdough Loaf", "price": 6.50},
  {"name": "Blueberry Muffins", "price": 8.00},
  {"name": "Croissants", "price": 3.50}
]
```

**Step 7 — Gemini responds to customer:**
"Today's specials: Sourdough Loaf ($6.50), Blueberry Muffins ($8.00), and Croissants ($3.50)! Want to order anything?"

### Tool Types — What Each One Does

| Tool Type | What the Executor Does | Example Use |
|-----------|----------------------|-------------|
| `query_log` | Reads records from a collection | "What's on the menu?", "Show me your services" |
| `structured_log` | Saves a record to a collection | "Log this order", "Save appointment" |
| `aggregate_log` | Counts/sums records | "How many orders today?", "Total revenue" |
| `diary_search` | Searches user's Zinq diary | "What workouts did I do last week?" |
| `save_memory` | Saves a user preference | "Remember I'm allergic to nuts" |
| `get_memories` | Reads saved preferences | "What are my dietary restrictions?" |
| `ask_user` | Shows interactive buttons | "Pick a size: [Small] [Medium] [Large]" |
| `schedule_follow_up` | Schedules a check-in vibe | "I'll check back tomorrow at 9am" |
| `request_human_review` | Pauses AI, notifies business owner | "Let me check with the team..." |

### You Control the Data, Gemini Controls the Conversation

Think of it like a restaurant:
- **You** stock the kitchen (upload data via SDK)
- **Gemini** is the waiter (talks to customers, takes orders)
- **The executor** is the kitchen (fetches what the waiter asks for)

You never write waiter logic. You just keep the kitchen stocked:

```python
# Every morning Rosa updates specials
admin.data.clear("daily_specials")
admin.data.add("daily_specials", {"name": "Sourdough Loaf", "price": 6.50})
admin.data.add("daily_specials", {"name": "Croissants", "price": 3.50})

# The agent automatically knows about the new specials
# No code changes, no YAML changes, no redeployment
```

### What About Custom Logic? (Tier 2)

If you need tools that do more than read/write data — like checking a real calendar, processing a payment, or calling an external API — that's [Tier 2 (Connected Agents)](dev-guide-marketplace-tier2.md). Your server handles the custom logic via webhooks, while Zinq still runs the AI conversation.
