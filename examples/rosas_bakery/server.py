"""Rosa's Bakery -- webhook server for pickup orders and custom cakes.

Demonstrates:
- ZinqBusinessWebhook for action routing (request_pickup, request_custom_cake)
- ZinqMarketplaceAdmin for data collections (daily_specials, orders)
- Human handoff for custom cake requests
- Broadcasting daily specials to all customers
- Data-driven menu with dynamic specials

Setup:
    pip install zinq-agent[webhook]

    export ZINQ_BIZ_KEY="zbk_your_key_here"
    export ZINQ_WEBHOOK_SECRET="zws_your_secret_here"

    python server.py
"""

import os
from datetime import datetime, timedelta

from zinq_agent import ZinqMarketplaceAdmin
from zinq_agent.webhook import ZinqBusinessWebhook

# ---------------------------------------------------------------------------
# Initialize clients
# ---------------------------------------------------------------------------

admin = ZinqMarketplaceAdmin(api_key=os.environ.get("ZINQ_BIZ_KEY"))
webhook = ZinqBusinessWebhook(
    secret=os.environ.get("ZINQ_WEBHOOK_SECRET", "zws_dev_secret"),
    admin=admin,
    skip_signature_check=os.environ.get("DEV_MODE") == "1",
)

# ---------------------------------------------------------------------------
# Menu and pricing
# ---------------------------------------------------------------------------

MENU = {
    "Sourdough Loaf": 8.00,
    "Whole Wheat Loaf": 7.00,
    "Ciabatta": 6.00,
    "Baguette": 5.00,
    "Croissant": 4.50,
    "Almond Croissant": 5.50,
    "Cinnamon Roll": 5.00,
    "Blueberry Muffin": 4.00,
    "Drip Coffee": 3.00,
    "Latte": 5.00,
    "Hot Chocolate": 4.50,
}

# In-memory orders (use a database in production)
orders: dict[str, dict] = {}
_next_order_id = 100


def _generate_order_id() -> str:
    global _next_order_id
    _next_order_id += 1
    return f"RB-{_next_order_id}"


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------


@webhook.action("request_pickup")
def request_pickup(params: dict, session_id: str) -> dict:
    """Place a pickup order."""
    items_str = params.get("items", "")
    pickup_time = params.get("pickup_time", "")
    customer_name = params.get("customer_name", "Customer")
    notes = params.get("notes", "")

    if not items_str or not pickup_time:
        return {"error": "Please specify items and a pickup time."}

    # Parse items: "2 Sourdough Loaf, 4 Croissant"
    parsed_items = []
    total = 0.0

    for item_entry in items_str.split(","):
        item_entry = item_entry.strip()
        if not item_entry:
            continue

        # Try to extract quantity and item name
        parts = item_entry.split(" ", 1)
        try:
            quantity = int(parts[0])
            item_name = parts[1].strip() if len(parts) > 1 else ""
        except ValueError:
            quantity = 1
            item_name = item_entry

        # Find the menu item (case-insensitive fuzzy match)
        matched_name = None
        for menu_item in MENU:
            if menu_item.lower() in item_name.lower() or item_name.lower() in menu_item.lower():
                matched_name = menu_item
                break

        if matched_name is None:
            return {
                "error": f"Sorry, I don't recognize '{item_name}'. "
                "Check our menu and try again.",
                "available_items": list(MENU.keys()),
            }

        price = MENU[matched_name]
        line_total = price * quantity
        total += line_total
        parsed_items.append({
            "name": matched_name,
            "quantity": quantity,
            "unit_price": price,
            "line_total": line_total,
        })

    # Create the order
    order_id = _generate_order_id()
    order = {
        "id": order_id,
        "customer_name": customer_name,
        "items": parsed_items,
        "total": round(total, 2),
        "pickup_time": pickup_time,
        "notes": notes,
        "session_id": session_id,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
    }
    orders[order_id] = order

    # Persist to data collection
    try:
        admin.data.add("orders", order)
    except Exception:
        pass

    # Build a readable receipt
    item_lines = []
    for item in parsed_items:
        item_lines.append(
            f"  {item['quantity']}x {item['name']} - ${item['line_total']:.2f}"
        )

    return {
        "confirmed": True,
        "order_id": order_id,
        "items": parsed_items,
        "total": f"${total:.2f}",
        "pickup_time": pickup_time,
        "customer_name": customer_name,
        "receipt": "\n".join(item_lines),
        "message": (
            f"Order {order_id} confirmed! Your order will be ready for "
            f"pickup at {pickup_time}. Total: ${total:.2f}. "
            f"See you soon, {customer_name}!"
        ),
    }


@webhook.action("request_custom_cake")
def request_custom_cake(params: dict, session_id: str) -> dict:
    """Handle a custom cake request. Complex orders escalate to Rosa."""
    occasion = params.get("occasion", "")
    servings = params.get("servings", 0)
    flavor = params.get("flavor", "not specified")
    date_needed = params.get("date_needed", "")
    details = params.get("details", "")

    if not occasion or not date_needed:
        return {"error": "Please tell me the occasion and when you need the cake."}

    # Validate the date is at least 3 days out
    try:
        needed_date = datetime.strptime(date_needed, "%Y-%m-%d").date()
        days_until = (needed_date - datetime.now().date()).days
    except ValueError:
        return {"error": f"Invalid date format: {date_needed}. Use YYYY-MM-DD."}

    if days_until < 3:
        return {
            "error": "Custom cakes need at least 3 days advance notice. "
            f"That date is only {days_until} day(s) away.",
            "earliest_date": (
                datetime.now().date() + timedelta(days=3)
            ).isoformat(),
        }

    # Estimate price based on servings
    if servings <= 10:
        price_range = "$45 - $65"
    elif servings <= 25:
        price_range = "$65 - $120"
    elif servings <= 50:
        price_range = "$120 - $200"
    else:
        price_range = "$200+"

    # Save the request
    request_data = {
        "occasion": occasion,
        "servings": servings,
        "flavor": flavor,
        "date_needed": date_needed,
        "details": details,
        "session_id": session_id,
        "status": "pending_review",
        "created_at": datetime.now().isoformat(),
    }

    try:
        admin.data.add("cake_requests", request_data)
    except Exception:
        pass

    # Complex designs always escalate to Rosa
    needs_human = (
        servings > 30
        or "tiered" in details.lower()
        or "wedding" in occasion.lower()
        or "fondant" in details.lower()
        or "sculpted" in details.lower()
    )

    if needs_human:
        return {
            "received": True,
            "escalated": True,
            "price_estimate": price_range,
            "message": (
                f"I've noted your cake request for {occasion} on {date_needed} "
                f"({servings} servings, {flavor}). This sounds like a special "
                "project -- let me connect you with Rosa directly so she can "
                "discuss the details and give you an exact quote."
            ),
        }

    return {
        "received": True,
        "escalated": False,
        "price_estimate": price_range,
        "occasion": occasion,
        "servings": servings,
        "flavor": flavor,
        "date_needed": date_needed,
        "message": (
            f"Got it! Custom {flavor} cake for {occasion}, serving {servings} "
            f"people, needed by {date_needed}. Estimated price: {price_range}. "
            "Rosa will confirm the final price and details within 24 hours."
        ),
    }


# ---------------------------------------------------------------------------
# Standard webhook handlers
# ---------------------------------------------------------------------------


@webhook.on("agent.wave")
def greet(event):
    """Greet customers and mention today's specials."""
    # Check for today's specials in the data collection
    specials_text = ""
    try:
        specials = admin.data.list("daily_specials", limit=5)
        if specials:
            today = datetime.now().strftime("%Y-%m-%d")
            todays = [s for s in specials if s.get("date") == today]
            if todays:
                lines = [f"  - {s['item']}: {s.get('note', '')}" for s in todays]
                specials_text = "\n\nToday's specials:\n" + "\n".join(lines)
    except Exception:
        pass

    if event.data.is_first_wave:
        admin.conversations.reply(
            str(event.user.id),
            f"Welcome to Rosa's Bakery! I can help you with:\n\n"
            f"- Place a pickup order\n"
            f"- Browse our menu\n"
            f"- Request a custom cake\n"
            f"- Check today's specials"
            f"{specials_text}",
        )
    else:
        admin.conversations.reply(
            str(event.user.id),
            f"Hey, welcome back! What sounds good today?{specials_text}",
        )


# ---------------------------------------------------------------------------
# Seed menu data
# ---------------------------------------------------------------------------


def seed_menu():
    """Load the menu into data collections."""
    try:
        admin.data.clear("menu")
        for name, price in MENU.items():
            admin.data.add("menu", {"name": name, "price": price})
        print(f"Seeded {len(MENU)} menu items.")
    except Exception as e:
        print(f"Could not seed menu (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    seed_menu()
    print("Rosa's Bakery agent is running on port 8080...")
    print("Webhook URL: http://localhost:8080/webhook")
    print("\nRun morning_update.py each morning to set daily specials.")
    webhook.start(port=8080)
