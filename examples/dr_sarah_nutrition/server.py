"""Dr. Sarah Nutrition -- webhook server for consultations and meal plans.

Demonstrates:
- ZinqBusinessWebhook for action routing (schedule_consultation, request_meal_plan)
- ZinqMarketplaceAdmin for managing client data and intake forms
- AI-powered nutrition advice using Gemini through the admin test client
- Client intake form collection
- Professional consultation booking with availability checking

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
# Configuration
# ---------------------------------------------------------------------------

# Available hours per day of week (0=Monday, 6=Sunday)
AVAILABLE_HOURS = {
    0: ("08:00", "18:00"),  # Monday
    1: ("08:00", "18:00"),  # Tuesday
    2: ("08:00", "18:00"),  # Wednesday
    3: ("08:00", "18:00"),  # Thursday
    4: ("08:00", "16:00"),  # Friday
    5: None,                # Saturday -- closed
    6: None,                # Sunday -- closed
}

SERVICE_INFO = {
    "Initial Consultation": {"price": 150, "duration": 60},
    "Follow-up Session": {"price": 85, "duration": 30},
    "Meal Plan (1 week)": {"price": 75, "duration": 0},
    "Meal Plan (4 weeks)": {"price": 200, "duration": 0},
    "Quick Check-in (15 min)": {"price": 45, "duration": 15},
}

# In-memory stores
appointments: dict[str, dict] = {}
meal_plan_requests: dict[str, dict] = {}
_next_id = 500


def _generate_id(prefix: str) -> str:
    global _next_id
    _next_id += 1
    return f"{prefix}-{_next_id}"


def _get_available_slots(date_str: str, duration: int) -> list[str]:
    """Get available consultation slots for a date."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return []

    day_of_week = dt.weekday()
    hours = AVAILABLE_HOURS.get(day_of_week)
    if hours is None:
        return []

    open_time = datetime.strptime(f"{date_str} {hours[0]}", "%Y-%m-%d %H:%M")
    close_time = datetime.strptime(f"{date_str} {hours[1]}", "%Y-%m-%d %H:%M")

    # Generate slots
    slots = []
    current = open_time
    slot_duration = max(duration, 30)  # Minimum 30-minute slots
    while current + timedelta(minutes=slot_duration) <= close_time:
        # Check for conflicts
        time_str = current.strftime("%I:%M %p").lstrip("0")
        booked = any(
            a["date"] == date_str
            and a["time"] == time_str
            and a["status"] == "confirmed"
            for a in appointments.values()
        )
        if not booked:
            slots.append(time_str)
        current += timedelta(minutes=slot_duration)

    return slots


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------


@webhook.action("schedule_consultation")
def schedule_consultation(params: dict, session_id: str) -> dict:
    """Book a consultation with Dr. Sarah."""
    service = params.get("service", "Initial Consultation")
    preferred_date = params.get("preferred_date", "")
    preferred_time = params.get("preferred_time", "")
    client_name = params.get("client_name", "Client")
    reason = params.get("reason", "")

    if not preferred_date:
        return {"error": "Please provide a preferred date (YYYY-MM-DD)."}

    # Validate service type
    svc_info = SERVICE_INFO.get(service)
    if svc_info is None:
        return {
            "error": f"Unknown service: {service}.",
            "available_services": list(SERVICE_INFO.keys()),
        }

    # Meal plans don't need a time slot
    if svc_info["duration"] == 0:
        return {
            "error": (
                f"'{service}' doesn't require an appointment. "
                "Use 'request a meal plan' instead, or book an "
                "Initial Consultation to discuss your goals first."
            ),
        }

    # Validate date
    try:
        requested = datetime.strptime(preferred_date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": f"Invalid date: {preferred_date}. Use YYYY-MM-DD."}

    if requested <= datetime.now().date():
        return {"error": "Please choose a future date."}

    # Check availability
    available_slots = _get_available_slots(preferred_date, svc_info["duration"])
    if not available_slots:
        # Find next available date
        check_date = requested
        for _ in range(14):
            check_date += timedelta(days=1)
            next_slots = _get_available_slots(
                check_date.isoformat(), svc_info["duration"]
            )
            if next_slots:
                return {
                    "confirmed": False,
                    "message": (
                        f"No availability on {preferred_date}. "
                        f"Next available date is {check_date.isoformat()} "
                        f"with slots at: {', '.join(next_slots[:5])}"
                    ),
                    "suggested_date": check_date.isoformat(),
                    "suggested_slots": next_slots[:5],
                }
        return {
            "confirmed": False,
            "message": "No availability in the next 2 weeks. Please try a later date.",
        }

    # If preferred time specified, validate it
    if preferred_time:
        if preferred_time not in available_slots:
            return {
                "confirmed": False,
                "message": (
                    f"{preferred_time} is not available on {preferred_date}. "
                    f"Available times: {', '.join(available_slots[:6])}"
                ),
                "available_slots": available_slots[:6],
            }
        booked_time = preferred_time
    else:
        # Suggest the first available slot
        booked_time = available_slots[0]

    # Book it
    appt_id = _generate_id("DS")
    appointment = {
        "id": appt_id,
        "service": service,
        "date": preferred_date,
        "time": booked_time,
        "client_name": client_name,
        "reason": reason,
        "session_id": session_id,
        "status": "confirmed",
        "price": svc_info["price"],
        "duration_minutes": svc_info["duration"],
        "created_at": datetime.now().isoformat(),
    }
    appointments[appt_id] = appointment

    # Persist
    try:
        admin.data.add("appointments", appointment)
    except Exception:
        pass

    # Save client info for future reference
    try:
        admin.data.add("clients", {
            "name": client_name,
            "session_id": session_id,
            "first_appointment": preferred_date,
            "reason": reason,
        })
    except Exception:
        pass

    return {
        "confirmed": True,
        "appointment_id": appt_id,
        "service": service,
        "date": preferred_date,
        "time": booked_time,
        "duration": f"{svc_info['duration']} minutes",
        "price": f"${svc_info['price']}",
        "message": (
            f"You're booked, {client_name}! Here are your appointment details:\n\n"
            f"  Service: {service}\n"
            f"  Date: {preferred_date}\n"
            f"  Time: {booked_time}\n"
            f"  Duration: {svc_info['duration']} minutes\n"
            f"  Price: ${svc_info['price']}\n"
            f"  Appointment ID: {appt_id}\n\n"
            "Dr. Sarah will send you a pre-consultation questionnaire "
            "before your appointment. Please fill it out so she can "
            "make the most of your time together."
        ),
    }


@webhook.action("request_meal_plan")
def request_meal_plan(params: dict, session_id: str) -> dict:
    """Request a personalized meal plan."""
    goal = params.get("goal", "")
    restrictions = params.get("dietary_restrictions", "none")
    calories = params.get("calories_target", 0)
    meals_per_day = params.get("meals_per_day", 3)
    duration = params.get("duration", "1_week")
    client_name = params.get("client_name", "Client")

    if not goal:
        return {"error": "Please describe your nutrition goal."}

    # Determine pricing
    if duration == "4_weeks":
        price = 200
        plan_label = "4-week meal plan"
    else:
        price = 75
        plan_label = "1-week meal plan"

    # Calculate estimated calories if not provided
    if not calories:
        calorie_guidance = (
            "Dr. Sarah will calculate your ideal calorie target "
            "based on your goals, activity level, and body composition."
        )
    else:
        calorie_guidance = f"Target: ~{calories} calories/day"

    # Save the request
    request_id = _generate_id("MP")
    request_data = {
        "id": request_id,
        "client_name": client_name,
        "goal": goal,
        "dietary_restrictions": restrictions,
        "calories_target": calories,
        "meals_per_day": meals_per_day,
        "duration": duration,
        "session_id": session_id,
        "status": "pending",
        "price": price,
        "created_at": datetime.now().isoformat(),
    }
    meal_plan_requests[request_id] = request_data

    # Persist
    try:
        admin.data.add("meal_plan_requests", request_data)
    except Exception:
        pass

    # Build intake summary
    intake_summary = [
        f"  Goal: {goal}",
        f"  Restrictions: {restrictions}",
        f"  Meals/day: {meals_per_day}",
        f"  {calorie_guidance}",
    ]

    return {
        "received": True,
        "request_id": request_id,
        "plan_type": plan_label,
        "price": f"${price}",
        "intake_summary": "\n".join(intake_summary),
        "message": (
            f"Got it, {client_name}! Here's what I have for your {plan_label}:\n\n"
            + "\n".join(intake_summary)
            + f"\n\n  Price: ${price}\n"
            f"  Request ID: {request_id}\n\n"
            "Dr. Sarah will prepare your personalized meal plan within "
            "48 hours. She may reach out if she has questions about your "
            "preferences.\n\n"
            "In the meantime, feel free to ask me any nutrition questions!"
        ),
    }


# ---------------------------------------------------------------------------
# Standard webhook handlers
# ---------------------------------------------------------------------------


@webhook.on("agent.wave")
def greet(event):
    """Greet clients with context-aware messaging."""
    session_id = str(event.user.id)

    # Check if they have existing appointments
    client_appts = [
        a for a in appointments.values()
        if a["session_id"] == session_id and a["status"] == "confirmed"
    ]

    if event.data.is_first_wave:
        admin.conversations.reply(
            session_id,
            "Hi! I'm Dr. Sarah's nutrition assistant. I can help you with:\n\n"
            "- Quick nutrition questions (AI-powered)\n"
            "- Book a consultation with Dr. Sarah\n"
            "- Request a personalized meal plan\n\n"
            "What would you like help with?",
        )
    elif client_appts:
        next_appt = client_appts[0]
        admin.conversations.reply(
            session_id,
            f"Welcome back! You have an upcoming appointment:\n\n"
            f"  {next_appt['service']} on {next_appt['date']} "
            f"at {next_appt['time']}\n\n"
            "How can I help you today?",
        )
    else:
        admin.conversations.reply(
            session_id,
            "Welcome back! Have a nutrition question, or looking to book "
            "a session with Dr. Sarah?",
        )


@webhook.on("vibe.received")
def handle_general_question(event):
    """Handle general nutrition questions with AI guidance.

    For questions that need clinical assessment, escalate to Dr. Sarah.
    """
    text = event.data.transcript or event.data.text or ""
    lower = text.lower()
    session_id = str(event.user.id)

    # Detect topics that should be escalated
    escalation_keywords = [
        "eating disorder", "anorexia", "bulimia", "binge",
        "pregnant", "pregnancy", "gestational diabetes",
        "kidney disease", "dialysis", "liver disease",
        "severe allergy", "anaphylaxis",
    ]

    if any(kw in lower for kw in escalation_keywords):
        admin.conversations.reply(
            session_id,
            "This is something Dr. Sarah should discuss with you directly. "
            "It requires a proper clinical assessment to give you safe, "
            "personalized guidance.\n\n"
            "Would you like me to book a consultation for you?",
        )
        return

    # For general questions, provide a helpful response
    # In production, this would use the Gemini proxy for AI-powered answers
    admin.conversations.reply(
        session_id,
        "Great question! Let me look into that for you. "
        "For personalized advice based on your specific health situation, "
        "I'd recommend booking a consultation with Dr. Sarah.\n\n"
        "Would you like to:\n"
        "- Book a consultation\n"
        "- Request a meal plan\n"
        "- Ask another question",
    )


# ---------------------------------------------------------------------------
# Seed initial data
# ---------------------------------------------------------------------------


def seed_services():
    """Load services into the data collection."""
    try:
        admin.data.clear("services")
        for name, info in SERVICE_INFO.items():
            admin.data.add("services", {
                "name": name,
                "price": info["price"],
                "duration_minutes": info["duration"],
            })
        print(f"Seeded {len(SERVICE_INFO)} services.")
    except Exception as e:
        print(f"Could not seed services (non-fatal): {e}")

    # Seed some nutrition tips for the AI to reference
    try:
        admin.data.clear("nutrition_tips")
        tips = [
            {
                "topic": "hydration",
                "tip": "Aim for 8 glasses (64 oz) of water daily. More if you exercise.",
            },
            {
                "topic": "protein",
                "tip": "Most adults need 0.8-1g of protein per kg of body weight. Athletes may need 1.2-2g/kg.",
            },
            {
                "topic": "fiber",
                "tip": "Target 25-30g of fiber daily from whole foods. Increase gradually to avoid discomfort.",
            },
            {
                "topic": "meal_timing",
                "tip": "Eating at consistent times helps regulate hunger hormones and blood sugar.",
            },
        ]
        for tip in tips:
            admin.data.add("nutrition_tips", tip)
        print(f"Seeded {len(tips)} nutrition tips.")
    except Exception as e:
        print(f"Could not seed tips (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    seed_services()
    print("Dr. Sarah Nutrition agent is running on port 8080...")
    print("Webhook URL: http://localhost:8080/webhook")
    webhook.start(port=8080)
