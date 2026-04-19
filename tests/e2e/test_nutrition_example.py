"""E2E tests for the Dr. Sarah Nutrition business agent example.

Dr. Sarah's agent handles consultation booking, meal plan requests,
nutrition Q&A, and safety escalation for sensitive topics. These tests
exercise the SDK methods used in the nutrition example.
"""

from __future__ import annotations

import uuid

import pytest

from zinq_agent import ZinqMarketplaceAdmin


class TestNutritionServiceMenu:
    """Tests covering Dr. Sarah's service catalog."""

    def test_seed_services(self, admin: ZinqMarketplaceAdmin) -> None:
        """Seed the service catalog into a data collection."""
        collection = f"e2e_nutrition_svc_{uuid.uuid4().hex[:6]}"
        services = [
            {"name": "Initial Consultation", "price": 150, "duration_minutes": 60},
            {"name": "Follow-up Session", "price": 85, "duration_minutes": 30},
            {"name": "Meal Plan (1 week)", "price": 75, "duration_minutes": 0},
            {"name": "Meal Plan (4 weeks)", "price": 200, "duration_minutes": 0},
            {"name": "Quick Check-in (15 min)", "price": 45, "duration_minutes": 15},
        ]
        try:
            for svc in services:
                admin.data.add(collection, svc)

            records = admin.data.list(collection, limit=50)
            assert len(records) == len(services)
        finally:
            admin.data.clear(collection)

    def test_seed_nutrition_tips(self, admin: ZinqMarketplaceAdmin) -> None:
        """Seed nutrition tips for the AI to reference."""
        collection = f"e2e_nutrition_tips_{uuid.uuid4().hex[:6]}"
        tips = [
            {
                "topic": "hydration",
                "tip": "Aim for 8 glasses (64 oz) of water daily.",
            },
            {
                "topic": "protein",
                "tip": "Most adults need 0.8-1g of protein per kg of body weight.",
            },
            {
                "topic": "fiber",
                "tip": "Target 25-30g of fiber daily from whole foods.",
            },
            {
                "topic": "meal_timing",
                "tip": "Eating at consistent times helps regulate blood sugar.",
            },
        ]
        try:
            for tip in tips:
                admin.data.add(collection, tip)

            records = admin.data.list(collection)
            assert len(records) == len(tips)
        finally:
            admin.data.clear(collection)


class TestNutritionConsultation:
    """Tests covering consultation booking via data collections."""

    def test_book_consultation_record(self, admin: ZinqMarketplaceAdmin) -> None:
        """Simulate booking a consultation."""
        collection = f"e2e_nutrition_appts_{uuid.uuid4().hex[:6]}"
        try:
            appointment = {
                "id": "DS-501",
                "service": "Initial Consultation",
                "date": "2026-04-25",
                "time": "10:00 AM",
                "client_name": "E2E Test Client",
                "reason": "Weight management",
                "status": "confirmed",
                "price": 150,
                "duration_minutes": 60,
            }
            result = admin.data.add(collection, appointment)
            assert isinstance(result, dict)

            records = admin.data.list(collection)
            assert len(records) >= 1
        finally:
            admin.data.clear(collection)

    def test_save_client_info(self, admin: ZinqMarketplaceAdmin) -> None:
        """Save client intake info for future reference."""
        collection = f"e2e_nutrition_clients_{uuid.uuid4().hex[:6]}"
        try:
            client = {
                "name": "E2E Test Client",
                "session_id": "test_session_001",
                "first_appointment": "2026-04-25",
                "reason": "Weight management and meal planning",
            }
            result = admin.data.add(collection, client)
            assert isinstance(result, dict)
        finally:
            admin.data.clear(collection)


class TestNutritionMealPlan:
    """Tests covering meal plan request management."""

    def test_meal_plan_request_record(self, admin: ZinqMarketplaceAdmin) -> None:
        """Simulate saving a meal plan request."""
        collection = f"e2e_nutrition_meals_{uuid.uuid4().hex[:6]}"
        try:
            request_data = {
                "id": "MP-501",
                "client_name": "E2E Test Client",
                "goal": "Lose 10 lbs over 3 months",
                "dietary_restrictions": "gluten-free",
                "calories_target": 1800,
                "meals_per_day": 3,
                "duration": "4_weeks",
                "status": "pending",
                "price": 200,
            }
            result = admin.data.add(collection, request_data)
            assert isinstance(result, dict)

            records = admin.data.list(collection)
            assert len(records) >= 1
        finally:
            admin.data.clear(collection)

    def test_update_meal_plan_status(self, admin: ZinqMarketplaceAdmin) -> None:
        """Update a meal plan request status to completed."""
        collection = f"e2e_nutrition_mpupd_{uuid.uuid4().hex[:6]}"
        try:
            added = admin.data.add(collection, {
                "id": "MP-502",
                "goal": "Build muscle",
                "status": "pending",
            })
            record_id = added.get("recordId") or added.get("record_id") or added.get("id")
            if record_id is None:
                pytest.skip("Could not get record_id")

            updated = admin.data.update(collection, str(record_id), {
                "id": "MP-502",
                "goal": "Build muscle",
                "status": "completed",
                "plan_url": "https://example.com/meal-plan-502.pdf",
            })
            assert isinstance(updated, dict)
        finally:
            admin.data.clear(collection)


class TestNutritionCustomerChat:
    """Tests covering client interactions via the test client."""

    def test_client_asks_services(self, admin: ZinqMarketplaceAdmin) -> None:
        """Client asks about available services."""
        admin.test.reset()
        response = admin.test.chat("What services do you offer?")
        assert isinstance(response, dict)
        reply = response.get("reply") or response.get("text") or response.get("message", "")
        assert len(reply) > 0

    def test_client_books_consultation(self, admin: ZinqMarketplaceAdmin) -> None:
        """Client attempts to book a consultation."""
        admin.test.reset()
        response = admin.test.chat(
            "I'd like to book an initial consultation for next Monday"
        )
        assert isinstance(response, dict)

    def test_client_asks_meal_plan(self, admin: ZinqMarketplaceAdmin) -> None:
        """Client requests a meal plan."""
        admin.test.reset()
        response = admin.test.chat(
            "I'd like a 4-week meal plan for weight loss. "
            "I'm gluten-free and want about 1800 calories per day."
        )
        assert isinstance(response, dict)

    def test_client_general_nutrition_question(self, admin: ZinqMarketplaceAdmin) -> None:
        """Client asks a general nutrition question."""
        admin.test.reset()
        response = admin.test.chat("How much protein should I eat per day?")
        assert isinstance(response, dict)

    def test_safety_escalation_topic(self, admin: ZinqMarketplaceAdmin) -> None:
        """Verify that sensitive topics get handled appropriately.

        The agent should either escalate to human or provide a safe
        response for sensitive health topics.
        """
        admin.test.reset()
        response = admin.test.chat(
            "I've been struggling with eating and want to talk about it"
        )
        assert isinstance(response, dict)
        reply = response.get("reply") or response.get("text") or response.get("message", "")
        # The response should exist and be non-empty (agent handles it)
        assert len(reply) > 0


class TestNutritionStats:
    """Tests covering Dr. Sarah's business analytics."""

    def test_user_count(self, admin: ZinqMarketplaceAdmin) -> None:
        """Check how many clients use the agent."""
        count = admin.users.count()
        assert isinstance(count, int)
        assert count >= 0

    def test_review_stats(self, admin: ZinqMarketplaceAdmin) -> None:
        """Check review statistics."""
        stats = admin.reviews.stats()
        assert isinstance(stats, dict)

    def test_earnings(self, admin: ZinqMarketplaceAdmin) -> None:
        """Check earnings summary."""
        earnings = admin.billing.earnings()
        assert isinstance(earnings, dict)
