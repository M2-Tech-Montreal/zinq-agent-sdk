# Dr. Sarah - Nutrition Coach

A complete marketplace agent example for a nutrition practice. Clients book consultations, request personalized meal plans, and ask nutrition questions -- all through chat on Zinq.

## What this demonstrates

- **Professional consultation booking** with availability checking and conflict detection
- **Meal plan requests** with intake form data collection (goals, restrictions, calories)
- **AI-powered nutrition advice** with safety guardrails for medical topics
- **Automatic escalation** for clinical topics (eating disorders, pregnancy, severe allergies)
- **Client data management** through data collections
- **Service tiering** (Initial Consultation, Follow-up, Quick Check-in, Meal Plans)

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Agent definition -- personality, services, tools, escalation rules |
| `server.py` | Webhook server -- handles schedule_consultation, request_meal_plan, general nutrition Q&A |

## Prerequisites

- Python 3.10+
- A Zinq business account (get one at [zinq-app.com/business](https://zinq-app.com/business))
- Your `ZINQ_BIZ_KEY` and `ZINQ_WEBHOOK_SECRET` (set as environment variables)

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

## Sample conversation

```
Client:  Hi, I'd like to start eating healthier. Where do I begin?
Agent:   Great question! The foundation of healthy eating is:

           1. Fill half your plate with vegetables
           2. Choose whole grains over refined
           3. Include lean protein at every meal
           4. Stay hydrated (aim for 64 oz of water daily)

         For a personalized plan based on your specific goals and
         health situation, I'd recommend booking an Initial Consultation
         with Dr. Sarah. Would you like to schedule one?

Client:  Yes, can I book next Wednesday at 10am? My name is Alex.
Agent:   [calls schedule_consultation]

Agent:   You're booked, Alex! Here are your appointment details:

           Service: Initial Consultation
           Date: 2026-04-22
           Time: 10:00 AM
           Duration: 60 minutes
           Price: $150
           Appointment ID: DS-501

         Dr. Sarah will send you a pre-consultation questionnaire
         before your appointment.

Client:  I'd also like a 4-week meal plan. I want to lose weight,
         I'm vegetarian, and I eat about 3 meals a day.
Agent:   [calls request_meal_plan]

Agent:   Got it, Alex! Here's what I have for your 4-week meal plan:

           Goal: weight loss
           Restrictions: vegetarian
           Meals/day: 3
           Dr. Sarah will calculate your ideal calorie target.

           Price: $200
           Request ID: MP-502

         Dr. Sarah will prepare your personalized meal plan within
         48 hours.

Client:  I've been struggling with binge eating lately.
Agent:   This is something Dr. Sarah should discuss with you directly.
         It requires a proper clinical assessment to give you safe,
         personalized guidance.

         Would you like me to book a consultation for you?
```

## Safety guardrails

This example demonstrates responsible AI behavior for health-related agents:

1. **Never diagnoses** -- The AI provides general nutrition guidance, not medical diagnoses
2. **Escalates clinical topics** -- Eating disorders, pregnancy nutrition, kidney disease, and severe allergies are immediately escalated to the human professional
3. **Recommends consultations** -- For personalized medical nutrition therapy, the agent always recommends booking time with Dr. Sarah
4. **Transparent about limitations** -- The greeting message clearly states that AI answers are general guidance

## Production considerations

- Replace in-memory stores with a database (PostgreSQL, SQLite)
- Integrate with a real calendar API (Google Calendar, Calendly) for availability
- Add payment processing (Stripe) for consultation fees
- Implement pre-consultation questionnaires via data collections
- Set up email notifications for new bookings
- Add HIPAA-compliant data handling if operating in the US
