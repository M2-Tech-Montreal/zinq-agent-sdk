"""
⚠️  REFERENCE CODE — not tested end-to-end. See examples/sentinel/ and examples/rosas_bakery/ for working agents.

Trading Agent — Monitor your crypto portfolio and get AI-powered alerts.

Connects to Binance (or any exchange via CCXT), watches your positions,
and sends you Zinq vibes when:
- A coin moves more than 5% in an hour
- Your portfolio hits a new daily high/low
- You ask "how's my portfolio?"
- Hourly P&L summary

Requirements:
    pip install zinq-agent ccxt apscheduler

Environment variables:
    ZINQ_API_KEY        - Your Zinq agent API key
    BINANCE_API_KEY     - Binance API key (read-only is fine)
    BINANCE_SECRET      - Binance API secret

Usage:
    python trading_bot.py
"""

import os
import ccxt
from decimal import Decimal
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from zinq_agent import ZinqAgent

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------

agent = ZinqAgent()  # reads ZINQ_API_KEY from env

exchange = ccxt.binance({
    "apiKey": os.environ["BINANCE_API_KEY"],
    "secret": os.environ["BINANCE_SECRET"],
    "enableRateLimit": True,
})

# Track state between checks
last_prices: dict[str, float] = {}
daily_high: float = 0.0
daily_low: float = float("inf")
ALERT_THRESHOLD = 0.05  # 5% move triggers alert

# --------------------------------------------------------------------------
# Portfolio helpers
# --------------------------------------------------------------------------

def get_portfolio() -> dict:
    """Fetch all non-zero balances and current prices."""
    balance = exchange.fetch_balance()
    positions = {}
    total_usd = 0.0

    for coin, amount in balance["total"].items():
        if amount > 0 and coin != "USD" and coin != "USDT":
            try:
                ticker = exchange.fetch_ticker(f"{coin}/USDT")
                price = ticker["last"]
                value = amount * price
                positions[coin] = {
                    "amount": amount,
                    "price": price,
                    "value_usd": round(value, 2),
                    "change_24h": round(ticker.get("percentage", 0), 2),
                }
                total_usd += value
            except Exception:
                pass  # skip coins without USDT pair

    # Include USDT balance
    usdt = balance["total"].get("USDT", 0)
    if usdt > 0:
        positions["USDT"] = {
            "amount": usdt,
            "price": 1.0,
            "value_usd": round(usdt, 2),
            "change_24h": 0,
        }
        total_usd += usdt

    return {"positions": positions, "total_usd": round(total_usd, 2)}


def format_portfolio(portfolio: dict) -> str:
    """Format portfolio as a readable vibe message."""
    lines = [f"Portfolio: ${portfolio['total_usd']:,.2f}\n"]

    sorted_positions = sorted(
        portfolio["positions"].items(),
        key=lambda x: x[1]["value_usd"],
        reverse=True,
    )

    for coin, pos in sorted_positions[:10]:  # top 10 holdings
        arrow = "+" if pos["change_24h"] >= 0 else ""
        lines.append(
            f"  {coin}: ${pos['value_usd']:,.2f} "
            f"({arrow}{pos['change_24h']}%)"
        )

    return "\n".join(lines)


def format_price_alert(coin: str, old_price: float, new_price: float) -> str:
    """Format a price movement alert."""
    change_pct = ((new_price - old_price) / old_price) * 100
    direction = "up" if change_pct > 0 else "down"
    emoji = "🚀" if change_pct > 0 else "📉"
    return (
        f"{emoji} {coin} is {direction} {abs(change_pct):.1f}%\n"
        f"${old_price:,.2f} → ${new_price:,.2f}"
    )


# --------------------------------------------------------------------------
# Scheduled checks
# --------------------------------------------------------------------------

def check_prices():
    """Check for significant price movements (runs every 5 min)."""
    global last_prices

    portfolio = get_portfolio()

    for coin, pos in portfolio["positions"].items():
        if coin == "USDT":
            continue

        price = pos["price"]
        if coin in last_prices:
            old_price = last_prices[coin]
            change = abs((price - old_price) / old_price)

            if change >= ALERT_THRESHOLD:
                alert = format_price_alert(coin, old_price, price)
                agent.vibes.send(text=alert)
                # Save to memory for context
                agent.memories.save(
                    key=f"alert_{coin}_{datetime.now().strftime('%H%M')}",
                    value=alert,
                    category="price_alerts",
                )

        last_prices[coin] = price


def hourly_summary():
    """Send hourly portfolio summary."""
    global daily_high, daily_low

    portfolio = get_portfolio()
    total = portfolio["total_usd"]

    # Track daily high/low
    if total > daily_high:
        daily_high = total
    if total < daily_low:
        daily_low = total

    summary = format_portfolio(portfolio)
    summary += f"\n\nDaily range: ${daily_low:,.2f} — ${daily_high:,.2f}"

    agent.vibes.send(text=summary)


def daily_reset():
    """Reset daily tracking at midnight."""
    global daily_high, daily_low
    portfolio = get_portfolio()
    daily_high = portfolio["total_usd"]
    daily_low = portfolio["total_usd"]

    agent.vibes.send(
        text=f"New day! Portfolio starting at ${portfolio['total_usd']:,.2f}"
    )


# --------------------------------------------------------------------------
# On-demand commands (polling-based)
# --------------------------------------------------------------------------

def check_commands():
    """Check for user commands via vibes (runs every 30 sec)."""
    vibes = agent.vibes.received(limit=5, unread=True)

    for vibe in vibes:
        text = (vibe.transcript or vibe.text or "").lower().strip()

        if not text:
            continue

        if any(w in text for w in ["portfolio", "holdings", "how am i doing", "balance"]):
            portfolio = get_portfolio()
            agent.vibes.send(text=format_portfolio(portfolio))

        elif any(w in text for w in ["price", "how much", "what's"]):
            # Extract coin name — ask Gemini to parse
            response = agent.gemini.chat(messages=[
                {"role": "system", "content": "Extract the cryptocurrency ticker symbol from this message. Reply with just the symbol (e.g., BTC, ETH, SOL). If none found, reply NONE."},
                {"role": "user", "content": text},
            ])
            coin = response.text.strip().upper()
            if coin != "NONE":
                try:
                    ticker = exchange.fetch_ticker(f"{coin}/USDT")
                    change = ticker.get("percentage", 0)
                    arrow = "+" if change >= 0 else ""
                    agent.vibes.send(
                        text=f"{coin}: ${ticker['last']:,.2f} ({arrow}{change:.1f}% 24h)\n"
                             f"High: ${ticker['high']:,.2f} | Low: ${ticker['low']:,.2f}\n"
                             f"Volume: ${ticker['quoteVolume']:,.0f}"
                    )
                except Exception:
                    agent.vibes.send(text=f"Couldn't find {coin}. Check the ticker symbol.")

        elif any(w in text for w in ["alert", "watch", "notify"]):
            # Ask Gemini to parse alert request
            response = agent.gemini.chat(messages=[
                {"role": "system", "content": "Parse this alert request. Extract: coin (ticker), direction (up/down/both), threshold (percentage). Reply as JSON: {\"coin\": \"BTC\", \"direction\": \"up\", \"threshold\": 5}"},
                {"role": "user", "content": text},
            ])
            agent.vibes.send(text=f"Got it. I'll watch for that.\n(Custom alerts coming soon — for now I alert on any 5%+ moves)")

        elif any(w in text for w in ["summary", "recap", "today"]):
            hourly_summary()

        elif any(w in text for w in ["help", "what can you do"]):
            agent.vibes.send(
                text="I can help with:\n"
                     "• \"How's my portfolio?\" — current holdings\n"
                     "• \"BTC price\" — any coin price\n"
                     "• \"Today's summary\" — P&L recap\n"
                     "• I auto-alert on 5%+ moves every 5 min\n"
                     "• Hourly portfolio summaries"
            )


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading agent starting...")

    # Initial portfolio snapshot
    portfolio = get_portfolio()
    daily_high = portfolio["total_usd"]
    daily_low = portfolio["total_usd"]

    agent.vibes.send(
        text=f"Trading agent online.\n{format_portfolio(portfolio)}"
    )

    # Save initial prices
    for coin, pos in portfolio["positions"].items():
        if coin != "USDT":
            last_prices[coin] = pos["price"]

    scheduler = BlockingScheduler()
    scheduler.add_job(check_commands, "interval", seconds=30)
    scheduler.add_job(check_prices, "interval", minutes=5)
    scheduler.add_job(hourly_summary, "cron", minute=0)
    scheduler.add_job(daily_reset, "cron", hour=0, minute=0)

    print(f"Watching {len(portfolio['positions'])} positions...")
    scheduler.start()
