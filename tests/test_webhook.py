"""Tests for the ZinqWebhook server."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from zinq_agent import ZinqWebhook
from zinq_agent.models import (
    AgentWaveData,
    CharmReceivedData,
    VibeReceivedData,
    VibeReplyData,
)

SECRET = "zws_" + "a" * 32


def make_signature(payload: bytes, secret: str = SECRET) -> str:
    """Generate a valid HMAC-SHA256 signature."""
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def make_event_payload(event_type: str, data: dict) -> dict:
    """Build a webhook event payload."""
    return {
        "event": event_type,
        "deliveryId": "del_test123",
        "timestamp": "2026-04-19T19:00:00Z",
        "agent": {"id": 501, "name": "Test Bot"},
        "user": {"id": 42, "name": "Alex", "timezone": "America/New_York"},
        "data": data,
    }


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestWebhookInit:
    def test_valid_secret(self):
        wh = ZinqWebhook(secret=SECRET)
        assert wh.secret == SECRET

    def test_invalid_secret_prefix(self):
        with pytest.raises(ValueError, match="Expected 'zws_' prefix"):
            ZinqWebhook(secret="bad_secret")

    def test_skip_signature_check_allows_any_secret(self):
        wh = ZinqWebhook(secret="anything", skip_signature_check=True)
        assert wh.secret == "anything"


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------


class TestHandlerRegistration:
    def test_register_valid_event(self):
        wh = ZinqWebhook(secret=SECRET)
        received = []

        @wh.on("vibe.received")
        def handler(event):
            received.append(event)

        assert "vibe.received" in wh._handlers
        assert len(wh._handlers["vibe.received"]) == 1

    def test_register_invalid_event(self):
        wh = ZinqWebhook(secret=SECRET)

        with pytest.raises(ValueError, match="Unknown event type"):

            @wh.on("invalid.event")
            def handler(event):
                pass

    def test_register_multiple_handlers_same_event(self):
        wh = ZinqWebhook(secret=SECRET)

        @wh.on("vibe.received")
        def handler1(event):
            pass

        @wh.on("vibe.received")
        def handler2(event):
            pass

        assert len(wh._handlers["vibe.received"]) == 2

    def test_register_all_event_types(self):
        wh = ZinqWebhook(secret=SECRET)

        for event_type in ["vibe.received", "charm.received", "agent.wave", "vibe.reply"]:

            @wh.on(event_type)
            def handler(event):
                pass

        assert len(wh._handlers) == 4


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


class TestSignatureVerification:
    def test_valid_signature(self):
        wh = ZinqWebhook(secret=SECRET)
        payload = b'{"event": "test"}'
        signature = make_signature(payload)
        timestamp = str(int(time.time()))

        assert wh.verify_signature(payload, signature, timestamp) is True

    def test_invalid_signature(self):
        wh = ZinqWebhook(secret=SECRET)
        payload = b'{"event": "test"}'
        timestamp = str(int(time.time()))

        assert wh.verify_signature(payload, "sha256=invalid", timestamp) is False

    def test_expired_timestamp(self):
        wh = ZinqWebhook(secret=SECRET)
        payload = b'{"event": "test"}'
        signature = make_signature(payload)
        old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago

        assert wh.verify_signature(payload, signature, old_timestamp) is False

    def test_skip_signature_check(self):
        wh = ZinqWebhook(secret="anything", skip_signature_check=True)
        assert wh.verify_signature(b"data", "bad_sig", None) is True


# ---------------------------------------------------------------------------
# Event parsing and dispatch
# ---------------------------------------------------------------------------


class TestEventDispatch:
    def test_vibe_received_event(self):
        wh = ZinqWebhook(secret=SECRET, skip_signature_check=True)
        received_events = []

        @wh.on("vibe.received")
        def handler(event):
            received_events.append(event)

        payload = make_event_payload(
            "vibe.received",
            {
                "vibeId": 67890,
                "type": "TEXT",
                "text": "Hello!",
                "transcript": None,
                "mediaUrl": None,
                "mediaType": None,
                "duration": None,
                "createdAt": "2026-04-19T19:00:00Z",
            },
        )

        body = json.dumps(payload).encode()
        response_body, status_code = wh.handle_request(body, {})

        assert status_code == 200
        assert len(received_events) == 1
        assert received_events[0].event == "vibe.received"
        assert isinstance(received_events[0].data, VibeReceivedData)
        assert received_events[0].data.vibe_id == 67890
        assert received_events[0].data.text == "Hello!"

    def test_charm_received_event(self):
        wh = ZinqWebhook(secret=SECRET, skip_signature_check=True)
        received_events = []

        @wh.on("charm.received")
        def handler(event):
            received_events.append(event)

        payload = make_event_payload(
            "charm.received",
            {
                "charmId": 55001,
                "emoji": "thumbs_up",
                "vibeId": 99001,
                "createdAt": "2026-04-19T19:05:00Z",
            },
        )

        body = json.dumps(payload).encode()
        wh.handle_request(body, {})

        assert len(received_events) == 1
        assert isinstance(received_events[0].data, CharmReceivedData)
        assert received_events[0].data.emoji == "thumbs_up"

    def test_agent_wave_event(self):
        wh = ZinqWebhook(secret=SECRET, skip_signature_check=True)
        received_events = []

        @wh.on("agent.wave")
        def handler(event):
            received_events.append(event)

        payload = make_event_payload(
            "agent.wave",
            {
                "isFirstWave": True,
                "lastInteractionAt": None,
            },
        )

        body = json.dumps(payload).encode()
        wh.handle_request(body, {})

        assert len(received_events) == 1
        assert isinstance(received_events[0].data, AgentWaveData)
        assert received_events[0].data.is_first_wave is True

    def test_vibe_reply_event(self):
        wh = ZinqWebhook(secret=SECRET, skip_signature_check=True)
        received_events = []

        @wh.on("vibe.reply")
        def handler(event):
            received_events.append(event)

        payload = make_event_payload(
            "vibe.reply",
            {
                "vibeId": 67891,
                "type": "TEXT",
                "text": "Show me the plan",
                "replyToVibeId": 99001,
                "buttonValue": "show_plan",
                "createdAt": "2026-04-19T19:03:00Z",
            },
        )

        body = json.dumps(payload).encode()
        wh.handle_request(body, {})

        assert len(received_events) == 1
        assert isinstance(received_events[0].data, VibeReplyData)
        assert received_events[0].data.button_value == "show_plan"

    def test_missing_signature_rejected(self):
        wh = ZinqWebhook(secret=SECRET)

        payload = make_event_payload("vibe.received", {"vibeId": 1, "type": "TEXT", "createdAt": "2026-04-19T19:00:00Z"})
        body = json.dumps(payload).encode()

        response_body, status_code = wh.handle_request(body, {})
        assert status_code == 401

    def test_invalid_json_rejected(self):
        wh = ZinqWebhook(secret=SECRET, skip_signature_check=True)

        response_body, status_code = wh.handle_request(b"not json", {})
        assert status_code == 400

    def test_handler_exception_does_not_crash_server(self):
        wh = ZinqWebhook(secret=SECRET, skip_signature_check=True)

        @wh.on("vibe.received")
        def bad_handler(event):
            raise RuntimeError("Handler crashed!")

        payload = make_event_payload(
            "vibe.received",
            {
                "vibeId": 1,
                "type": "TEXT",
                "text": "test",
                "createdAt": "2026-04-19T19:00:00Z",
            },
        )

        body = json.dumps(payload).encode()
        response_body, status_code = wh.handle_request(body, {})

        # Server should still return 200 even if handler crashes
        assert status_code == 200

    def test_no_handler_registered_still_ok(self):
        wh = ZinqWebhook(secret=SECRET, skip_signature_check=True)

        payload = make_event_payload(
            "vibe.received",
            {
                "vibeId": 1,
                "type": "TEXT",
                "text": "no handler",
                "createdAt": "2026-04-19T19:00:00Z",
            },
        )

        body = json.dumps(payload).encode()
        response_body, status_code = wh.handle_request(body, {})
        assert status_code == 200
