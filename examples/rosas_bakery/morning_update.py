#!/usr/bin/env python3
"""Morning update — set daily specials and broadcast to all customers.

Rosa runs this each morning (or sets up a cron job):
    python morning_update.py

Cron example (runs at 6am daily):
    0 6 * * * cd /path/to/rosas_bakery && ZINQ_BIZ_KEY=zbk_xxx python morning_update.py
"""

import os
from zinq_agent import ZinqMarketplaceAdmin

API_KEY = os.environ.get("ZINQ_BIZ_KEY", "")
if not API_KEY:
    print("ERROR: Set ZINQ_BIZ_KEY first")
    exit(1)

admin = ZinqMarketplaceAdmin(api_key=API_KEY, base_url="https://zinq-app.com/api")

# ── Edit these each morning ──────────────────────────────────────────────

TODAYS_SPECIALS = [
    {"name": "Lavender Honey Croissant", "price": 6.00, "note": "Limited batch — only 20 made today!"},
    {"name": "Rosemary Focaccia", "price": 7.50, "note": "Fresh rosemary from the garden."},
    {"name": "Matcha Muffin", "price": 4.50, "note": "New recipe — tell us what you think!"},
]

# ── Update specials collection ───────────────────────────────────────────

# Clear yesterday's specials
try:
    old = admin.data.list("specials")
    for item in old:
        admin.data.delete("specials", item.get("id"))
    print(f"Cleared {len(old)} old specials")
except Exception:
    pass

# Add today's
for special in TODAYS_SPECIALS:
    admin.data.add("specials", special)
    print(f"  Added: {special['name']} — ${special['price']:.2f}")

# ── Broadcast to all customers ───────────────────────────────────────────

specials_text = "\n".join(
    f"  {s['name']} — ${s['price']:.2f}\n    {s['note']}"
    for s in TODAYS_SPECIALS
)

broadcast = (
    "Good morning from Rosa's Bakery!\n\n"
    "Fresh out of the oven today:\n"
    f"{specials_text}\n\n"
    "Order ahead for pickup — just message me!"
)

admin.broadcast(broadcast)
print(f"\nBroadcast sent to all customers")
