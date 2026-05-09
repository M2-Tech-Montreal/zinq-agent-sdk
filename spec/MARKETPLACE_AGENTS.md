# Marketplace Agents — Full Spec

## Overview

Marketplace agents are AI agents that represent a business on Zinq. Customers find them in the marketplace, enable them, and interact through chat. There are two tiers:

- **Tier 1 (No-Code)** — Business owner describes their business in plain English, AI generates a YAML agent. No Python, no webhook, no server. Human handoff for anything the AI can't handle.
- **Tier 2 (SDK/Webhook)** — Same YAML definition, but a developer adds a Python webhook server for real-time integrations (calendar, inventory, payments).

Both tiers support payments via Zinq credits.

---

## 1. Who Is This For?

Small businesses and solo operators:
- Nail salons, barber shops, spas
- Bakeries, cafes, food trucks
- Personal trainers, yoga instructors
- Tutors, music teachers
- Plumbers, electricians, cleaners
- Photographers, freelance designers
- Pet groomers, dog walkers
- Handmade goods sellers (candles, jewelry, art)

---

## 2. Creation Flow

### In-App (Flutter)

1. Owner opens Zinq → Marketplace → Create Agent
2. Picks **Business** (vs Personal)
3. Types business name + description in plain English
4. Taps **"Generate My Agent"**
5. Backend calls Gemini → generates YAML definition (personality, tools, services, hours, guardrails)
6. Backend validates YAML with marketplace parser
7. Owner previews agent (name, bio, avatar)
8. Owner taps **"Go Live"** → agent appears in marketplace
9. Owner gets a one-time API key (for SDK access if they want Tier 2 later)

Screen: `create_marketplace_agent_screen.dart`

### SDK (Python)

```python
from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin(api_key="zbk_xxx")

# AI generates YAML from description
result = admin.agent.generate(
    "A barber shop in Brooklyn. Haircuts, beard trims, hot towel shaves. "
    "Open Tue-Sat 9am-7pm.",
    name="Joe's Barber Shop"
)

# Review the AI's work (score 1-10, issues, suggestions)
review = admin.agent.review(yaml=result["yamlDefinition"])

# Refine with feedback
refined = admin.agent.refine(
    yaml=result["yamlDefinition"],
    feedback="Add a loyalty program tool and change the tone to be more casual"
)

# Deploy
admin.agent.deploy(refined["yaml"])
```

### Backend Endpoints

All under `/marketplace/agents`:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/generate` | No | AI generates YAML from business description |
| POST | `/validate` | No | Validates YAML against marketplace parser |
| POST | `/review` | No | AI quality review (score 1-10, issues, suggestions) |
| POST | `/refine` | No | AI improves YAML based on user feedback |
| POST | `/create` | Yes | Creates agent system user, returns API key |

---

## 3. YAML Agent Definition

The YAML defines everything about the agent's behavior:

```yaml
agent:
  name: "Maria's Nails"
  bio: "Your neighborhood nail salon in Brooklyn."
  category: beauty
  language: [en, es]

personality:
  tone: warm, professional
  greeting: "Hey! Welcome to Maria's Nails. Looking to book or just browsing?"
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

products:
  - name: Lavender Candle
    price: 18.00
    description: "Hand-poured lavender soy candle, 8oz"
    in_stock: true
  - name: Custom Scent
    price: 35.00
    requires_human_review: true

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

shipping:
  free_above: 50.00
  flat_rate: 5.00
  processing_days: 2

policies:
  cancellation: "Please cancel at least 2 hours before your appointment."
  walk_ins: "Walk-ins welcome but appointments preferred."

payments:
  enabled: true
  currency: usd

guardrails:
  - Never discuss competitors
  - Don't give medical advice
  - Redirect complaints to owner immediately
  - Never confirm a booking — always hand off to owner
  - Never quote prices not on the service list
```

---

## 4. Conversation Flow

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

If customer wants to buy a product:
  → AI calls create_order tool
  → Customer gets a confirm button vibe
  → Customer taps confirm → credits deducted → order created
  → Owner gets notified
```

### What the AI Can Do (from YAML alone)

- Answer questions about services, pricing, hours, location
- Describe menu items, packages, products
- Explain policies (cancellation, refund, etc.)
- Greet customers with the right tone/personality
- Speak multiple languages (if specified)
- Create orders and collect payment via credits
- Redirect off-topic questions politely

### What Requires Human Handoff

- **Booking confirmations** — AI says "I'll check with [Owner]", hands off
- **Custom quotes** — anything not in the fixed price list
- **Complaints** — always escalate
- **Custom products** — items marked `requires_human_review: true`
- **Anything the AI is unsure about** — better to ask than guess

---

## 5. Built-In Tools

Every marketplace agent gets these tools automatically. No code required.

### `request_human_review`

Escalates the conversation to the business owner.

**Triggers:** booking request, complaint, custom quote, AI unsure, customer asks for a human.

**Flow:**
1. Conversation status → `awaiting_human`
2. Owner gets a vibe: "New message from Sarah about booking: 'Can I get a gel mani Saturday at 2pm?' — Reply here to respond."
3. Owner replies in-app
4. Customer sees the reply as a vibe from the agent
5. Conversation status → `active`

If owner doesn't reply within configurable timeout: "Maria will get back to you shortly."

### `list_services`

Returns service list from YAML. Prevents hallucinated prices.

### `list_products`

Returns product catalog from YAML with names, prices, descriptions, stock status.

### `get_hours`

Returns business hours. Answers "are you open Saturday?" / "what time do you close?"

### `get_location`

Returns address and contact info.

### `create_order`

Creates an order from the conversation. Calculates subtotal, shipping.

**Parameters:** `items` — list of `{product_name, quantity}`
**Returns:** `order_id`, `subtotal`, `shipping`, `total_credits`

Sends a confirm button vibe to the customer.

### `check_order_status`

Customer asks "where's my order?" → returns status, tracking number.

### `update_inventory` (owner-initiated)

Owner says "out of stock: lavender candle" → agent stops selling it.
Owner says "back in stock: lavender candle" → agent re-enables it.

### `send_broadcast` (owner-initiated)

Owner sends "broadcast: 20% off all manicures today!" → agent vibes all enabled customers.

---

## 6. Payments

### Credits as Currency

Customers already buy credits via Apple Pay / Google Pay. Those same credits are the payment method for purchases. No second payment system. No Stripe for sellers.

```
Customer has 10,000 credits
Customer buys 2x Lavender Candle ($36 = 3,600 credits)
  → 3,600 credits deducted instantly
  → Order confirmed
  → Zinq pays owner monthly (minus platform fee)
```

**Credit-to-dollar conversion:** 100 credits = $1.

**Why credits, not Stripe Connect:**
- No Stripe onboarding for sellers (no KYC, no bank details, no tax ID)
- One-tap purchase — customer already has credits
- No second payment flow — customer paid once (Apple Pay for credits), done
- Works globally instantly
- Zinq handles refunds, disputes, chargebacks centrally
- Sellers just receive a monthly payout

### Purchase UX

```json
{
  "vibeType": "action",
  "textContent": "Your order:\n2x Lavender Candle — 3,600 credits ($36)\n\nYou have 10,000 credits available.",
  "buttons": [
    {
      "label": "Confirm & Pay 3,600 credits",
      "action": "deduct_credits",
      "amount": 3600,
      "order_id": "order_1847"
    }
  ]
}
```

If insufficient credits → "Buy Credits" button → Apple Pay → return to confirm.

### Owner Payouts

Monthly payout to the business owner:

```
Total orders in May:       $580.00
Zinq platform fee (15%):  -$87.00
Owner payout:              $493.00
```

Payout via bank transfer, Wise, or PayPal. Zinq handles tax reporting (1099 for US sellers).

### Revenue Model

```
Customer buys $58 worth of credits (Apple Pay)
  Apple fee (30%):         already paid at credit purchase time
  Customer spends 5,800 credits on products
  Zinq platform fee (15%): -$8.70
  Owner payout:             $49.30
```

Compare to Shopify: $39/month + 2.9% + $0.30 per transaction.
Zinq: $0/month + 15% per transaction. Zero risk to start.

---

## 7. Owner Experience

Everything happens in the Zinq app. No dashboard needed.

- **New order vibes:** "New order #1847 — 2x Lavender, 1x Vanilla — $58.00 (paid)"
- **Order list:** "show orders" → agent lists recent orders
- **Revenue:** "how much did I make today?" → agent calculates
- **Inventory:** "out of stock: vanilla" → agent stops selling
- **Shipping:** "shipped order 1847, tracking USPS123456" → customer gets tracking vibe
- **Broadcasts:** "broadcast: 20% off today!" → all customers notified
- **Stats:** "stats" → customer count, conversations, response time

---

## 8. Customer Experience

1. Customer finds "Maria's Nails" in marketplace or via shared link
2. Enables the agent (appears as a contact)
3. "do you have anything open Saturday?"
4. AI: "Saturday is looking good! What service?"
5. "gel mani + pedi combo at 2pm"
6. AI: "Let me check with Maria — I'll get back to you shortly."
7. Maria replies "confirmed!"
8. Customer gets: "You're all set! Gel mani + pedi combo, Saturday at 2pm."

For shops:
1. "what do you have?"
2. AI lists products with prices
3. "I'll take 2 lavender candles"
4. AI: "2x Lavender — 3,600 credits ($36). Confirm?" [Confirm & Pay]
5. Customer taps → credits deducted → "Order confirmed! Ships in 2 days."

---

## 9. Tier 1 vs Tier 2

| Feature | Tier 1 (No-Code) | Tier 2 (SDK/Webhook) |
|---------|-------------------|----------------------|
| Setup | Describe business → done | Write Python webhook server |
| Conversations | Gemini + YAML | Gemini + YAML + custom tools |
| Bookings | Human handoff | Can check real calendar |
| Orders | Built-in (credits) | Built-in + custom logic |
| Payments | Credits (built-in) | Credits + custom integrations |
| Inventory | From YAML (static) | Can query live database |
| Human handoff | Built-in | Built-in + custom escalation |
| Server required | No | Yes |
| Cost to owner | $0 | Hosting cost for webhook |

---

## 10. Competitive Positioning

| Feature | Shopify | Zinq Agent Shop |
|---------|---------|-----------------|
| Monthly fee | $39+ | $0 |
| Setup time | Hours | Minutes |
| Website needed | Yes | No |
| App needed | Yes (Shopify app) | Already in Zinq |
| Customer acquisition | SEO, ads, social | Marketplace + word of mouth |
| Customer relationship | Transactional | Conversational (AI + human) |
| Product catalog | Dashboard | Describe in chat |
| Payments | Stripe/Shopify Payments | Credits (Apple Pay) |
| Inventory | Dashboard | Talk to your agent |

---

## 11. What Needs to Be Built

### Backend

1. **`request_human_review` tool** — changes status to `awaiting_human`, sends vibe to owner, routes owner reply back to customer
2. **Owner reply routing** — detect reply to specific customer, forward as agent vibe
3. **Order model** — orders table (items, total_credits, status, tracking, user_id, agent_id)
4. **`create_order` tool** — creates order, validates credit balance, sends confirm button vibe
5. **Credit deduction for purchases** — atomic deduct on confirm tap
6. **`check_order_status` tool** — returns order status and tracking
7. **Confirm button vibe type** — vibe with tappable credit-deduction action
8. **Product/service catalog from YAML** — parse into tool definitions
9. **Broadcast tool** — send to all enabled customers (rate limited)
10. **Marketplace conversation handler** — Gemini loop with YAML as system prompt + built-in tools
11. **Owner payout tracking** — monthly revenue aggregation per agent owner
12. **Payout service** — monthly batch payout (bank transfer / Wise / PayPal)

### Flutter

1. **Confirm & Pay button vibe** — render tappable "Pay X credits" in chat
2. **Insufficient credits flow** — "Buy Credits" → Apple Pay → return to confirm
3. **Owner conversation view** — show escalated conversations in agent chat
4. **Reply-to-customer UI** — owner taps escalated message, types reply
5. **Order status vibes** — render order confirmation with details
6. **Owner payout settings** — bank account / Wise / PayPal configuration
7. **Agent stats** — basic metrics (customers, conversations, revenue)

### SDK (Python — Tier 2 only)

1. **`admin.orders.list()`** — list orders
2. **`admin.orders.update(order_id, status, tracking)`** — update shipping
3. **Webhook events** — `order.created`, `order.paid`, `order.shipped`

---

## 12. Open Questions

1. **Owner reply routing** — how does the owner indicate which customer they're replying to?
   - Each escalation as a separate thread
   - Reply-to-vibe feature
   - Agent asks for disambiguation

2. **YAML updates via chat** — can the owner say "change gel manicure to $40" and the agent updates the YAML? Requires agent to edit its own definition.

3. **Availability** — without calendar integration (Tier 1), the AI can't check real availability. Handoff template should include: "Maria, Sarah wants Saturday 2pm — available? Reply YES or suggest another time."

4. **Multiple owners** — can a business have multiple people handling handoffs? (Maria + her employee)

5. **Offline owner** — what happens when owner doesn't respond for hours? Auto-message? Close conversation?

6. **Refunds** — customer asks for refund → credits returned to customer, deducted from owner's payout? Or dispute process?

7. **Digital products** — downloads, access codes. No shipping needed. Phase 2?

---

## 13. Roadmap

### Phase 1 (MVP)
1. Products/services in YAML → `list_products`, `list_services` tools
2. `request_human_review` tool with owner notification vibes
3. Owner reply routing
4. `create_order` tool with credit deduction
5. Confirm button vibe type
6. Owner notification vibes for new orders
7. Simple order status tracking

### Phase 2
1. Inventory management via chat
2. Shipping integration (tracking numbers)
3. Discount codes
4. Order history for customers
5. Revenue analytics for owners
6. Refunds via chat
7. Broadcast tool

### Phase 3
1. Subscription products (monthly boxes, memberships)
2. Digital products (downloads, access codes)
3. Multi-currency
4. Tax calculation per jurisdiction
5. Customer reviews and ratings
6. Multiple owner support
