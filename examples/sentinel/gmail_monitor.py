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
    creds_file = Path(__file__).parent / "credentials.json"

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_file.exists():
                _log(f"credentials.json not found — cannot auth {account}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0)

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
