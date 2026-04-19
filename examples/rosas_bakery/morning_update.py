"""Morning Update -- Rosa runs this each morning to set daily specials.

Demonstrates:
- ZinqMarketplaceAdmin.data for updating collections
- ZinqMarketplaceAdmin.broadcast for notifying all customers
- A standalone script that manages agent data without running a server

Usage:
    # Set today's specials and broadcast to customers
    python morning_update.py

    # Run automatically every morning at 6am with cron:
    # 0 6 * * * cd /path/to/rosas_bakery && python morning_update.py

Setup:
    export ZINQ_BIZ_KEY="zbk_your_key_here"
"""

import os
import sys
from datetime import datetime

from zinq_agent import ZinqMarketplaceAdmin

admin = ZinqMarketplaceAdmin(api_key=os.environ.get("ZINQ_BIZ_KEY"))

# ---------------------------------------------------------------------------
# Today's specials -- edit these each morning
# ---------------------------------------------------------------------------

TODAYS_SPECIALS = [
    {
        "item": "Lavender Honey Croissant",
        "note": "Limited batch -- only 20 made today!",
        "price": 6.00,
    },
    {
        "item": "Rosemary Focaccia",
        "note": "Fresh rosemary from the garden. Perfect with olive oil.",
        "price": 7.50,
    },
    {
        "item": "Matcha Muffin",
        "note": "New recipe -- tell us what you think!",
        "price": 4.50,
    },
]

# Set to True to send a broadcast notification to all customers
SEND_BROADCAST = True


def update_specials():
    """Upload today's specials to the data collection."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Clear yesterday's specials
    try:
        admin.data.clear("daily_specials")
    except Exception:
        pass

    # Add today's specials
    for special in TODAYS_SPECIALS:
        special["date"] = today
        admin.data.add("daily_specials", special)

    print(f"Updated {len(TODAYS_SPECIALS)} specials for {today}:")
    for s in TODAYS_SPECIALS:
        print(f"  - {s['item']} (${s['price']:.2f}) -- {s['note']}")


def broadcast_specials():
    """Send a broadcast to all customers about today's specials."""
    lines = ["Good morning from Rosa's Bakery!\n"]
    lines.append("Fresh out of the oven today:\n")
    for s in TODAYS_SPECIALS:
        lines.append(f"  {s['item']} - ${s['price']:.2f}")
        lines.append(f"    {s['note']}\n")
    lines.append("Order ahead for pickup -- just message me!")

    message = "\n".join(lines)

    result = admin.broadcast(message)
    print(f"\nBroadcast sent to {result.get('recipientCount', '?')} customers.")


def check_stats():
    """Print quick stats about the agent."""
    try:
        user_count = admin.users.count()
        print(f"\nCustomers using Rosa's Bakery agent: {user_count}")
    except Exception:
        pass

    try:
        stats = admin.reviews.stats()
        print(
            f"Reviews: {stats.get('avg_rating', 'N/A')}/5 "
            f"({stats.get('total_count', 0)} total)"
        )
    except Exception:
        pass

    try:
        orders = admin.data.list("orders", limit=5)
        pending = [o for o in orders if o.get("status") == "confirmed"]
        print(f"Pending orders today: {len(pending)}")
    except Exception:
        pass


def main():
    print("=" * 50)
    print("Rosa's Bakery -- Morning Update")
    print(f"Date: {datetime.now().strftime('%A, %B %d, %Y')}")
    print("=" * 50)

    update_specials()

    if SEND_BROADCAST:
        broadcast_specials()
    else:
        print("\nBroadcast skipped (SEND_BROADCAST=False).")

    check_stats()
    print("\nDone! Have a great day of baking.")


if __name__ == "__main__":
    main()
