# Zinq Agent SDK — Examples

## Working Agents (tested end-to-end)

| Agent | Type | Description |
|-------|------|-------------|
| [**sentinel/**](sentinel/) | Personal (`zak_`) | Email & Slack monitor — sends urgent vibes, daily digests |
| [**rosas_bakery/**](rosas_bakery/) | Business (`zbk_`) | Marketplace agent — menu browsing, order placement via webhooks |

## Reference Code (not tested — for learning only)

These examples demonstrate SDK patterns but have **not been deployed or tested end-to-end**. Use them as starting points, not production templates.

| Example | Pattern | Description |
|---------|---------|-------------|
| [echo_bot.py](echo_bot.py) | Webhook | Simplest possible agent — echoes back messages |
| [appointment_bot.py](appointment_bot.py) | Polling | Appointment scheduler using memories |
| [personal_shopper.py](personal_shopper.py) | Gemini + Diary | AI shopping assistant using diary context |
| [trading_bot.py](trading_bot.py) | Polling | Crypto portfolio monitoring with alerts |
| [dr_sarah_nutrition/](dr_sarah_nutrition/) | Marketplace | Nutrition coach with YAML definition |
| [joes_barber/](joes_barber/) | Marketplace | Barbershop appointment booker |

## Getting Started

Start with a working agent:

```bash
# Personal agent (monitors your email)
cd sentinel/
export ZINQ_API_KEY=zak_your_key
python3 sentinel.py

# Business agent (bakery with menu + orders)
cd rosas_bakery/
export ZINQ_BIZ_KEY=zbk_your_key
bash start.sh
```

## Creating Your Own Agent

See the [SDK README](../README.md) for full documentation. The two working agents above are the best reference for building your own.
