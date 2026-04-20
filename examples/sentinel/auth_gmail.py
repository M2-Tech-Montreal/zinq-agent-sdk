#!/usr/bin/env python3
"""One-time Gmail OAuth setup. Run this ONCE per account.

On a headless server, run from a machine with a browser OR use SSH tunnel:
  gcloud compute ssh INSTANCE -- -L 8090:localhost:8090
  # then run this on the instance

Usage:
  python auth_gmail.py mayeski@gmail.com
  python auth_gmail.py v2@m2te.ch
"""

import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_DIR = Path(__file__).parent / "tokens"


def main():
    if len(sys.argv) < 2:
        print("Usage: python auth_gmail.py EMAIL_ADDRESS")
        sys.exit(1)

    account = sys.argv[1]
    TOKEN_DIR.mkdir(exist_ok=True)
    token_file = TOKEN_DIR / f"token_{account.replace('@', '_at_')}.json"

    # Find credentials
    creds_file = None
    for p in [
        Path(__file__).parent / "credentials.json",
        Path.home() / "gmail_secret" / "client_secret.json",
    ]:
        if p.exists():
            creds_file = p
            break

    if not creds_file:
        print("ERROR: No credentials.json found")
        sys.exit(1)

    print(f"Authorizing {account}...")
    print(f"Using credentials from {creds_file}")
    print(f"A browser window will open. Sign in with {account}.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(port=8090, open_browser=True)

    token_file.write_text(creds.to_json())
    print(f"\nToken saved to {token_file}")
    print("You can now run sentinel.py")


if __name__ == "__main__":
    main()
