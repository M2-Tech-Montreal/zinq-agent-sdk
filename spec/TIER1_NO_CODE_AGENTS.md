# Tier 1: No-Code Marketplace Agents

## What Is a Tier 1 Agent?

A business agent that runs entirely on a YAML definition + Gemini. No Python, no webhook, no server. The business owner describes their business in plain English, AI generates a YAML definition, and the agent goes live. When the AI can't handle something, it hands off to the human owner.

## Who Is This For?

Small businesses and solo operators who want an AI agent but will never write code:
- Nail salons, barber shops, spas
- Bakeries, cafes, food trucks
- Personal trainers, yoga instructors
- Tutors, music teachers
- Plumbers, electricians, cleaners
- Photographers, freelance designers
- Pet groomers, dog walkers

## How It Works

### Creation Flow

1. Owner opens Zinq app → Marketplace → Create Agent
2. Types business name + description in plain English
3. Taps "Generate My Agent"
4. Backend calls Gemini → generates YAML definition
5. Owner previews the agent (name, bio, personality, services)
6. Owner taps "Go Live"
7. Agent appears in the marketplace
8. Customers find it, enable it, start chatting

### Conversation Flow

```
Customer sends vibe → Gemini reads YAML context → responds

If AI can handle it (hours, prices, services, FAQ):
  → AI responds directly

If AI cannot handle it (booking, complaint, custom request):
  → AI calls request_human_review tool
  → Conversation status → "awaiting_human"
  → Owner gets a vibe: "New message from [Customer] about [topic]"
  → Owner replies in app
  → Customer sees reply as a vibe from the agent
  → Conversation status → "active" (AI resumes)
```

### What the AI Can Do (from YAML alone)

- Answer questions about services, pricing, hours, location
- Describe menu items, packages, offerings
- Explain policies (cancellation, refund, etc.)
- Greet customers with the right tone/personality
- Speak multiple languages (if specified in YAML)
- Redirect off-topic questions politely

### What Requires Human Handoff

- **Booking confirmations** — AI says "I'll check with [Owner]", hands off
- **Custom quotes** — anything not in the fixed price list
- **Complaints** — always escalate
- **Payments** — Tier 1 agents never handle money
- **Anything the AI is unsure about** — better to ask than guess

## YAML Definition Format

```yaml
agent:
  name: "Maria's Nails"
  bio: "Your neighborhood nail salon in Brooklyn. Book appointments, check availability, see our services."
  category: beauty
  language: [en, es]

personality:
  tone: warm, professional
  greeting: "Hey! Welcome to Maria's Nails. Looking to book an appointment or just browsing?"
  style: casual but respectful

services:
  - name: Gel Manicure
    price: 35
    duration_minutes: 45
  - name: Pedicure
    price: 45
    duration_minutes: 60
  - name: Gel Mani + Pedi Combo
    price: 70
    duration_minutes: 90
  - name: Nail Art (per nail)
    price: 5
    duration_minutes: 5
  - name: Dip Powder
    price: 50
    duration_minutes: 60

hours:
  monday: 10:00-19:00
  tuesday: 10:00-19:00
  wednesday: 10:00-19:00
  thursday: 10:00-19:00
  friday: 10:00-19:00
  saturday: 10:00-19:00
  sunday: closed

location:
  address: "412 5th Ave, Brooklyn, NY 11215"
  phone: "+17185551234"

policies:
  cancellation: "Please cancel at least 2 hours before your appointment."
  walk_ins: "Walk-ins welcome but appointments preferred."
  payment: "Cash, card, Venmo, Zelle."

guardrails:
  - Never discuss competitors
  - Don't give medical advice about nail conditions
  - Redirect complaints to owner immediately
  - Never confirm a booking — always hand off to owner for confirmation
  - Never quote prices not on the service list
```

## Built-In Tools (No Code Required)

These tools are available to every Tier 1 agent automatically. The agent calls them based on conversation context. The business owner doesn't configure them — they just exist.

### 1. `request_human_review`

Escalates the conversation to the business owner.

**When the AI calls it:**
- Customer wants to book an appointment
- Customer has a complaint
- Customer asks for a custom quote
- AI is unsure how to respond
- Customer explicitly asks to talk to a human

**What happens:**
1. Conversation status changes to `awaiting_human`
2. Owner receives a vibe in their chat with the agent:
   ```
   New message from Sarah about booking:
   "Can I get a gel mani + pedi combo Saturday at 2pm?"

   Reply here to respond to Sarah.
   ```
3. Owner replies in the app (plain text)
4. Customer sees the reply as a vibe from the agent
5. Conversation status returns to `active`

**If owner doesn't reply within [configurable] minutes:**
- Customer gets: "Maria will get back to you shortly. You'll get a notification when she responds."

### 2. `list_services`

Returns the service list from the YAML definition. AI uses this to answer "what do you offer?" / "how much is a manicure?" without hallucinating prices.

**Returns:** Service name, price, duration for all services in the YAML.

### 3. `get_hours`

Returns business hours from the YAML. AI uses this to answer "are you open Saturday?" / "what time do you close?"

**Returns:** Hours for each day, current open/closed status.

### 4. `get_location`

Returns address and contact info from the YAML.

**Returns:** Address, phone number, any directions notes.

### 5. `send_broadcast` (owner-initiated)

Owner sends a vibe to the agent saying "broadcast: 20% off all manicures today!" → agent sends this as a vibe to all customers who have the agent enabled.

**Trigger:** Owner sends a message starting with "broadcast:" to their own agent.

## Owner Experience

### In the Zinq App

The owner interacts with their agent just like any other contact:

- **See customer conversations** — Agent forwards escalated messages as vibes
- **Reply to customers** — Owner types a reply, customer sees it from the agent
- **Send broadcasts** — Owner sends "broadcast: [message]" to push to all customers
- **Update services** — Owner sends "update: gel manicure is now $40" (AI updates YAML)
- **Check stats** — Owner sends "stats" to see customer count, conversations today

### No Dashboard Needed

Everything happens in the Zinq app. The owner's chat thread with their own agent IS the dashboard.

## Customer Experience

1. Customer finds "Maria's Nails" in marketplace or via shared link
2. Enables the agent (appears as a contact)
3. Sends a vibe: "do you have anything open Saturday?"
4. AI responds: "Saturday is looking good! What service were you interested in?"
5. Customer: "gel mani + pedi combo at 2pm"
6. AI: "Let me check with Maria — I'll get back to you shortly with confirmation."
7. Maria gets notified, replies "confirmed!"
8. Customer gets: "You're all set! Gel mani + pedi combo, Saturday at 2pm. 412 5th Ave, Brooklyn. See you then!"

## Tier 1 vs Tier 2 Comparison

| Feature | Tier 1 (No-Code) | Tier 2 (SDK/Webhook) |
|---------|-------------------|----------------------|
| Setup | Describe business → done | Write Python webhook server |
| Conversations | Gemini + YAML | Gemini + YAML + custom tools |
| Bookings | Human handoff | Can check real calendar |
| Orders | Human handoff | Can process real orders |
| Payments | Never | Can integrate Stripe, Square |
| Inventory | From YAML (static) | Can query live database |
| Human handoff | Built-in | Built-in + custom logic |
| Server required | No | Yes |
| Cost to owner | $0 (uses customer credits) | Hosting cost for webhook |

## What Needs to Be Built

### Backend

1. **`request_human_review` tool** — Built-in tool for marketplace agents
   - Changes conversation status to `awaiting_human`
   - Sends a vibe to the owner with customer message + context summary
   - Handles owner reply → forwards to customer as agent vibe
   - Timeout handling (notify customer if owner doesn't reply)

2. **Owner reply routing** — When owner sends a vibe to their agent with a customer context
   - Detect it's a reply to a specific customer conversation
   - Forward as agent vibe to the customer
   - Resume AI conversation

3. **Broadcast tool** — Owner sends "broadcast:" prefix message
   - Agent sends to all enabled customers
   - Rate limit (max N broadcasts per day)

4. **YAML-to-tools mapping** — Parse YAML services/hours/location into tool definitions
   - `list_services` → reads from YAML
   - `get_hours` → reads from YAML
   - `get_location` → reads from YAML

5. **Marketplace conversation handler** — Gemini conversation loop for Tier 1 agents
   - System prompt built from YAML definition
   - Built-in tools injected automatically
   - Guardrails from YAML enforced

### Flutter

1. **Owner conversation view** — Show escalated conversations in the agent chat thread
2. **Reply-to-customer UI** — Owner taps on escalated message, types reply
3. **Broadcast UI** — Simple text input for broadcast messages
4. **Agent stats** — Basic metrics (customers, conversations, response time)

### SDK (Python)

No changes needed for Tier 1 — it's entirely backend + app. The SDK is for Tier 2 only.

## Open Questions

1. **Credits** — Who pays? Customer's credits or owner's credits? Recommendation: customer pays (1 credit per message), owner pays nothing.

2. **Owner reply format** — How does the owner indicate which customer they're replying to? Options:
   - Each escalation is a separate "thread" in the owner's chat
   - Owner replies to the specific vibe (reply-to-vibe feature)
   - Agent asks "reply to Sarah's booking request?" for disambiguation

3. **YAML updates** — Can the owner update services/hours by talking to their own agent? ("change gel manicure to $40") This would require the agent to edit its own YAML definition.

4. **Availability** — Without calendar integration, the AI can't check real availability. Should the handoff message template include a slot request? ("Maria, Sarah wants Saturday 2pm — is that available? Reply YES or suggest another time.")

5. **Multiple owners** — Can a business have multiple people who handle handoffs? (e.g., Maria + her employee)

6. **Offline owner** — What happens when the owner doesn't respond for hours? Auto-message to customer? Close the conversation?
