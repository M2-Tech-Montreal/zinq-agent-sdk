"""E2E tests for the Rosa's Bakery business agent example.

Rosa's Bakery uses ZinqMarketplaceAdmin to manage daily specials,
receive pickup orders, handle custom cake requests, and broadcast
to customers. These tests exercise the SDK methods that the
bakery example uses.
"""

from __future__ import annotations

import uuid

import pytest

from zinq_agent import ZinqMarketplaceAdmin


class TestRosasDailySpecials:
    """Tests covering Rosa's morning update flow (daily specials management)."""

    def test_clear_and_add_specials(self, admin: ZinqMarketplaceAdmin) -> None:
        """Rosa clears yesterday's specials and adds today's."""
        collection = f"e2e_bakery_specials_{uuid.uuid4().hex[:6]}"
        try:
            # Clear (may not exist yet, that's fine)
            try:
                admin.data.clear(collection)
            except Exception:
                pass

            # Add today's specials
            admin.data.add(collection, {
                "item": "Sourdough Loaf",
                "price": 8.00,
                "note": "Fresh from the oven!",
                "date": "2026-04-19",
            })
            admin.data.add(collection, {
                "item": "Lavender Honey Croissant",
                "price": 6.00,
                "note": "Limited batch -- only 20 made today!",
                "date": "2026-04-19",
            })
            admin.data.add(collection, {
                "item": "Matcha Muffin",
                "price": 4.50,
                "note": "New recipe -- tell us what you think!",
                "date": "2026-04-19",
            })

            records = admin.data.list(collection)
            assert len(records) == 3

            # Verify items contain expected data
            item_names = [r.get("name") or r.get("item") for r in records]
            for r in records:
                data = r.get("data", r)
                name = data.get("item") or data.get("name")
                assert name is not None
        finally:
            admin.data.clear(collection)

    def test_seed_menu(self, admin: ZinqMarketplaceAdmin) -> None:
        """Rosa seeds the full menu into a data collection."""
        collection = f"e2e_bakery_menu_{uuid.uuid4().hex[:6]}"
        menu = {
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
        try:
            for name, price in menu.items():
                admin.data.add(collection, {"name": name, "price": price})

            records = admin.data.list(collection, limit=50)
            assert len(records) == len(menu)
        finally:
            admin.data.clear(collection)


class TestRosasCustomerChat:
    """Tests covering customer interactions via the test client."""

    def test_customer_asks_specials(self, admin: ZinqMarketplaceAdmin) -> None:
        """Customer asks what's fresh today."""
        admin.test.reset()
        response = admin.test.chat("What are your specials today?")
        assert isinstance(response, dict)
        reply = response.get("reply") or response.get("text") or response.get("message", "")
        assert len(reply) > 0

    def test_customer_asks_menu(self, admin: ZinqMarketplaceAdmin) -> None:
        """Customer asks about the menu."""
        admin.test.reset()
        response = admin.test.chat("What's on your menu?")
        assert isinstance(response, dict)

    def test_customer_asks_hours(self, admin: ZinqMarketplaceAdmin) -> None:
        """Customer asks about business hours."""
        admin.test.reset()
        response = admin.test.chat("What are your hours?")
        assert isinstance(response, dict)


class TestRosasOrderFlow:
    """Tests covering pickup order management via data collections."""

    def test_create_order_record(self, admin: ZinqMarketplaceAdmin) -> None:
        """Simulate saving a pickup order to the data collection."""
        collection = f"e2e_bakery_orders_{uuid.uuid4().hex[:6]}"
        try:
            order = {
                "id": "RB-101",
                "customer_name": "E2E Test Customer",
                "items": [
                    {"name": "Sourdough Loaf", "quantity": 2, "unit_price": 8.00, "line_total": 16.00},
                    {"name": "Croissant", "quantity": 4, "unit_price": 4.50, "line_total": 18.00},
                ],
                "total": 34.00,
                "pickup_time": "10:00 AM",
                "status": "confirmed",
            }
            result = admin.data.add(collection, order)
            assert isinstance(result, dict)

            records = admin.data.list(collection)
            assert len(records) >= 1
        finally:
            admin.data.clear(collection)

    def test_custom_cake_request(self, admin: ZinqMarketplaceAdmin) -> None:
        """Simulate saving a custom cake request."""
        collection = f"e2e_bakery_cakes_{uuid.uuid4().hex[:6]}"
        try:
            cake_request = {
                "occasion": "birthday",
                "servings": 20,
                "flavor": "chocolate",
                "date_needed": "2026-05-01",
                "details": "Two layers with buttercream frosting",
                "status": "pending_review",
            }
            result = admin.data.add(collection, cake_request)
            assert isinstance(result, dict)
        finally:
            admin.data.clear(collection)


class TestRosasBroadcast:
    """Tests covering Rosa's broadcast to customers."""

    def test_morning_broadcast(self, admin: ZinqMarketplaceAdmin) -> None:
        """Rosa sends a morning broadcast about daily specials."""
        message = (
            "Good morning from Rosa's Bakery!\n\n"
            "Fresh out of the oven today:\n"
            "  Lavender Honey Croissant - $6.00\n"
            "    Limited batch -- only 20 made today!\n\n"
            "  Rosemary Focaccia - $7.50\n"
            "    Fresh rosemary from the garden.\n\n"
            "Order ahead for pickup -- just message me!"
        )
        result = admin.broadcast(message)
        assert isinstance(result, dict)


class TestRosasStats:
    """Tests covering Rosa's daily stats checks."""

    def test_user_count(self, admin: ZinqMarketplaceAdmin) -> None:
        """Rosa checks how many customers use the agent."""
        count = admin.users.count()
        assert isinstance(count, int)
        assert count >= 0

    def test_review_stats(self, admin: ZinqMarketplaceAdmin) -> None:
        """Rosa checks review statistics."""
        stats = admin.reviews.stats()
        assert isinstance(stats, dict)

    def test_collections_overview(self, admin: ZinqMarketplaceAdmin) -> None:
        """Rosa checks which data collections exist."""
        collections = admin.data.collections()
        assert isinstance(collections, list)
