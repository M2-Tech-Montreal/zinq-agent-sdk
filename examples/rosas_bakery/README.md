# Rosa's Bakery

A complete marketplace agent example for a bakery. Customers order pickups, ask about daily specials, and request custom cakes. Rosa sends morning broadcasts with what's fresh today.

## What this demonstrates

- **Pickup ordering** with item parsing, pricing, and receipt generation
- **Daily specials** managed through data collections and updated each morning
- **Custom cake requests** with automatic escalation to human for complex designs
- **Broadcasting** daily specials to all customers
- **Human handoff** for wedding cakes, large orders, and complaints
- **Standalone data management scripts** (morning_update.py)

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Agent definition -- personality, menu, tools, escalation rules |
| `server.py` | Webhook server -- handles request_pickup, request_custom_cake |
| `morning_update.py` | Script Rosa runs each morning to set daily specials and broadcast |

## Prerequisites

- Python 3.10+
- A Zinq business account (get one at [zinq-app.com/business](https://zinq-app.com/business))
- Your `ZINQ_BIZ_KEY` and `ZINQ_WEBHOOK_SECRET` from the dashboard

## Setup

1. Install dependencies:

```bash
pip install zinq-agent[webhook]
```

2. Set environment variables:

```bash
export ZINQ_BIZ_KEY="zbk_your_key_here"
export ZINQ_WEBHOOK_SECRET="zws_your_secret_here"
```

3. Deploy the agent definition:

```bash
python -c "
from zinq_agent import ZinqMarketplaceAdmin
admin = ZinqMarketplaceAdmin()
result = admin.agent.deploy(open('agent.yaml').read())
print(f'Deployed: {result}')
"
```

4. Start the webhook server:

```bash
python server.py
```

5. Run the morning update (edit TODAYS_SPECIALS in the script first):

```bash
python morning_update.py
```

## Automating the morning update

Set up a cron job to run the morning update automatically:

```bash
# Edit TODAYS_SPECIALS in morning_update.py, then:
crontab -e

# Add this line (runs at 6am every day):
0 6 * * * cd /path/to/rosas_bakery && ZINQ_BIZ_KEY=zbk_xxx python morning_update.py
```

Or use a simple web form to update specials and trigger the broadcast.

## Sample conversation

```
Customer: What's fresh today?
Agent:    Good morning! Here's what's special today:

            Lavender Honey Croissant - $6.00
              Limited batch -- only 20 made today!
            Rosemary Focaccia - $7.50
              Fresh rosemary from the garden.
            Matcha Muffin - $4.50
              New recipe -- tell us what you think!

          Want to place a pickup order?

Customer: I'll take 2 sourdough loaves and 4 croissants, pickup at 10am.
          Name is Carlos.
Agent:    [calls request_pickup]

Agent:    Order RB-101 confirmed! Here's your receipt:

            2x Sourdough Loaf - $16.00
            4x Croissant - $18.00

          Total: $34.00
          Pickup: 10:00 AM
          See you soon, Carlos!

Customer: I also need a birthday cake for my daughter. She turns 7
          next Saturday. Vanilla with rainbow sprinkles, feeds about 15.
Agent:    [calls request_custom_cake]

Agent:    Got it! Custom vanilla cake for a birthday, serving 15 people,
          needed by next Saturday. Estimated price: $65 - $120.
          Rosa will confirm the final price and details within 24 hours.

Customer: Actually, make it a 3-tier wedding cake with fondant flowers.
Agent:    [calls request_custom_cake with escalation]

Agent:    This sounds like a beautiful project! Let me connect you with
          Rosa directly -- she'll want to discuss the design details
          with you personally.
          [conversation escalated to human]
```

## Broadcast example

When Rosa runs `morning_update.py`, all customers who have enabled the bakery agent receive:

```
Good morning from Rosa's Bakery!

Fresh out of the oven today:

  Lavender Honey Croissant - $6.00
    Limited batch -- only 20 made today!

  Rosemary Focaccia - $7.50
    Fresh rosemary from the garden. Perfect with olive oil.

  Matcha Muffin - $4.50
    New recipe -- tell us what you think!

Order ahead for pickup -- just message me!
```
