"""Webhook server for receiving push events from Zinq.

Provides a Flask-based HTTP server that receives webhook events,
verifies HMAC-SHA256 signatures, and dispatches to registered handlers.

Requires the ``webhook`` extra: ``pip install zinq-agent[webhook]``
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from collections.abc import Callable
from typing import Any

from .models import (
    EVENT_DATA_MODELS,
    VibeReceivedData,
    WebhookAgent,
    WebhookEvent,
    WebhookUser,
)

logger = logging.getLogger("zinq_agent.webhook")

# Maximum age of a webhook request (replay protection)
MAX_TIMESTAMP_AGE_SECONDS = 300  # 5 minutes


class ZinqWebhook:
    """Webhook server for receiving events from the Zinq platform.

    Registers event handlers and starts a Flask server to receive
    webhook POST requests from Zinq.

    Usage::

        from zinq_agent import ZinqWebhook

        webhook = ZinqWebhook(secret="zws_xxxxx")

        @webhook.on("vibe.received")
        def handle_vibe(event):
            print(f"User said: {event.data.text}")

        webhook.start(port=8080)

    Args:
        secret: Webhook secret (``zws_`` prefix) for signature verification.
        skip_signature_check: If True, skip signature verification (for local dev only).
    """

    def __init__(
        self,
        secret: str,
        *,
        skip_signature_check: bool = False,
    ) -> None:
        if not secret.startswith("zws_") and not skip_signature_check:
            raise ValueError(
                f"Invalid webhook secret format. Expected 'zws_' prefix, got '{secret[:4]}...'"
            )

        self.secret = secret
        self.skip_signature_check = skip_signature_check
        self._handlers: dict[str, list[Callable[[WebhookEvent], Any]]] = {}

    def on(self, event_type: str) -> Callable:
        """Register a handler for a specific event type.

        Valid event types:
        - ``"vibe.received"`` -- User sends a vibe to the agent
        - ``"charm.received"`` -- User sends a charm (emoji reaction)
        - ``"agent.wave"`` -- User opens the agent chat
        - ``"vibe.reply"`` -- User replies to an agent vibe or taps a button

        Usage::

            @webhook.on("vibe.received")
            def handle_vibe(event):
                text = event.data.transcript or event.data.text
                print(f"User said: {text}")
        """
        valid_events = {"vibe.received", "charm.received", "agent.wave", "vibe.reply"}
        if event_type not in valid_events:
            raise ValueError(
                f"Unknown event type '{event_type}'. Valid types: {', '.join(sorted(valid_events))}"
            )

        def decorator(func: Callable[[WebhookEvent], Any]) -> Callable[[WebhookEvent], Any]:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(func)
            return func

        return decorator

    def verify_signature(
        self,
        payload: bytes,
        signature_header: str,
        timestamp_header: str | None = None,
    ) -> bool:
        """Verify the HMAC-SHA256 signature of a webhook request.

        Args:
            payload: Raw request body as bytes.
            signature_header: Value of the ``X-Zinq-Signature`` header.
            timestamp_header: Value of the ``X-Zinq-Timestamp`` header (for replay protection).

        Returns:
            True if the signature is valid and the request is not too old.
        """
        if self.skip_signature_check:
            return True

        # Replay protection
        if timestamp_header is not None:
            try:
                request_time = int(timestamp_header)
                now = int(time.time())
                if abs(now - request_time) > MAX_TIMESTAMP_AGE_SECONDS:
                    logger.warning(
                        "Webhook request rejected: timestamp too old (%d seconds)",
                        abs(now - request_time),
                    )
                    return False
            except (ValueError, TypeError):
                logger.warning("Webhook request rejected: invalid timestamp header")
                return False

        expected = "sha256=" + hmac.new(
            self.secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature_header)

    def _parse_event(self, payload: dict[str, Any]) -> WebhookEvent:
        """Parse a raw webhook payload into a typed WebhookEvent."""
        event_type = payload.get("event", "")
        data_model = EVENT_DATA_MODELS.get(event_type)

        raw_data = payload.get("data", {})
        if data_model is not None:
            typed_data = data_model.model_validate(raw_data)
        else:
            # Unknown event type -- use VibeReceivedData as fallback
            logger.warning("Unknown webhook event type: %s", event_type)
            typed_data = VibeReceivedData.model_validate(raw_data)

        return WebhookEvent(
            event=event_type,
            delivery_id=payload.get("deliveryId", ""),
            timestamp=payload.get("timestamp", ""),
            agent=WebhookAgent.model_validate(payload.get("agent", {})),
            user=WebhookUser.model_validate(payload.get("user", {})),
            data=typed_data,
        )

    def _dispatch(self, event: WebhookEvent) -> None:
        """Dispatch an event to all registered handlers."""
        handlers = self._handlers.get(event.event, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Error in webhook handler for event '%s'",
                    event.event,
                )

    def handle_request(self, body: bytes, headers: dict[str, str]) -> tuple[str, int]:
        """Process a raw webhook request.

        This method can be used with any web framework, not just Flask.

        Args:
            body: Raw request body as bytes.
            headers: Request headers as a dict.

        Returns:
            Tuple of (response_body, status_code).
        """
        signature = headers.get("X-Zinq-Signature", "")
        timestamp = headers.get("X-Zinq-Timestamp")

        if not self.skip_signature_check:
            if not signature:
                return '{"error": "Missing X-Zinq-Signature header"}', 401

            if not self.verify_signature(body, signature, timestamp):
                return '{"error": "Invalid signature"}', 401

        import json

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return '{"error": "Invalid JSON"}', 400

        event = self._parse_event(payload)

        logger.info(
            "Received webhook event: %s (delivery_id=%s)",
            event.event,
            event.delivery_id,
        )

        self._dispatch(event)

        return '{"ok": true}', 200

    def start(
        self,
        *,
        host: str = "0.0.0.0",
        port: int = 8080,
        path: str = "/webhook",
        debug: bool = False,
    ) -> None:
        """Start the Flask webhook server.

        This is a blocking call that runs the Flask development server.
        For production, use a WSGI server (gunicorn, uvicorn) with
        ``create_flask_app()`` instead.

        Args:
            host: Host to bind to (default: ``"0.0.0.0"``).
            port: Port to listen on (default: 8080).
            path: URL path for the webhook endpoint (default: ``"/webhook"``).
            debug: Enable Flask debug mode (default: False).

        Raises:
            ImportError: If Flask is not installed. Install with
                         ``pip install zinq-agent[webhook]``.
        """
        app = self.create_flask_app(path=path)
        logger.info("Starting Zinq webhook server on %s:%d%s", host, port, path)
        app.run(host=host, port=port, debug=debug)

    def create_flask_app(self, *, path: str = "/webhook") -> Any:
        """Create a Flask app with the webhook endpoint configured.

        Use this for production deployments with a WSGI server::

            webhook = ZinqWebhook(secret="zws_xxxxx")
            app = webhook.create_flask_app()
            # Run with: gunicorn app:app

        Args:
            path: URL path for the webhook endpoint (default: ``"/webhook"``).

        Returns:
            A Flask application instance.

        Raises:
            ImportError: If Flask is not installed.
        """
        try:
            from flask import Flask, request
        except ImportError:
            raise ImportError(
                "Flask is required for webhook support. "
                "Install it with: pip install zinq-agent[webhook]"
            ) from None

        app = Flask("zinq_webhook")

        @app.route(path, methods=["POST"])
        def webhook_handler():  # type: ignore[no-untyped-def]
            body = request.get_data()
            headers = {key: value for key, value in request.headers}
            response_body, status_code = self.handle_request(body, headers)
            return response_body, status_code, {"Content-Type": "application/json"}

        @app.route("/health", methods=["GET"])
        def health():  # type: ignore[no-untyped-def]
            return '{"status": "ok"}', 200, {"Content-Type": "application/json"}

        return app
