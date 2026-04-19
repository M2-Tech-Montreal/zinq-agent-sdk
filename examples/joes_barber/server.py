"""Joe's Barber Shop -- webhook server for appointment booking.

Demonstrates:
- ZinqBusinessWebhook for tool-call action routing
- ZinqMarketplaceAdmin for data management and replying
- Service menu stored in data collections
- Appointment slot management with conflict detection
- Cancellation with ID lookup

Setup:
    pip install zinq-agent[webhook]

    export ZINQ_BIZ_KEY="zbk_your_key_here"
    export ZINQ_WEBHOOK_SECRET="zws_your_secret_here"

    python server.py
"""

import json
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
# In-memory store (replace with a real database in production)
# ---------------------------------------------------------------------------

# Appointments keyed by ID
appointments: dict[str, dict] = {}

# Shop hours per day of week (0=Monday, 6=Sunday)
SHOP_HOURS = {
    0: ("09:00", "19:00"),  # Monday
    1: ("09:00", "19:00"),  # Tuesday
    2: ("09:00", "19:00"),  # Wednesday
    3: ("09:00", "20:00"),  # Thursday
    4: ("09:00", "20:00"),  # Friday
    5: ("08:00", "18:00"),  # Saturday
    6: None,                # Sunday -- closed
}

# Service durations in minutes
SERVICE_DURATION = {
    "Classic Haircut": 30,
    "Fade": 30,
    "Beard Trim": 15,
    "Haircut + Beard": 45,
    "Kids Cut (under 12)": 20,
    "Head Shave": 20,
}

_next_appt_id = 1000


def _generate_id() -> str:
    global _next_appt_id
    _next_appt_id += 1
    return f"JB-{_next_appt_id}"


def _get_slots(date_str: str, duration: int = 30) -> list[str]:
    """Generate available time slots for a given date."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return []

    day_of_week = dt.weekday()
    hours = SHOP_HOURS.get(day_of_week)
    if hours is None:
        return []  # Closed

    open_time = datetime.strptime(f"{date_str} {hours[0]}", "%Y-%m-%d %H:%M")
    close_time = datetime.strptime(f"{date_str} {hours[1]}", "%Y-%m-%d %H:%M")

    # Generate all possible slots
    all_slots = []
    current = open_time
    while current + timedelta(minutes=duration) <= close_time:
        all_slots.append(current.strftime("%I:%M %p").lstrip("0"))
        current += timedelta(minutes=30)

    # Remove slots that conflict with existing appointments
    booked_times = set()
    for appt in appointments.values():
        if appt["date"] == date_str and appt["status"] == "confirmed":
            booked_times.add(appt["time"])

    available = [s for s in all_slots if s not in booked_times]
    return available


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------


@webhook.action("check_availability")
def check_availability(params: dict, session_id: str) -> dict:
    """Check available slots for a given date and optional service."""
    date_str = params.get("date", "")
    service = params.get("service", "Classic Haircut")

    if not date_str:
        return {"error": "Please provide a date (YYYY-MM-DD format)."}

    # Validate date is not in the past
    try:
        requested = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"error": f"Invalid date format: {date_str}. Use YYYY-MM-DD."}

    if requested < datetime.now().date():
        return {"error": "That date has already passed. Pick a future date."}

    duration = SERVICE_DURATION.get(service, 30)
    slots = _get_slots(date_str, duration)

    if not slots:
        # Check if it's a closed day
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if SHOP_HOURS.get(dt.weekday()) is None:
            return {
                "available": False,
                "date": date_str,
                "message": "We're closed on Sundays.",
                "slots": [],
            }
        return {
            "available": False,
            "date": date_str,
            "message": "Fully booked for that day.",
            "slots": [],
        }

    return {
        "available": True,
        "date": date_str,
        "service": service,
        "slots": slots[:8],  # Show up to 8 slots
        "total_available": len(slots),
    }


@webhook.action("book_appointment")
def book_appointment(params: dict, session_id: str) -> dict:
    """Book an appointment."""
    date_str = params.get("date", "")
    time_str = params.get("time", "")
    service = params.get("service", "Classic Haircut")
    customer_name = params.get("customer_name", "Customer")

    if not date_str or not time_str:
        return {"error": "Date and time are required to book."}

    # Validate the slot is actually available
    duration = SERVICE_DURATION.get(service, 30)
    available_slots = _get_slots(date_str, duration)
    if time_str not in available_slots:
        return {
            "confirmed": False,
            "error": f"{time_str} on {date_str} is not available.",
            "available_slots": available_slots[:5],
        }

    # Book it
    appt_id = _generate_id()
    appointments[appt_id] = {
        "id": appt_id,
        "date": date_str,
        "time": time_str,
        "service": service,
        "customer_name": customer_name,
        "session_id": session_id,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
    }

    # Also store in the admin data collection for persistence
    try:
        admin.data.add("appointments", appointments[appt_id])
    except Exception:
        pass  # Data collection is a nice-to-have, don't fail the booking

    price = dict(
        zip(
            SERVICE_DURATION.keys(),
            [30, 35, 15, 40, 20, 25],
        )
    ).get(service, 30)

    return {
        "confirmed": True,
        "appointment_id": appt_id,
        "date": date_str,
        "time": time_str,
        "service": service,
        "price": f"${price}",
        "customer_name": customer_name,
        "message": f"You're all set, {customer_name}! See you {date_str} at {time_str}.",
    }


@webhook.action("cancel_appointment")
def cancel_appointment(params: dict, session_id: str) -> dict:
    """Cancel an existing appointment."""
    appt_id = params.get("appointment_id", "")
    reason = params.get("reason", "No reason provided")

    if not appt_id:
        return {"error": "Please provide the appointment ID to cancel."}

    appt = appointments.get(appt_id)
    if appt is None:
        return {
            "cancelled": False,
            "error": f"Appointment {appt_id} not found.",
        }

    if appt["status"] == "cancelled":
        return {
            "cancelled": False,
            "error": f"Appointment {appt_id} was already cancelled.",
        }

    # Cancel it
    appt["status"] = "cancelled"
    appt["cancel_reason"] = reason
    appt["cancelled_at"] = datetime.now().isoformat()

    return {
        "cancelled": True,
        "appointment_id": appt_id,
        "service": appt["service"],
        "was_scheduled": f"{appt['date']} at {appt['time']}",
        "message": "Your appointment has been cancelled. Hope to see you again soon!",
    }


# ---------------------------------------------------------------------------
# Standard webhook handlers (greetings, general messages)
# ---------------------------------------------------------------------------


@webhook.on("agent.wave")
def greet(event):
    """Greet new and returning customers."""
    if event.data.is_first_wave:
        admin.conversations.reply(
            str(event.user.id),
            "Hey! Welcome to Joe's Barber Shop. I can help you:\n\n"
            "- Book a haircut\n"
            "- Check available times\n"
            "- Browse our service menu\n"
            "- Cancel an appointment\n\n"
            "What can I do for you?",
        )
    else:
        admin.conversations.reply(
            str(event.user.id),
            "Welcome back! Ready to book your next cut?",
        )


# ---------------------------------------------------------------------------
# Seed the service menu on startup
# ---------------------------------------------------------------------------


def seed_services():
    """Load the service menu into the data collection."""
    services = [
        {"name": "Classic Haircut", "price": 30, "duration": 30},
        {"name": "Fade", "price": 35, "duration": 30},
        {"name": "Beard Trim", "price": 15, "duration": 15},
        {"name": "Haircut + Beard", "price": 40, "duration": 45},
        {"name": "Kids Cut (under 12)", "price": 20, "duration": 20},
        {"name": "Head Shave", "price": 25, "duration": 20},
    ]
    try:
        admin.data.clear("services")
        for svc in services:
            admin.data.add("services", svc)
        print(f"Seeded {len(services)} services.")
    except Exception as e:
        print(f"Could not seed services (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    seed_services()
    print("Joe's Barber Shop agent is running on port 8080...")
    print("Webhook URL: http://localhost:8080/webhook")
    webhook.start(port=8080)
