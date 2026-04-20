"""Gmail monitoring via Gmail API with OAuth."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import URGENT_KEYWORDS, VIP_SENDERS

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_DIR = Path(__file__).parent / "tokens"


def _log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] [GMAIL] {msg}")


def get_gmail_service(account: str):
    """Build an authenticated Gmail API service for the given account."""
    TOKEN_DIR.mkdir(exist_ok=True)
    token_file = TOKEN_DIR / f"token_{account.replace('@', '_at_')}.json"
    # Look for credentials.json in multiple locations
    creds_file = None
    for p in [
        Path(__file__).parent / "credentials.json",
        Path.home() / "gmail_secret" / "client_secret.json",
    ]:
        if p.exists():
            creds_file = p
            break

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_file:
                _log(f"No credentials file found — cannot auth {account}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            _log(f"Authorizing {account} — a browser will open (or use the URL printed):")
            creds = flow.run_local_server(port=0, open_browser=False)

        token_file.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_unread(account: str, since: str | None = None) -> list[dict[str, Any]]:
    """Fetch unread emails from a Gmail account.

    Args:
        account: Gmail address.
        since: ISO timestamp — only fetch emails after this time.

    Returns:
        List of dicts with: id, sender, subject, snippet, date, body_preview.
    """
    service = get_gmail_service(account)
    if not service:
        return []

    query = "is:unread"
    if since:
        # Gmail uses epoch seconds for after:
        try:
            dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            query += f" after:{int(dt.timestamp())}"
        except ValueError:
            pass

    try:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=50
        ).execute()
    except Exception as e:
        _log(f"Error listing messages for {account}: {e}")
        return []

    messages = results.get("messages", [])
    if not messages:
        return []

    emails = []
    for msg_ref in messages:
        try:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            emails.append({
                "id": msg_ref["id"],
                "sender": headers.get("From", "Unknown"),
                "subject": headers.get("Subject", "(no subject)"),
                "snippet": msg.get("snippet", ""),
                "date": headers.get("Date", ""),
                "account": account,
            })
        except Exception as e:
            _log(f"Error fetching message {msg_ref['id']}: {e}")

    _log(f"{account}: {len(emails)} unread emails")
    return emails


def search_emails(account: str, query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search emails (read or unread) matching a query string."""
    service = get_gmail_service(account)
    if not service:
        return []

    try:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
    except Exception as e:
        _log(f"Error searching {account} for '{query}': {e}")
        return []

    messages = results.get("messages", [])
    if not messages:
        return []

    emails = []
    for msg_ref in messages:
        try:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            body = _extract_body(msg.get("payload", {}))

            emails.append({
                "id": msg_ref["id"],
                "sender": headers.get("From", "Unknown"),
                "subject": headers.get("Subject", "(no subject)"),
                "snippet": msg.get("snippet", ""),
                "body": body[:4000],
                "date": headers.get("Date", ""),
                "account": account,
            })
        except Exception as e:
            _log(f"Error fetching message {msg_ref['id']}: {e}")

    _log(f"{account}: {len(emails)} results for '{query}'")
    return emails


def fetch_email_body(account: str, msg_id: str) -> str:
    """Fetch the full body text of an email by ID."""
    service = get_gmail_service(account)
    if not service:
        return ""

    try:
        msg = service.users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()

        payload = msg.get("payload", {})
        body_text = _extract_body(payload)
        return body_text[:4000]  # Cap at 4k chars

    except Exception as e:
        _log(f"Error fetching body for {msg_id}: {e}")
        return ""


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from Gmail payload."""
    # Direct body
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Multipart — recurse into parts
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Fallback: try first part with body data
    for part in parts:
        result = _extract_body(part)
        if result:
            return result

    return ""


def classify_urgency(email: dict[str, Any]) -> str:
    """Classify email urgency based on keywords and VIP senders.

    Returns: 'high', 'medium', or 'low'.
    """
    sender = email.get("sender", "").lower()
    subject = email.get("subject", "").lower()
    snippet = email.get("snippet", "").lower()
    text = f"{sender} {subject} {snippet}"

    # VIP sender = always high
    for vip in VIP_SENDERS:
        if vip.lower() in sender:
            return "high"

    # Urgent keywords = high
    for kw in URGENT_KEYWORDS:
        if kw in text:
            return "high"

    # Calendar invites, meeting requests = medium
    if any(w in text for w in ["calendar", "meeting", "invite", "rsvp", "schedule"]):
        return "medium"

    return "low"
