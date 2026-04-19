"""E2E tests for the Joe's Barber Shop business agent example.

Joe's Barber uses ZinqMarketplaceAdmin to manage services, check
availability, book appointments, and handle cancellations. These tests
exercise the SDK methods used in the barber shop example.
"""

from __future__ import annotations

import uuid

import pytest

from zinq_agent import ZinqMarketplaceAdmin


class TestBarberServiceMenu:
    """Tests covering Joe's service menu data management."""

    def test_seed_services(self, admin: ZinqMarketplaceAdmin) -> None:
        """Joe seeds his service menu into a data collection."""
        collection = f"e2e_barber_services_{uuid.uuid4().hex[:6]}"
        services = [
            {"name": "Classic Haircut", "price": 30, "duration": 30},
            {"name": "Fade", "price": 35, "duration": 30},
            {"name": "Beard Trim", "price": 15, "duration": 15},
            {"name": "Haircut + Beard", "price": 40, "duration": 45},
            {"name": "Kids Cut (under 12)", "price": 20, "duration": 20},
            {"name": "Head Shave", "price": 25, "duration": 20},
        ]
        try:
            for svc in services:
                admin.data.add(collection, svc)

            records = admin.data.list(collection, limit=50)
            assert len(records) == len(services)
        finally:
            admin.data.clear(collection)

    def test_update_service_price(self, admin: ZinqMarketplaceAdmin) -> None:
        """Joe updates a service price."""
        collection = f"e2e_barber_svcupd_{uuid.uuid4().hex[:6]}"
        try:
            added = admin.data.add(collection, {
                "name": "Classic Haircut",
                "price": 30,
                "duration": 30,
            })
            record_id = added.get("recordId") or added.get("record_id") or added.get("id")
            if record_id is None:
                pytest.skip("Could not get record_id from add response")

            updated = admin.data.update(collection, str(record_id), {
                "name": "Classic Haircut",
                "price": 35,
                "duration": 30,
            })
            assert isinstance(updated, dict)
        finally:
            admin.data.clear(collection)


class TestBarberAppointments:
    """Tests covering appointment booking via data collections."""

    def test_book_appointment_record(self, admin: ZinqMarketplaceAdmin) -> None:
        """Simulate booking an appointment by adding to data collection."""
        collection = f"e2e_barber_appts_{uuid.uuid4().hex[:6]}"
        try:
            appointment = {
                "id": "JB-1001",
                "date": "2026-04-21",
                "time": "10:00 AM",
                "service": "Classic Haircut",
                "customer_name": "E2E Test Customer",
                "status": "confirmed",
            }
            result = admin.data.add(collection, appointment)
            assert isinstance(result, dict)

            records = admin.data.list(collection)
            assert len(records) >= 1
        finally:
            admin.data.clear(collection)

    def test_cancel_appointment_record(self, admin: ZinqMarketplaceAdmin) -> None:
        """Simulate cancelling an appointment by updating record status."""
        collection = f"e2e_barber_cancel_{uuid.uuid4().hex[:6]}"
        try:
            added = admin.data.add(collection, {
                "id": "JB-1002",
                "date": "2026-04-21",
                "time": "2:00 PM",
                "service": "Fade",
                "status": "confirmed",
            })
            record_id = added.get("recordId") or added.get("record_id") or added.get("id")
            if record_id is None:
                pytest.skip("Could not get record_id")

            updated = admin.data.update(collection, str(record_id), {
                "id": "JB-1002",
                "date": "2026-04-21",
                "time": "2:00 PM",
                "service": "Fade",
                "status": "cancelled",
                "cancel_reason": "E2E test cancellation",
            })
            assert isinstance(updated, dict)
        finally:
            admin.data.clear(collection)

    def test_multiple_bookings_same_day(self, admin: ZinqMarketplaceAdmin) -> None:
        """Simulate multiple bookings for conflict detection."""
        collection = f"e2e_barber_multi_{uuid.uuid4().hex[:6]}"
        try:
            admin.data.add(collection, {
                "date": "2026-04-22",
                "time": "9:00 AM",
                "service": "Classic Haircut",
                "status": "confirmed",
            })
            admin.data.add(collection, {
                "date": "2026-04-22",
                "time": "9:30 AM",
                "service": "Fade",
                "status": "confirmed",
            })
            admin.data.add(collection, {
                "date": "2026-04-22",
                "time": "10:00 AM",
                "service": "Beard Trim",
                "status": "confirmed",
            })

            records = admin.data.list(collection)
            assert len(records) == 3

            # Verify we can filter confirmed bookings
            confirmed = [
                r for r in records
                if (r.get("data", r)).get("status") == "confirmed"
            ]
            assert len(confirmed) == 3
        finally:
            admin.data.clear(collection)


class TestBarberCustomerChat:
    """Tests covering customer interactions via the test client."""

    def test_customer_asks_services(self, admin: ZinqMarketplaceAdmin) -> None:
        """Customer asks about available services."""
        admin.test.reset()
        response = admin.test.chat("What services do you offer?")
        assert isinstance(response, dict)
        reply = response.get("reply") or response.get("text") or response.get("message", "")
        assert len(reply) > 0

    def test_customer_asks_availability(self, admin: ZinqMarketplaceAdmin) -> None:
        """Customer asks about available times."""
        admin.test.reset()
        response = admin.test.chat("Do you have any openings tomorrow?")
        assert isinstance(response, dict)

    def test_customer_books_appointment(self, admin: ZinqMarketplaceAdmin) -> None:
        """Customer books a haircut via chat."""
        admin.test.reset()
        response = admin.test.chat(
            "I'd like to book a classic haircut for tomorrow at 10 AM"
        )
        assert isinstance(response, dict)

    def test_customer_asks_prices(self, admin: ZinqMarketplaceAdmin) -> None:
        """Customer asks about pricing."""
        admin.test.reset()
        response = admin.test.chat("How much is a fade?")
        assert isinstance(response, dict)
